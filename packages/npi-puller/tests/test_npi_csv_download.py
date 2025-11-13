"""Tests for NPI CSV Download"""

import pytest
import pandas as pd
import os
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
from pathlib import Path
from rehab_npi_puller.npi_csv_download import (
    truncate_columns,
    _extract_csv_from_zip,
    _cleanup_temp_directory,
    download_and_extract_csv,
    filter_and_deduplicate,
    parse_csv_to_providers,
    TARGET_CODES
)


class TestTruncateColumns:
    """Test suite for column truncation"""
    
    def test_truncate_columns_strings(self):
        """Test truncating string columns to max length"""
        df = pd.DataFrame({
            "npi_number": ["1234567890123"],  # Should truncate to 10
            "city": ["A" * 300],  # Should truncate to 255
            "state": ["California"],  # Should not truncate (under limit)
            "other": ["test"]  # Not in truncation list
        })
        
        result = truncate_columns(df)
        
        assert len(result.loc[0, "npi_number"]) == 10
        assert len(result.loc[0, "city"]) == 255
        assert result.loc[0, "state"] == "California"
        assert result.loc[0, "other"] == "test"
    
    def test_truncate_columns_non_strings(self):
        """Test that non-string values are not affected"""
        df = pd.DataFrame({
            "npi_number": [1234567890],
            "city": [None],
            "state": [12345]
        })
        
        result = truncate_columns(df)
        
        # Non-strings should remain unchanged
        assert result.loc[0, "npi_number"] == 1234567890
        assert pd.isna(result.loc[0, "city"])
        assert result.loc[0, "state"] == 12345


class TestCSVExtraction:
    """Test suite for CSV extraction helpers"""
    
    @patch('zipfile.ZipFile')
    @patch('os.path.exists')
    @patch('os.remove')
    @patch('os.rename')
    def test_extract_csv_from_zip_success(self, mock_rename, mock_remove, mock_exists, mock_zipfile):
        """Test successful CSV extraction from ZIP"""
        mock_zip = MagicMock()
        mock_zip.namelist.return_value = ["npidata_pfile_20240101-20240131.csv", "other_file.txt"]
        mock_zipfile.return_value.__enter__.return_value = mock_zip
        mock_exists.return_value = True
        
        _extract_csv_from_zip("/tmp/test.zip")
        
        mock_zip.extract.assert_called_once()
        mock_remove.assert_called_once()
        mock_rename.assert_called_once()
    
    @patch('zipfile.ZipFile')
    def test_extract_csv_from_zip_no_match(self, mock_zipfile):
        """Test error when no matching CSV found"""
        mock_zip = MagicMock()
        mock_zip.namelist.return_value = ["other_file.txt", "wrong_file.csv"]
        mock_zipfile.return_value.__enter__.return_value = mock_zip
        
        with pytest.raises(FileNotFoundError, match="No matching npidata_pfile CSV"):
            _extract_csv_from_zip("/tmp/test.zip")
    
    @patch('os.listdir')
    @patch('os.path.isfile')
    @patch('os.remove')
    def test_cleanup_temp_directory(self, mock_remove, mock_isfile, mock_listdir):
        """Test cleanup of temporary directory"""
        from rehab_npi_puller.npi_csv_download import FINAL_CSV_PATH
        
        mock_listdir.return_value = ["npidata.csv", "temp_file.zip", "other.txt"]
        mock_isfile.return_value = True
        
        _cleanup_temp_directory()
        
        # Should remove files except FINAL_CSV_PATH
        assert mock_remove.call_count >= 2  # At least 2 files removed


class TestAsyncDownloadAndExtract:
    """Test suite for async download and extract"""
    
    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession')
    @patch('asyncio.to_thread')
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.makedirs')
    async def test_download_and_extract_csv_success(
        self, mock_makedirs, mock_file, mock_to_thread, mock_session
    ):
        """Test successful download and extraction"""
        # Mock HTTP response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.headers = {'content-length': '1000'}
        mock_response.raise_for_status = MagicMock()
        
        # Mock chunked content
        async def mock_chunks():
            yield b"chunk1"
            yield b"chunk2"
        
        mock_response.content.iter_chunked = mock_chunks
        
        mock_session_instance = AsyncMock()
        mock_session_instance.get.return_value.__aenter__.return_value = mock_response
        mock_session_instance.get.return_value.__aexit__.return_value = None
        mock_session.return_value.__aenter__.return_value = mock_session_instance
        mock_session.return_value.__aexit__.return_value = None
        
        # Mock extraction and cleanup
        mock_to_thread.side_effect = [None, None]  # Extract and cleanup
        
        result = await download_and_extract_csv()
        
        assert result.endswith("npidata.csv")
        mock_makedirs.assert_called_once()
        assert mock_to_thread.call_count == 2


