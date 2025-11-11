"""NPI Puller service demonstrating cross-package imports."""

from typing import List, Optional
import asyncio

# Import from common package
rehab_common.models 

class NPIPullerService:
    """Service for pulling NPI data.
    
    This class demonstrates:
    1. Importing shared models from rehab_common
    2. Using shared database schemas
    3. Using shared configuration
    """
    
    def __init__(self):
        self.db_settings = DatabaseSettings()
        print(f"NPIPullerService initialized")
        print(f"  Database: {self.db_settings.database}")
    
    async def pull_npi_data(self, npi: str) -> ProviderCreate:
        """Pull NPI data from external API.
        
        Args:
            npi: The NPI to pull
            
        Returns:
            ProviderCreate model with the pulled data
        """
        print(f"Pulling NPI data for: {npi}")
        
        # Simulate API call
        await asyncio.sleep(0.1)
        
        # Return using shared model
        return ProviderCreate(
            npi=npi,
            first_name="John",
            last_name="Doe"
        )
    
    async def bulk_pull(self, npis: List[str]) -> List[ProviderCreate]:
        """Pull multiple NPIs concurrently."""
        tasks = [self.pull_npi_data(npi) for npi in npis]
        return await asyncio.gather(*tasks)

