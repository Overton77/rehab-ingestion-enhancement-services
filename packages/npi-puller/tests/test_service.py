"""Tests for NPI Service"""

import pytest
import sys
from unittest.mock import AsyncMock, MagicMock, patch
from rehab_npi_puller.service import (
    convert_to_rehab_input,
    ingest_npi_providers,
    main
)


class TestConvertToRehabInput:
    """Test suite for converting provider to rehab input"""
    
    def test_convert_to_rehab_input_complete(self):
        """Test converting a complete provider dictionary"""
        provider = {
            "npi_number": "1234567890",
            "organization_name": "Test Rehab Center",
            "address": "123 Main St",
            "city": "Anytown",
            "state": "CA",
            "postal_code": "12345",
            "phone": "555-1234",
            "taxonomy_code": "324500000X",
            "taxonomy_desc": "Substance Abuse Rehabilitation Facility",
            "authorized_official": "John Doe",
            "last_updated": "2024-01-15"
        }
        
        with patch('graphql_client.input_types.CreateProspectiveRehabInput') as mock_input:
            convert_to_rehab_input(provider)
            
            mock_input.assert_called_once_with(
                npi_number="1234567890",
                organization_name="Test Rehab Center",
                address="123 Main St",
                city="Anytown",
                state="CA",
                postal_code="12345",
                phone="555-1234",
                taxonomy_code="324500000X",
                taxonomy_desc="Substance Abuse Rehabilitation Facility",
                authorized_official="John Doe",
                last_updated="2024-01-15"
            )
    
    def test_convert_to_rehab_input_minimal(self):
        """Test converting a minimal provider dictionary"""
        provider = {
            "npi_number": "1234567890",
            "organization_name": None,
            "address": None,
            "city": None,
            "state": None,
            "postal_code": None,
            "phone": None,
            "taxonomy_code": None,
            "taxonomy_desc": None,
            "authorized_official": None,
            "last_updated": None
        }
        
        with patch('graphql_client.input_types.CreateProspectiveRehabInput') as mock_input:
            convert_to_rehab_input(provider)
            
            mock_input.assert_called_once()