class TestFilterAndDeduplicate:
    """Test suite for filtering and deduplication"""
    
    @pytest.mark.asyncio
    async def test_filter_and_deduplicate_with_matches(self, tmp_path):
        """Test filtering CSV with matching taxonomy codes"""
        # Create a temporary CSV file
        csv_path = tmp_path / "test_npi.csv"
        
        # Create test data with some matching codes
        test_data = pd.DataFrame({
            "NPI": ["123", "456", "789", "123"],  # Note duplicate
            "Healthcare Provider Taxonomy Code_1": ["324500000X", "999999999X", "3245S0500X", "324500000X"],
            "Provider Organization Name (Legal Business Name)": ["Org1", "Org2", "Org3", "Org1"]
        })
        
        # Add other required columns
        for i in range(2, 16):
            test_data[f"Healthcare Provider Taxonomy Code_{i}"] = None
        
        test_data.to_csv(csv_path, index=False)
        
        # Filter and deduplicate
        result = await filter_and_deduplicate(str(csv_path))
        
        # Should have 2 matches (123 and 789), deduplicated to 2
        assert len(result) == 2
        assert "123" in result["NPI"].values
        assert "789" in result["NPI"].values
        assert "456" not in result["NPI"].values  # Doesn't match target codes
    
    @pytest.mark.asyncio
    async def test_filter_and_deduplicate_no_matches(self, tmp_path):
        """Test filtering CSV with no matching taxonomy codes"""
        csv_path = tmp_path / "test_npi.csv"
        
        test_data = pd.DataFrame({
            "NPI": ["123", "456"],
            "Healthcare Provider Taxonomy Code_1": ["999999999X", "888888888X"]
        })
        
        for i in range(2, 16):
            test_data[f"Healthcare Provider Taxonomy Code_{i}"] = None
        
        test_data.to_csv(csv_path, index=False)
        
        result = await filter_and_deduplicate(str(csv_path))
        
        assert len(result) == 0 or result.empty


class TestParseCSVToProviders:
    """Test suite for parsing CSV to provider format"""
    
    @pytest.mark.asyncio
    @patch('rehab_npi_puller.npi_csv_download.filter_and_deduplicate')
    async def test_parse_csv_to_providers_success(self, mock_filter):
        """Test successful parsing of CSV to providers"""
        # Mock filtered dataframe
        mock_df = pd.DataFrame({
            "NPI": ["1234567890"],
            "Provider Organization Name (Legal Business Name)": ["Test Rehab"],
            "Provider First Line Business Mailing Address": ["123 Main St"],
            "Provider Business Mailing Address City Name": ["Anytown"],
            "Provider Business Mailing Address State Name": ["CA"],
            "Provider Business Mailing Address Postal Code": ["12345"],
            "Provider Business Mailing Address Telephone Number": ["555-1234"],
            "Healthcare Provider Taxonomy Code_1": ["324500000X"],
            "Healthcare Provider Taxonomy Group_1": ["Substance Abuse"],
            "Authorized Official First Name": ["John"],
            "Authorized Official Middle Name": ["Q"],
            "Authorized Official Last Name": ["Doe"],
            "Last Update Date": ["2024-01-15"]
        })
        
        mock_filter.return_value = mock_df
        
        providers = await parse_csv_to_providers("/fake/path.csv")
        
        assert len(providers) == 1
        provider = providers[0]
        assert provider["npi_number"] == "1234567890"
        assert provider["organization_name"] == "Test Rehab"
        assert provider["address"] == "123 Main St"
        assert provider["city"] == "Anytown"
        assert provider["state"] == "CA"
        assert provider["postal_code"] == "12345"
        assert provider["phone"] == "555-1234"
        assert provider["taxonomy_code"] == "324500000X"
        assert provider["authorized_official"] == "John Q Doe"
        assert provider["last_updated"] == "2024-01-15"
    
    @pytest.mark.asyncio
    @patch('rehab_npi_puller.npi_csv_download.filter_and_deduplicate')
    async def test_parse_csv_to_providers_empty(self, mock_filter):
        """Test parsing empty CSV"""
        mock_filter.return_value = pd.DataFrame()
        
        providers = await parse_csv_to_providers("/fake/path.csv")
        
        assert len(providers) == 0
    
    @pytest.mark.asyncio
    @patch('rehab_npi_puller.npi_csv_download.filter_and_deduplicate')
    async def test_parse_csv_to_providers_missing_official(self, mock_filter):
        """Test parsing with missing authorized official"""
        mock_df = pd.DataFrame({
            "NPI": ["1234567890"],
            "Provider Organization Name (Legal Business Name)": ["Test Rehab"],
            "Provider First Line Business Mailing Address": ["123 Main St"],
            "Provider Business Mailing Address City Name": ["Anytown"],
            "Provider Business Mailing Address State Name": ["CA"],
            "Provider Business Mailing Address Postal Code": ["12345"],
            "Provider Business Mailing Address Telephone Number": ["555-1234"],
            "Healthcare Provider Taxonomy Code_1": ["324500000X"],
            "Healthcare Provider Taxonomy Group_1": ["Substance Abuse"],
            "Authorized Official First Name": [None],
            "Authorized Official Middle Name": [None],
            "Authorized Official Last Name": [None],
            "Last Update Date": ["2024-01-15"]
        })
        
        mock_filter.return_value = mock_df
        
        providers = await parse_csv_to_providers("/fake/path.csv")
        
        assert len(providers) == 1
        assert providers[0]["authorized_official"] is None

