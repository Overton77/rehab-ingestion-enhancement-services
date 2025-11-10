"""Main entry point for the enricher service."""

import asyncio
import sys


def main():
    """Main function for enricher service."""
    print("Starting Rehab Enricher Service...")
    print("This is where your enrichment logic would run")
    
    # Example: Import from common package
    try:
        from rehab_common.models import ProviderBase
        from rehab_common.config import DatabaseSettings
        
        print(f"✓ Successfully imported from rehab_common")
        print(f"  - ProviderBase model available")
        print(f"  - DatabaseSettings available")
        
        # Example usage
        db_settings = DatabaseSettings()
        print(f"  - Database config: {db_settings.database}")
        
    except ImportError as e:
        print(f"✗ Failed to import from rehab_common: {e}")
        sys.exit(1)
    
    # Your enricher logic here
    print("\nEnricher service ready!")


if __name__ == "__main__":
    main()