class TestIngestNPIProviders:
    """Test suite for the main ingestion function"""
    
    @pytest.mark.asyncio
    @patch('rehab_npi_puller.service.NPIClient')
    @patch('rehab_npi_puller.service.batch_create_rehabs')
    @patch('graphql_client.input_types.CreateProspectiveRehabInput')
    async def test_ingest_npi_providers_api_success(
        self, mock_input, mock_batch_create, mock_client_class
    ):
        """Test successful ingestion using API method"""
        # Mock providers
        mock_providers = [
            {
                "npi_number": "123",
                "organization_name": "Rehab 1",
                "address": "123 St",
                "city": "City1",
                "state": "CA",
                "postal_code": "12345",
                "phone": "555-1234",
                "taxonomy_code": "324500000X",
                "taxonomy_desc": "Rehab",
                "authorized_official": "John Doe",
                "last_updated": "2024-01-01"
            },
            {
                "npi_number": "456",
                "organization_name": "Rehab 2",
                "address": "456 Ave",
                "city": "City2",
                "state": "NY",
                "postal_code": "67890",
                "phone": "555-5678",
                "taxonomy_code": "3245S0500X",
                "taxonomy_desc": "Children Treatment",
                "authorized_official": "Jane Smith",
                "last_updated": "2024-01-02"
            }
        ]
        
        # Mock NPIClient
        mock_client = AsyncMock()
        mock_client.fetch_all_providers = AsyncMock(return_value=mock_providers)
        mock_client_class.return_value = mock_client
        
        # Mock rehab input creation
        mock_input.return_value = MagicMock()
        
        # Mock batch create response
        mock_batch_create.return_value = {
            "total_successes": 2,
            "total_errors": 0,
            "responses": []
        }
        
        result = await ingest_npi_providers(method="api", chunk_size=100)
        
        assert result["total_successes"] == 2
        assert result["total_errors"] == 0
        mock_client.fetch_all_providers.assert_called_once_with(method="api")
        mock_batch_create.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('rehab_npi_puller.service.NPIClient')
    @patch('rehab_npi_puller.service.batch_create_rehabs')
    @patch('graphql_client.input_types.CreateProspectiveRehabInput')
    async def test_ingest_npi_providers_csv_success(
        self, mock_input, mock_batch_create, mock_client_class
    ):
        """Test successful ingestion using CSV method"""
        mock_providers = [
            {
                "npi_number": "789",
                "organization_name": "CSV Rehab",
                "address": "789 Blvd",
                "city": "City3",
                "state": "TX",
                "postal_code": "54321",
                "phone": "555-9999",
                "taxonomy_code": "324500000X",
                "taxonomy_desc": "Rehab",
                "authorized_official": "Bob Jones",
                "last_updated": "2024-01-03"
            }
        ]
        
        mock_client = AsyncMock()
        mock_client.fetch_all_providers = AsyncMock(return_value=mock_providers)
        mock_client_class.return_value = mock_client
        
        mock_input.return_value = MagicMock()
        
        mock_batch_create.return_value = {
            "total_successes": 1,
            "total_errors": 0,
            "responses": []
        }
        
        result = await ingest_npi_providers(method="csv", chunk_size=50)
        
        assert result["total_successes"] == 1
        assert result["total_errors"] == 0
        mock_client.fetch_all_providers.assert_called_once_with(method="csv")
    
    @pytest.mark.asyncio
    @patch('rehab_npi_puller.service.NPIClient')
    async def test_ingest_npi_providers_no_providers(self, mock_client_class):
        """Test ingestion when no providers are found"""
        mock_client = AsyncMock()
        mock_client.fetch_all_providers = AsyncMock(return_value=[])
        mock_client_class.return_value = mock_client
        
        result = await ingest_npi_providers(method="api")
        
        assert result["total_successes"] == 0
        assert result["total_errors"] == 0
        assert result["responses"] == []
    
    @pytest.mark.asyncio
    @patch('rehab_npi_puller.service.NPIClient')
    async def test_ingest_npi_providers_fetch_error(self, mock_client_class):
        """Test error handling during provider fetch"""
        mock_client = AsyncMock()
        mock_client.fetch_all_providers = AsyncMock(
            side_effect=Exception("API Error")
        )
        mock_client_class.return_value = mock_client
        
        with pytest.raises(Exception, match="API Error"):
            await ingest_npi_providers(method="api")
    
    @pytest.mark.asyncio
    @patch('rehab_npi_puller.service.NPIClient')
    @patch('rehab_npi_puller.service.batch_create_rehabs')
    @patch('graphql_client.input_types.CreateProspectiveRehabInput')
    async def test_ingest_npi_providers_conversion_errors(
        self, mock_input, mock_batch_create, mock_client_class
    ):
        """Test handling of conversion errors"""
        mock_providers = [
            {"npi_number": "123", "organization_name": "Rehab 1"},
            {"npi_number": "456", "organization_name": "Rehab 2"}
        ]
        
        mock_client = AsyncMock()
        mock_client.fetch_all_providers = AsyncMock(return_value=mock_providers)
        mock_client_class.return_value = mock_client
        
        # First conversion succeeds, second fails
        mock_input.side_effect = [MagicMock(), Exception("Conversion Error")]
        
        mock_batch_create.return_value = {
            "total_successes": 1,
            "total_errors": 0,
            "responses": []
        }
        
        result = await ingest_npi_providers(method="api")
        
        # Should still process the successful one
        assert result["total_successes"] == 1
    
    @pytest.mark.asyncio
    @patch('rehab_npi_puller.service.NPIClient')
    @patch('rehab_npi_puller.service.batch_create_rehabs')
    @patch('graphql_client.input_types.CreateProspectiveRehabInput')
    async def test_ingest_npi_providers_database_error(
        self, mock_input, mock_batch_create, mock_client_class
    ):
        """Test error handling during database save"""
        mock_providers = [{"npi_number": "123"}]
        
        mock_client = AsyncMock()
        mock_client.fetch_all_providers = AsyncMock(return_value=mock_providers)
        mock_client_class.return_value = mock_client
        
        mock_input.return_value = MagicMock()
        mock_batch_create.side_effect = Exception("Database Error")
        
        with pytest.raises(Exception, match="Database Error"):
            await ingest_npi_providers(method="api")
    
    @pytest.mark.asyncio
    @patch('rehab_npi_puller.service.NPIClient')
    @patch('rehab_npi_puller.service.batch_create_rehabs')
    @patch('graphql_client.input_types.CreateProspectiveRehabInput')
    async def test_ingest_npi_providers_custom_taxonomies(
        self, mock_input, mock_batch_create, mock_client_class
    ):
        """Test ingestion with custom taxonomy descriptions"""
        custom_taxonomies = ["Custom Taxonomy 1"]
        
        mock_client = AsyncMock()
        mock_client.fetch_all_providers = AsyncMock(return_value=[])
        mock_client_class.return_value = mock_client
        
        await ingest_npi_providers(
            method="api",
            taxonomy_descriptions=custom_taxonomies
        )
        
        mock_client_class.assert_called_once_with(
            taxonomy_descriptions=custom_taxonomies
        )


