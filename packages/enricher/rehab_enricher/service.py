"""Enricher service demonstrating cross-package imports."""

from typing import Optional
import asyncio

# Import from common package - these imports work because rehab-common
# is declared as a dependency in pyproject.toml
from rehab_common.models import ProviderBase, ProviderCreate
from rehab_common.database import Provider, EnrichmentData
from rehab_common.config import DatabaseSettings, AWSSettings


class EnricherService:
    """Service for enriching provider data.
    
    This class demonstrates:
    1. Importing shared models from rehab_common
    2. Using shared database schemas
    3. Using shared configuration
    """
    
    def __init__(self):
        self.db_settings = DatabaseSettings()
        self.aws_settings = AWSSettings()
        print(f"EnricherService initialized")
        print(f"  Database: {self.db_settings.database}")
        print(f"  AWS Region: {self.aws_settings.region}")
    
    async def enrich_provider(self, provider_npi: str) -> dict:
        """Enrich provider data.
        
        Args:
            provider_npi: The NPI to enrich
            
        Returns:
            Enrichment data dictionary
        """
        print(f"Enriching provider with NPI: {provider_npi}")
        
        # Validate using shared model
        provider = ProviderCreate(
            npi=provider_npi,
            first_name="Unknown",
            last_name="Unknown"
        )
        
        # Simulate enrichment
        await asyncio.sleep(0.1)
        
        return {
            "npi": provider.npi,
            "enriched": True,
            "source": "enricher-service"
        }
    
    def get_database_connection_string(self) -> str:
        """Get database connection string from shared config."""
        return self.db_settings.connection_string

