import asyncio
import sys
from typing import List, Optional
from rehab_common.rehab_sdk import batch_create_rehabs
from rehab_common.graphql_client.input_types import CreateProspectiveRehabInput
from rehab_npi_puller.npi_api_client import NPIClient, FetchMethod


def convert_to_rehab_input(provider: dict) -> CreateProspectiveRehabInput:
    """
    Convert a provider dictionary to CreateProspectiveRehabInput.
    
    Args:
        provider: Provider dictionary from NPI API or CSV
        
    Returns:
        CreateProspectiveRehabInput object
    """
    return CreateProspectiveRehabInput(
        npi_number=provider.get("npi_number"),
        organization_name=provider.get("organization_name"),
        address=provider.get("address"),
        city=provider.get("city"),
        state=provider.get("state"),
        postal_code=provider.get("postal_code"),
        phone=provider.get("phone"),
        taxonomy_code=provider.get("taxonomy_code"),
        taxonomy_desc=provider.get("taxonomy_desc"),
        authorized_official=provider.get("authorized_official"),
        last_updated=provider.get("last_updated")
    )


async def ingest_npi_providers(
    method: FetchMethod = "api",
    taxonomy_descriptions: Optional[List[str]] = None,
    chunk_size: int = 100
) -> dict:
    """
    Main ingestion function that fetches NPI providers and saves them to the database.
    
    Args:
        method: Either "api" or "csv" for fetching providers
        taxonomy_descriptions: List of taxonomy descriptions to filter by (API method only)
        chunk_size: Number of records to batch when creating rehabs
        
    Returns:
        Dictionary with ingestion results (total_successes, total_errors, etc.)
    """
    print(f"\n{'='*60}")
    print(f"NPI PROVIDER INGESTION - METHOD: {method.upper()}")
    print(f"{'='*60}\n")
    
    # Initialize NPI Client
    client = NPIClient(taxonomy_descriptions=taxonomy_descriptions)
    
    # Fetch providers
    try:
        providers = await client.fetch_all_providers(method=method)
    except Exception as e:
        print(f"❌ Error fetching providers: {e}")
        raise
    
    if not providers:
        print("⚠️  No providers found. Exiting.")
        return {
            "total_successes": 0,
            "total_errors": 0,
            "responses": []
        }
    
    print(f"\n📊 Total providers fetched: {len(providers)}")
    print(f"💾 Converting to rehab input format...")
    
    # Convert to CreateProspectiveRehabInput
    rehab_inputs = []
    conversion_errors = 0
    for provider in providers:
        try:
            rehab_input = convert_to_rehab_input(provider)
            rehab_inputs.append(rehab_input)
        except Exception as e:
            conversion_errors += 1
            print(f"⚠️  Error converting provider {provider.get('npi_number')}: {e}")
    
    if conversion_errors > 0:
        print(f"⚠️  {conversion_errors} providers failed conversion")
    
    print(f"✅ Successfully converted {len(rehab_inputs)} providers to rehab input format")
    
    # Save to database
    print(f"\n💾 Saving {len(rehab_inputs)} rehabs to database (chunk_size={chunk_size})...")
    try:
        result = await batch_create_rehabs(data=rehab_inputs, chunk_size=chunk_size)
        print(f"\n{'='*60}")
        print(f"INGESTION COMPLETE")
        print(f"{'='*60}")
        print(f"✅ Total successes: {result['total_successes']}")
        print(f"❌ Total errors: {result['total_errors']}")
        print(f"{'='*60}\n")
        return result
    except Exception as e:
        print(f"❌ Error saving to database: {e}")
        raise


async def main():
    """
    CLI entry point for NPI provider ingestion.
    
    Usage:
        python -m rehab_npi_puller.service [api|csv]
    """
    # Parse command line arguments
    method: FetchMethod = "api"
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        if arg in ["api", "csv"]:
            method = arg  # type: ignore
        else:
            print(f"❌ Invalid method: {arg}. Must be 'api' or 'csv'.")
            print("Usage: python -m rehab_npi_puller.service [api|csv]")
            sys.exit(1)
    
    try:
        result = await ingest_npi_providers(method=method)
        
        # Exit with appropriate code
        if result['total_errors'] > 0:
            sys.exit(1)
        else:
            sys.exit(0)
    except KeyboardInterrupt:
        print("\n⚠️  Ingestion interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Ingestion failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
