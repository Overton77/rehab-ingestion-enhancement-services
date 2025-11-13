import aiohttp
import asyncio
import time 
import os 
from typing import List, Optional, Literal
from dotenv import load_dotenv  
from pathlib import Path     
from rehab_npi_puller.npi_csv_download import download_and_extract_csv, parse_csv_to_providers

here = Path(__file__).parent.parent  

load_dotenv(dotenv_path=here / ".env")

NPI_API_URL = os.getenv("NPI_API_URL") or "https://npiregistry.cms.hhs.gov/api/"

# Type alias for fetch methods
FetchMethod = Literal["api", "csv"]

class NPIClient:
    # API limits and constraints (based on NPI Registry API rules)
    MAX_RESULTS_PER_REQUEST = 200
    MAX_SKIP = 1000
    MAX_TOTAL_RESULTS = 1200
    MAX_REQUESTS = 6
    RETRY_LIMIT = 5
    INITIAL_RETRY_DELAY = 1  # Start with 1 second
    MAX_RETRY_DELAY = 32  # Cap at 32 seconds
    RATE_LIMIT_DELAY = 1  
    RUN_TIME_LIMIT = 4 * 60 * 60  # 4 hours
    WAIT_TIME = 2 * 60 * 60  # 2 hours

    def __init__(self, taxonomy_descriptions=None):
        if taxonomy_descriptions is None:
            taxonomy_descriptions = [
                "Substance Abuse Rehabilitation Facility",
                "Substance Abuse Treatment, Children",
            ]
        self.taxonomy_descriptions = taxonomy_descriptions

    async def fetch_providers_by_taxonomy_description(
        self, 
        description: str, 
        session: aiohttp.ClientSession, 
        limit: int = MAX_RESULTS_PER_REQUEST, 
        skip: int = 0
    ) -> List[dict]:
        """
        Fetch providers from NPI API with exponential backoff retry logic.
        """
        params = {
            "version": "2.1",
            "taxonomy_description": description,
            "limit": limit,
            "skip": skip,
            "pretty": "true",
        }
        retries = 0
        while retries < self.RETRY_LIMIT:
            try:
                async with session.get(NPI_API_URL, params=params, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    if resp.status == 429:  # Rate limit
                        delay = self._calculate_backoff_delay(retries)
                        print(f"Rate limited. Waiting {delay}s before retry...")
                        await asyncio.sleep(delay)
                        retries += 1
                        continue
                    
                    resp.raise_for_status()
                    data = await resp.json()
                    return data.get("results", [])
            except asyncio.TimeoutError:
                delay = self._calculate_backoff_delay(retries)
                print(f"Timeout error. Retrying in {delay}s ({retries+1}/{self.RETRY_LIMIT})...")
                retries += 1
                await asyncio.sleep(delay)
            except aiohttp.ClientError as e:
                delay = self._calculate_backoff_delay(retries)
                print(f"Client error: {e}. Retrying in {delay}s ({retries+1}/{self.RETRY_LIMIT})...")
                retries += 1
                await asyncio.sleep(delay)
            except Exception as e:
                delay = self._calculate_backoff_delay(retries)
                print(f"Unexpected error: {e}. Retrying in {delay}s ({retries+1}/{self.RETRY_LIMIT})...")
                retries += 1
                await asyncio.sleep(delay)
        
        print(f"Failed to fetch after {self.RETRY_LIMIT} retries.")
        return []
    
    def _calculate_backoff_delay(self, retry_count: int) -> float:
        """Calculate exponential backoff delay with jitter."""
        import random
        delay = min(self.INITIAL_RETRY_DELAY * (2 ** retry_count), self.MAX_RETRY_DELAY)
        # Add jitter to prevent thundering herd
        jitter = random.uniform(0, delay * 0.1)
        return delay + jitter

    async def fetch_all_providers_from_api(self, start_time: Optional[float] = None) -> List[dict]:
        """
        Fetch all providers from the NPI API based on taxonomy descriptions.
        Returns a list of parsed provider dictionaries.
        """
        all_results = []
        if start_time is None:
            start_time = time.time()
        
        async with aiohttp.ClientSession() as session:
            for desc in self.taxonomy_descriptions:
                skip = 0
                total_fetched = 0
                print(f"\n🔍 Fetching providers for taxonomy: '{desc}'")
                
                for request_num in range(self.MAX_REQUESTS):
                    # Check if we've exceeded runtime limit
                    if time.time() - start_time > self.RUN_TIME_LIMIT:
                        print("⏸️  Reached 4 hour run time limit. Pausing for 2 hours...")
                        await asyncio.sleep(self.WAIT_TIME)
                        print("▶️  Resuming after wait.")
                        start_time = time.time()
                    
                    results = await self.fetch_providers_by_taxonomy_description(
                        desc, session, limit=self.MAX_RESULTS_PER_REQUEST, skip=skip
                    )
                    
                    if not results:
                        print(f"No more results for '{desc}'")
                        break
                    
                    all_results.extend(results)
                    total_fetched += len(results)
                    print(f"✅ Fetched {len(results)} results for '{desc}' (skip={skip}, total: {total_fetched})")
                    
                    # Check if we got fewer results than requested (last page)
                    if len(results) < self.MAX_RESULTS_PER_REQUEST:
                        print(f"📄 Last page reached for '{desc}'")
                        break
                    
                    skip += self.MAX_RESULTS_PER_REQUEST
                    
                    # Respect API limits
                    if skip > self.MAX_SKIP or total_fetched >= self.MAX_TOTAL_RESULTS:
                        print(f"⚠️  API limit reached for '{desc}' (skip: {skip}, total: {total_fetched})")
                        break
                    
                    # Rate limiting between requests
                    await asyncio.sleep(self.RATE_LIMIT_DELAY)
        
        print(f"\n📊 Total raw results fetched: {len(all_results)}")
        # Convert to standardized provider format
        parsed_results = [self._parse_npi_result(r) for r in all_results]
        print(f"✅ Parsed {len(parsed_results)} providers")
        return parsed_results

    def _parse_npi_result(self, result: dict) -> dict:
        """
        Parse NPI API result into a standardized provider dictionary.
        
        Args:
            result: Raw result from NPI API
            
        Returns:
            Dictionary with standardized provider fields
        """
        basic = result.get("basic", {})
        npi_number = str(result.get("number"))
        organization_name = basic.get("organization_name") or basic.get("name")
        last_updated = basic.get("last_updated")
        
        # Get primary taxonomy or fallback to first available
        taxonomy = next((t for t in result.get("taxonomies", []) if t.get("primary")), None)
        if not taxonomy and result.get("taxonomies"):
            taxonomy = result["taxonomies"][0]
        taxonomy_code = taxonomy.get("code") if taxonomy else None
        taxonomy_desc = taxonomy.get("desc") if taxonomy else None
        
        # Get location address or fallback to first available
        address = next((a for a in result.get("addresses", []) if a.get("address_purpose") == "LOCATION"), None)
        if not address and result.get("addresses"):
            address = result["addresses"][0]
        
        addr_str = address.get("address_1", "") if address else ""
        city = address.get("city", "") if address else ""
        state = address.get("state", "") if address else ""
        postal_code = address.get("postal_code", "") if address else ""
        phone = address.get("telephone_number", "") if address else ""
        
        # Build authorized official name
        first_name = basic.get("authorized_official_first_name", "")
        last_name = basic.get("authorized_official_last_name", "")
        official = None
        if first_name or last_name:
            official = f"{first_name} {last_name}".strip()
        
        return {
            "npi_number": npi_number,
            "organization_name": organization_name,
            "address": addr_str,
            "city": city,
            "state": state,
            "postal_code": postal_code,
            "phone": phone,
            "taxonomy_code": taxonomy_code,
            "taxonomy_desc": taxonomy_desc,
            "authorized_official": official,
            "last_updated": last_updated
        }
    
    async def fetch_all_providers_from_csv(self) -> List[dict]:
        """
        Download and parse providers from the NPPES CSV file.
        This method downloads the full NPPES dataset and filters for rehab facilities.
        
        Returns:
            List of parsed provider dictionaries
        """
        print("\n📥 Starting CSV download and processing...")
        
        # Download and extract the CSV file
        csv_path = await download_and_extract_csv()
        
        # Parse the CSV into provider dictionaries
        providers = await parse_csv_to_providers(csv_path)
        
        print(f"✅ CSV processing complete. Found {len(providers)} providers")
        return providers
    
    async def fetch_all_providers(self, method: FetchMethod = "api") -> List[dict]:
        """
        Unified method to fetch providers using either API or CSV method.
        
        Args:
            method: Either "api" or "csv". 
                   - "api": Fetch from NPI Registry API (faster, limited by API constraints)
                   - "csv": Download and parse full NPPES CSV (comprehensive, slower)
        
        Returns:
            List of parsed provider dictionaries in standardized format
        """
        print(f"\n🚀 Fetching providers using method: {method.upper()}")
        
        if method == "api": 
            return await self.fetch_all_providers_from_api()
        elif method == "csv":
            return await self.fetch_all_providers_from_csv() 