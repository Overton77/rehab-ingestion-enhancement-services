"""Tests for NPI API Client"""

import pytest
import asyncio
import aiohttp
from unittest.mock import AsyncMock, MagicMock, patch
from rehab_npi_puller.npi_api_client import NPIClient


class TestNPIClient:
    """Test suite for NPIClient class"""
    
    def test_init_default_taxonomy(self):
        """Test client initialization with default taxonomy descriptions"""
        client = NPIClient()
        assert len(client.taxonomy_descriptions) == 2
        assert "Substance Abuse Rehabilitation Facility" in client.taxonomy_descriptions
        assert "Substance Abuse Treatment, Children" in client.taxonomy_descriptions
    
    def test_init_custom_taxonomy(self):
        """Test client initialization with custom taxonomy descriptions"""
        custom_taxonomies = ["Custom Taxonomy 1", "Custom Taxonomy 2"]
        client = NPIClient(taxonomy_descriptions=custom_taxonomies)
        assert client.taxonomy_descriptions == custom_taxonomies
    
    def test_calculate_backoff_delay(self):
        """Test exponential backoff calculation"""
        client = NPIClient()
        
        # Test first retry (2^0 = 1 second base)
        delay_0 = client._calculate_backoff_delay(0)
        assert 1.0 <= delay_0 <= 1.1  # 1s + 10% jitter
        
        # Test second retry (2^1 = 2 seconds base)
        delay_1 = client._calculate_backoff_delay(1)
        assert 2.0 <= delay_1 <= 2.2  # 2s + 10% jitter
        
        # Test that max delay is capped
        delay_max = client._calculate_backoff_delay(10)
        assert delay_max <= client.MAX_RETRY_DELAY * 1.1  # 32s + jitter
    
    def test_parse_npi_result_complete(self):
        """Test parsing a complete NPI API result"""
        client = NPIClient()
        
        sample_result = {
            "number": "1234567890",
            "basic": {
                "organization_name": "Test Rehab Center",
                "last_updated": "2024-01-15",
                "authorized_official_first_name": "John",
                "authorized_official_last_name": "Doe"
            },
            "taxonomies": [
                {
                    "primary": True,
                    "code": "324500000X",
                    "desc": "Substance Abuse Rehabilitation Facility"
                }
            ],
            "addresses": [
                {
                    "address_purpose": "LOCATION",
                    "address_1": "123 Main St",
                    "city": "Anytown",
                    "state": "CA",
                    "postal_code": "12345",
                    "telephone_number": "555-1234"
                }
            ]
        }
        
        result = client._parse_npi_result(sample_result)
        
        assert result["npi_number"] == "1234567890"
        assert result["organization_name"] == "Test Rehab Center"
        assert result["address"] == "123 Main St"
        assert result["city"] == "Anytown"
        assert result["state"] == "CA"
        assert result["postal_code"] == "12345"
        assert result["phone"] == "555-1234"
        assert result["taxonomy_code"] == "324500000X"
        assert result["taxonomy_desc"] == "Substance Abuse Rehabilitation Facility"
        assert result["authorized_official"] == "John Doe"
        assert result["last_updated"] == "2024-01-15"
    
    def test_parse_npi_result_minimal(self):
        """Test parsing a minimal NPI API result with missing fields"""
        client = NPIClient()
        
        minimal_result = {
            "number": "9876543210",
            "basic": {},
            "taxonomies": [],
            "addresses": []
        }
        
        result = client._parse_npi_result(minimal_result)
        
        assert result["npi_number"] == "9876543210"
        assert result["organization_name"] is None
        assert result["address"] == ""
        assert result["city"] == ""
        assert result["state"] == ""
        assert result["postal_code"] == ""
        assert result["phone"] == ""
        assert result["taxonomy_code"] is None
        assert result["taxonomy_desc"] is None
        assert result["authorized_official"] is None
    
    @pytest.mark.asyncio
    async def test_fetch_providers_by_taxonomy_description_success(self):
        """Test successful fetch from NPI API"""
        client = NPIClient()
        
        # Mock successful API response
        mock_response_data = {
            "results": [
                {"number": "1234567890", "basic": {}, "taxonomies": [], "addresses": []},
                {"number": "0987654321", "basic": {}, "taxonomies": [], "addresses": []}
            ]
        }
        
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=mock_response_data)
        mock_response.raise_for_status = MagicMock()
        
        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.get.return_value.__aexit__ = AsyncMock()
        
        results = await client.fetch_providers_by_taxonomy_description(
            "Test Taxonomy", mock_session
        )
        
        assert len(results) == 2
        assert results[0]["number"] == "1234567890"
        assert results[1]["number"] == "0987654321"
    
    @pytest.mark.asyncio
    async def test_fetch_providers_by_taxonomy_description_retry(self):
        """Test retry logic on failure"""
        client = NPIClient()
        client.RETRY_LIMIT = 2
        
        # Mock responses: first fails, second succeeds
        mock_response_fail = AsyncMock()
        mock_response_fail.status = 500
        mock_response_fail.raise_for_status = MagicMock(
            side_effect=aiohttp.ClientResponseError(None, None, status=500)
        )
        
        mock_response_success = AsyncMock()
        mock_response_success.status = 200
        mock_response_success.json = AsyncMock(return_value={"results": [{"number": "123"}]})
        mock_response_success.raise_for_status = MagicMock()
        
        mock_session = AsyncMock()
        mock_session.get = MagicMock(
            side_effect=[mock_response_fail, mock_response_success]
        )
        mock_session.get.return_value.__aenter__ = AsyncMock(
            side_effect=[mock_response_fail, mock_response_success]
        )
        mock_session.get.return_value.__aexit__ = AsyncMock()
        
        with patch('asyncio.sleep', new_callable=AsyncMock):
            results = await client.fetch_providers_by_taxonomy_description(
                "Test Taxonomy", mock_session
            )
        
        # Should succeed after retry
        assert len(results) == 1
    
    @pytest.mark.asyncio
    async def test_fetch_providers_by_taxonomy_description_rate_limit(self):
        """Test handling of rate limit (429) response"""
        client = NPIClient()
        client.RETRY_LIMIT = 2
        
        mock_response_rate_limit = AsyncMock()
        mock_response_rate_limit.status = 429
        
        mock_response_success = AsyncMock()
        mock_response_success.status = 200
        mock_response_success.json = AsyncMock(return_value={"results": []})
        mock_response_success.raise_for_status = MagicMock()
        
        mock_session = AsyncMock()
        mock_session.get = MagicMock()
        mock_session.get.return_value.__aenter__ = AsyncMock(
            side_effect=[mock_response_rate_limit, mock_response_success]
        )
        mock_session.get.return_value.__aexit__ = AsyncMock()
        
        with patch('asyncio.sleep', new_callable=AsyncMock):
            results = await client.fetch_providers_by_taxonomy_description(
                "Test Taxonomy", mock_session
            )
        
        assert isinstance(results, list)
    
    @pytest.mark.asyncio
    async def test_fetch_all_providers_from_api(self):
        """Test fetching all providers from API"""
        client = NPIClient(taxonomy_descriptions=["Test Taxonomy"])
        
        mock_results = [
            {"number": "123", "basic": {}, "taxonomies": [], "addresses": []},
            {"number": "456", "basic": {}, "taxonomies": [], "addresses": []}
        ]
        
        # Mock the fetch method
        client.fetch_providers_by_taxonomy_description = AsyncMock(
            return_value=mock_results
        )
        
        with patch('asyncio.sleep', new_callable=AsyncMock):
            providers = await client.fetch_all_providers_from_api()
        
        assert len(providers) == 2
        assert all(isinstance(p, dict) for p in providers)
    
    @pytest.mark.asyncio
    async def test_fetch_all_providers_unified_api(self):
        """Test unified fetch method with API"""
        client = NPIClient()
        
        client.fetch_all_providers_from_api = AsyncMock(return_value=[{"npi_number": "123"}])
        
        providers = await client.fetch_all_providers(method="api")
        
        assert len(providers) == 1
        client.fetch_all_providers_from_api.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_fetch_all_providers_unified_csv(self):
        """Test unified fetch method with CSV"""
        client = NPIClient()
        
        client.fetch_all_providers_from_csv = AsyncMock(return_value=[{"npi_number": "456"}])
        
        providers = await client.fetch_all_providers(method="csv")
        
        assert len(providers) == 1
        client.fetch_all_providers_from_csv.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_fetch_all_providers_invalid_method(self):
        """Test unified fetch method with invalid method"""
        client = NPIClient()
        
        with pytest.raises(ValueError, match="Invalid fetch method"):
            await client.fetch_all_providers(method="invalid")  # type: ignore

