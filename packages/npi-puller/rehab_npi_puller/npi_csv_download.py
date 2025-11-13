import os
import re
import zipfile
import aiohttp
import asyncio
import pandas as pd
import shutil 
from typing import List

from dotenv import load_dotenv  
from pathlib import Path   

here = Path(__file__).parent.parent  
load_dotenv(dotenv_path=here / ".env")

NPPES_ZIP_URL = os.getenv("NPPES_ZIP_URL") or  "https://download.cms.gov/nppes/NPPES_Data_Dissemination_May_2025_V2.zip"
TEMP_DIR = "/tmp/nppes_data"
FINAL_CSV_PATH = os.path.join(TEMP_DIR, "npidata.csv")
CSV_REGEX = re.compile(r"^npidata_pfile_\d{8}-\d{8}\.csv$", re.IGNORECASE)
TARGET_CODES = {"324500000X", "3245S0500X"}
TAXONOMY_COLS = [f"Healthcare Provider Taxonomy Code_{i}" for i in range(1, 16)]

CSV_TO_MODEL = {
    "NPI": "npi_number",
    "Provider Organization Name (Legal Business Name)": "organization_name",
    "Provider First Line Business Mailing Address": "address",
    "Provider Business Mailing Address City Name": "city",
    "Provider Business Mailing Address State Name": "state",
    "Provider Business Mailing Address Postal Code": "postal_code",
    "Provider Business Mailing Address Telephone Number": "phone",
    "Healthcare Provider Taxonomy Code_1": "taxonomy_code",
    "Healthcare Provider Taxonomy Group_1": "taxonomy_desc",
    # Authorized official: concatenate first, middle, last name
    # Last Update Date: direct mapping
    "Last Update Date": "last_updated"
}

REQUIRED_MODEL_COLS = [
    "npi_number", "organization_name", "address", "city", "state",
    "postal_code", "phone", "taxonomy_code",
    "last_updated"
]

def truncate_columns(df):
    max_lengths = {
        "npi_number": 10,
        "city": 255,
        "state": 255,
        "postal_code": 255,
        "phone": 255,
        "taxonomy_code": 255,
    }
    for col, max_len in max_lengths.items():
        if col in df.columns:
            df[col] = df[col].apply(lambda x: x[:max_len] if isinstance(x, str) else x)
    return df

async def download_and_extract_csv() -> str:
    """
    Asynchronously download and extract the NPPES CSV file.
    
    Returns:
        Path to the extracted CSV file
    """
    os.makedirs(TEMP_DIR, exist_ok=True)
    zip_path = os.path.join(TEMP_DIR, "nppes.zip")
    print("⬇️ Downloading NPPES ZIP file (this may take a while)...")
    
    try:
        # Download the ZIP file asynchronously
        async with aiohttp.ClientSession() as session:
            async with session.get(NPPES_ZIP_URL, timeout=aiohttp.ClientTimeout(total=3600)) as response:
                response.raise_for_status()
                
                # Get total file size for progress tracking
                total_size = int(response.headers.get('content-length', 0))
                downloaded = 0
                chunk_size = 8192 * 10  # 80KB chunks
                
                with open(zip_path, "wb") as f:
                    async for chunk in response.content.iter_chunked(chunk_size):
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            percent = (downloaded / total_size) * 100
                            if downloaded % (chunk_size * 100) == 0:  # Print every ~8MB
                                print(f"📥 Downloaded: {percent:.1f}% ({downloaded / 1024 / 1024:.1f} MB)")
        
        print("✅ Download complete. Extracting...")
        
        # Extract the ZIP file (run in thread pool since zipfile is blocking)
        await asyncio.to_thread(_extract_csv_from_zip, zip_path)
        
        # Clean up (run in thread pool since file operations are blocking)
        await asyncio.to_thread(_cleanup_temp_directory)
        
        print(f"✅ CSV ready at: {FINAL_CSV_PATH}")
        return FINAL_CSV_PATH
        
    except Exception as e:
        print(f"❌ Error during download/extraction: {e}")
        raise
    finally:
        print('🧹 Download and extraction process completed')


def _extract_csv_from_zip(zip_path: str) -> None:
    """Helper function to extract CSV from ZIP file (blocking I/O)."""
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        matched_files = [name for name in zip_ref.namelist() if CSV_REGEX.match(name)]
        if not matched_files:
            raise FileNotFoundError("❌ No matching npidata_pfile CSV found in ZIP.")
        
        target_file = matched_files[0]
        zip_ref.extract(target_file, TEMP_DIR)
        extracted_path = os.path.join(TEMP_DIR, target_file)
        print(f"✅ Extracted: {extracted_path}")
        
        # Move the extracted CSV to FINAL_CSV_PATH (overwrite if exists)
        if os.path.exists(FINAL_CSV_PATH):
            os.remove(FINAL_CSV_PATH)
        os.rename(extracted_path, FINAL_CSV_PATH)
        print(f"✅ Moved CSV to: {FINAL_CSV_PATH}")