class TestMain:
    """Test suite for CLI main function"""
    
    @pytest.mark.asyncio
    @patch('rehab_npi_puller.service.ingest_npi_providers')
    @patch('sys.argv', ['service.py', 'api'])
    async def test_main_api_method(self, mock_ingest):
        """Test main function with API method argument"""
        mock_ingest.return_value = {
            "total_successes": 5,
            "total_errors": 0,
            "responses": []
        }
        
        with pytest.raises(SystemExit) as exc_info:
            await main()
        
        assert exc_info.value.code == 0
        mock_ingest.assert_called_once_with(method="api")
    
    @pytest.mark.asyncio
    @patch('rehab_npi_puller.service.ingest_npi_providers')
    @patch('sys.argv', ['service.py', 'csv'])
    async def test_main_csv_method(self, mock_ingest):
        """Test main function with CSV method argument"""
        mock_ingest.return_value = {
            "total_successes": 10,
            "total_errors": 0,
            "responses": []
        }
        
        with pytest.raises(SystemExit) as exc_info:
            await main()
        
        assert exc_info.value.code == 0
        mock_ingest.assert_called_once_with(method="csv")
    
    @pytest.mark.asyncio
    @patch('rehab_npi_puller.service.ingest_npi_providers')
    @patch('sys.argv', ['service.py'])
    async def test_main_default_method(self, mock_ingest):
        """Test main function with default (API) method"""
        mock_ingest.return_value = {
            "total_successes": 3,
            "total_errors": 0,
            "responses": []
        }
        
        with pytest.raises(SystemExit) as exc_info:
            await main()
        
        assert exc_info.value.code == 0
        mock_ingest.assert_called_once_with(method="api")
    
    @pytest.mark.asyncio
    @patch('sys.argv', ['service.py', 'invalid'])
    async def test_main_invalid_method(self):
        """Test main function with invalid method argument"""
        with pytest.raises(SystemExit) as exc_info:
            await main()
        
        assert exc_info.value.code == 1
    
    @pytest.mark.asyncio
    @patch('rehab_npi_puller.service.ingest_npi_providers')
    @patch('sys.argv', ['service.py', 'api'])
    async def test_main_with_errors(self, mock_ingest):
        """Test main function when ingestion has errors"""
        mock_ingest.return_value = {
            "total_successes": 5,
            "total_errors": 2,
            "responses": []
        }
        
        with pytest.raises(SystemExit) as exc_info:
            await main()
        
        assert exc_info.value.code == 1
    
    @pytest.mark.asyncio
    @patch('rehab_npi_puller.service.ingest_npi_providers')
    @patch('sys.argv', ['service.py', 'api'])
    async def test_main_keyboard_interrupt(self, mock_ingest):
        """Test main function handling KeyboardInterrupt"""
        mock_ingest.side_effect = KeyboardInterrupt()
        
        with pytest.raises(SystemExit) as exc_info:
            await main()
        
        assert exc_info.value.code == 130
    
    @pytest.mark.asyncio
    @patch('rehab_npi_puller.service.ingest_npi_providers')
    @patch('sys.argv', ['service.py', 'api'])
    async def test_main_exception(self, mock_ingest):
        """Test main function handling general exception"""
        mock_ingest.side_effect = Exception("Unexpected error")
        
        with pytest.raises(SystemExit) as exc_info:
            await main()
        
        assert exc_info.value.code == 1

