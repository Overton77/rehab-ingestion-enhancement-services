"""Main entry point for the NPI puller service."""

import asyncio
import sys


async def run_loop():
    """Run the NPI puller loop."""
    print("Running NPI puller loop...")
    
    # Example: Import from common package
    try:
        from rehab_common.models import ProviderCreate
        from rehab_common.database import Provider
        
        print("✓ Successfully imported from rehab_common")
        print("  - ProviderCreate model available")
        print("  - Provider database model available")
        
        # Example: Create a provider instance
        provider = ProviderCreate(
            npi="1234567890",
            first_name="John",
            last_name="Doe"
        )
        print(f"  - Created provider: {provider.npi}")
        
    except ImportError as e:
        print(f"✗ Failed to import from rehab_common: {e}")
        sys.exit(1)
    
    # Your NPI pulling logic here
    print("\nNPI Puller service ready!")


def main():
    """Main function for NPI puller service."""
    print("Starting Rehab NPI Puller Service...")
    
    # Check for command line arguments
    if len(sys.argv) > 1 and sys.argv[1] == "loop":
        asyncio.run(run_loop())
    else:
        print("Usage: python -m rehab_npi_puller [loop]")
        print("  loop: Run the continuous pulling loop")


if __name__ == "__main__":
    main()