def _cleanup_temp_directory() -> None:
    """Helper function to clean up temporary directory (blocking I/O)."""
    for fname in os.listdir(TEMP_DIR):
        fpath = os.path.join(TEMP_DIR, fname)
        if fpath != FINAL_CSV_PATH:
            if os.path.isfile(fpath) or os.path.islink(fpath):
                os.remove(fpath)
            elif os.path.isdir(fpath):
                shutil.rmtree(fpath)
    print(f"🧹 Cleaned up temp directory, only CSV remains")

async def filter_and_deduplicate(csv_path: str) -> pd.DataFrame:
    """
    Asynchronously filter and deduplicate the CSV data.
    Runs the pandas operations in a thread pool to avoid blocking.
    
    Args:
        csv_path: Path to the CSV file
        
    Returns:
        Filtered and deduplicated DataFrame
    """
    print("🔎 Filtering and deduplicating CSV data...")
    return await asyncio.to_thread(_filter_and_deduplicate_sync, csv_path)


def _filter_and_deduplicate_sync(csv_path: str) -> pd.DataFrame:
    """
    Synchronous helper to filter and deduplicate CSV data (blocking I/O).
    """
    reader = pd.read_csv(csv_path, nrows=0)
    all_cols = reader.columns.tolist()
    taxonomy_cols = [col for col in TAXONOMY_COLS if col in all_cols]
    chunksize = 100_000
    filtered_rows = []
    
    print(f"📊 Processing CSV in chunks of {chunksize:,} rows...")
    chunk_count = 0
    for chunk in pd.read_csv(csv_path, dtype=str, chunksize=chunksize, usecols=all_cols):
        chunk_count += 1
        mask = chunk[taxonomy_cols].apply(
            lambda row: any(code in TARGET_CODES for code in row if isinstance(code, str)), 
            axis=1
        )
        filtered_chunk = chunk[mask]
        if len(filtered_chunk) > 0:
            filtered_rows.append(filtered_chunk)
        if chunk_count % 10 == 0:
            print(f"  Processed {chunk_count} chunks...")
    
    if not filtered_rows:
        print("⚠️  No matching records found!")
        return pd.DataFrame()
    
    df = pd.concat(filtered_rows, ignore_index=True)
    before = len(df)
    df = df.drop_duplicates()
    after = len(df)
    print(f"✅ Rows before deduplication: {before:,}, after: {after:,}")
    return df


async def parse_csv_to_providers(csv_path: str) -> List[dict]:
    """
    Download, filter, and parse CSV data into provider dictionaries.
    
    Args:
        csv_path: Path to the CSV file
        
    Returns:
        List of provider dictionaries in standardized format
    """
    # Filter and deduplicate
    df = await filter_and_deduplicate(csv_path)
    
    if df.empty:
        print("⚠️  No providers found in CSV")
        return []
    
    print(f"📊 Converting {len(df)} records to provider format...")
    
    # Apply truncation
    df = truncate_columns(df)
    
    # Convert to list of dictionaries with standardized field names
    providers = []
    for _, row in df.iterrows():
        # Build authorized official name
        first_name = row.get("Authorized Official First Name", "")
        last_name = row.get("Authorized Official Last Name", "")
        middle_name = row.get("Authorized Official Middle Name", "")
        
        official = None
        if first_name or last_name:
            parts = [str(first_name).strip(), str(middle_name).strip(), str(last_name).strip()]
            official = " ".join(p for p in parts if p and p != "nan")
        
        provider = {
            "npi_number": str(row.get("NPI")),
            "organization_name": row.get("Provider Organization Name (Legal Business Name)"),
            "address": row.get("Provider First Line Business Mailing Address"),
            "city": row.get("Provider Business Mailing Address City Name"),
            "state": row.get("Provider Business Mailing Address State Name"),
            "postal_code": row.get("Provider Business Mailing Address Postal Code"),
            "phone": row.get("Provider Business Mailing Address Telephone Number"),
            "taxonomy_code": row.get("Healthcare Provider Taxonomy Code_1"),
            "taxonomy_desc": row.get("Healthcare Provider Taxonomy Group_1"),
            "authorized_official": official if official else None,
            "last_updated": row.get("Last Update Date")
        }
        providers.append(provider)
    
    print(f"✅ Converted {len(providers)} providers")
    return providers


