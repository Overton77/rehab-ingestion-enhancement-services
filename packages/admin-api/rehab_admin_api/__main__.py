"""Main entry point for the admin API service."""

import sys


def main():
    """Main function for admin API service."""
    print("Starting Rehab Admin API Service...")
    
    # Example: Import from common package
    try:
        from rehab_common.models import ProviderResponse
        from rehab_common.database import Provider, EnrichmentData
        from rehab_common.config import DatabaseSettings, AWSSettings
        
        print("✓ Successfully imported from rehab_common")
        print("  - ProviderResponse model available")
        print("  - Database models available (Provider, EnrichmentData)")
        print("  - Configuration classes available")
        
    except ImportError as e:
        print(f"✗ Failed to import from rehab_common: {e}")
        sys.exit(1)
    
    # Import FastAPI app
    try:
        from rehab_admin_api.app import app
        print("✓ FastAPI app imported successfully")
        
        # For production, use uvicorn programmatically
        import uvicorn
        print("\nStarting uvicorn server on http://127.0.0.1:8000")
        uvicorn.run(app, host="127.0.0.1", port=8000)
        
    except ImportError as e:
        print(f"✗ Failed to import app: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

