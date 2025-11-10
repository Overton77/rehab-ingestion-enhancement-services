# Cross-Package Import Examples

This file demonstrates practical examples of importing between packages in the monorepo.

## Example 1: Admin API Using Common Models

**File: `packages/admin-api/rehab_admin_api/app.py`**

```python
from fastapi import FastAPI, HTTPException
from rehab_common.models import ProviderCreate, ProviderResponse
from rehab_common.config import DatabaseSettings

app = FastAPI()
db_settings = DatabaseSettings()

@app.post("/providers", response_model=dict)
def create_provider(provider: ProviderCreate):
    """Create provider using shared model."""
    # ProviderCreate comes from rehab_common
    return {
        "npi": provider.npi,
        "name": f"{provider.first_name} {provider.last_name}"
    }
```

**How to run:**

```bash
make run-admin-dev
# Or: uv run --package rehab-admin-api uvicorn rehab_admin_api.app:app --reload
```

**Test the endpoint:**

```bash
curl -X POST http://localhost:8000/providers \
  -H "Content-Type: application/json" \
  -d '{"npi": "1234567890", "first_name": "John", "last_name": "Doe"}'
```

## Example 2: Enricher Using Common Database Models

**File: `packages/enricher/rehab_enricher/service.py`**

```python
from rehab_common.database import Provider, EnrichmentData
from rehab_common.models import ProviderCreate
from rehab_common.config import DatabaseSettings, AWSSettings

class EnricherService:
    def __init__(self):
        # Use shared configuration
        self.db_settings = DatabaseSettings()
        self.aws_settings = AWSSettings()

    async def enrich_provider(self, npi: str) -> dict:
        # Use shared models
        provider = ProviderCreate(
            npi=npi,
            first_name="Unknown",
            last_name="Unknown"
        )

        return {
            "npi": provider.npi,
            "enriched": True,
            "database": self.db_settings.database
        }
```

**File: `packages/enricher/rehab_enricher/__main__.py`**

```python
import asyncio
from rehab_enricher.service import EnricherService

async def main_async():
    service = EnricherService()
    result = await service.enrich_provider("1234567890")
    print(f"Enriched: {result}")

def main():
    asyncio.run(main_async())

if __name__ == "__main__":
    main()
```

**How to run:**

```bash
make run-enricher
# Or: uv run --package rehab-enricher python -m rehab_enricher
```

## Example 3: NPI Puller Using Common Models

**File: `packages/npi-puller/rehab_npi_puller/service.py`**

```python
from typing import List
import asyncio
from rehab_common.models import ProviderCreate
from rehab_common.config import DatabaseSettings

class NPIPullerService:
    def __init__(self):
        self.db_settings = DatabaseSettings()

    async def pull_npi_data(self, npi: str) -> ProviderCreate:
        # Simulate pulling from external API
        await asyncio.sleep(0.1)

        # Return using shared Pydantic model
        return ProviderCreate(
            npi=npi,
            first_name="Jane",
            last_name="Smith"
        )

    async def bulk_pull(self, npis: List[str]) -> List[ProviderCreate]:
        tasks = [self.pull_npi_data(npi) for npi in npis]
        return await asyncio.gather(*tasks)
```

**File: `packages/npi-puller/rehab_npi_puller/__main__.py`**

```python
import asyncio
from rehab_npi_puller.service import NPIPullerService

async def run_loop():
    service = NPIPullerService()

    # Pull some NPIs
    npis = ["1234567890", "0987654321", "1111111111"]
    results = await service.bulk_pull(npis)

    for provider in results:
        print(f"Pulled: {provider.npi} - {provider.first_name} {provider.last_name}")

def main():
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "loop":
        asyncio.run(run_loop())
    else:
        print("Usage: python -m rehab_npi_puller [loop]")

if __name__ == "__main__":
    main()
```

**How to run:**

```bash
make run-npi-loop
# Or: uv run --package rehab-npi-puller python -m rehab_npi_puller loop
```

## Example 4: Package Importing Another Service Package

If you need one service to import from another (not just common):

**Step 1: Add dependency in `pyproject.toml`**

```toml
# packages/enricher/pyproject.toml
[project]
dependencies = [
    "rehab-common",
    "rehab-npi-puller",  # Add this to use NPI puller
]
```

**Step 2: Import and use**

```python
# packages/enricher/rehab_enricher/enhanced_service.py
from rehab_npi_puller.service import NPIPullerService
from rehab_common.models import ProviderCreate

class EnhancedEnricherService:
    def __init__(self):
        # Use another package's service
        self.npi_puller = NPIPullerService()

    async def enrich_from_npi(self, npi: str):
        # Pull NPI data first
        provider = await self.npi_puller.pull_npi_data(npi)

        # Then enrich it
        return {
            "npi": provider.npi,
            "name": f"{provider.first_name} {provider.last_name}",
            "enriched": True
        }
```

**Step 3: Re-sync workspace**

```bash
make setup  # Re-sync to install new dependency
```

## Example 5: Accessing Package Configuration

**File: `packages/common/rehab_common/config.py`**

```python
from pydantic_settings import BaseSettings

class DatabaseSettings(BaseSettings):
    host: str = "localhost"
    port: int = 5432
    database: str = "rehab_app"

    model_config = {"env_prefix": "DB_"}

    @property
    def connection_string(self) -> str:
        return f"postgresql://{self.host}:{self.port}/{self.database}"
```

**Using in any package:**

```python
from rehab_common.config import DatabaseSettings

# Reads from environment variables: DB_HOST, DB_PORT, DB_DATABASE
db = DatabaseSettings()
print(db.connection_string)  # postgresql://localhost:5432/rehab_app
```

**Set environment variables:**

```bash
export DB_HOST=production-db.example.com
export DB_PORT=5432
export DB_DATABASE=prod_rehab

make run-admin  # Will use production settings
```

## Example 6: Sharing Database Models

**File: `packages/common/rehab_common/database.py`**

```python
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class Provider(Base):
    __tablename__ = "providers"

    id = Column(Integer, primary_key=True)
    npi = Column(String(10), unique=True, index=True)
    first_name = Column(String(100))
    last_name = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
```

**Using in any package:**

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from rehab_common.database import Base, Provider
from rehab_common.config import DatabaseSettings

# Get connection string from shared config
db_settings = DatabaseSettings()
engine = create_engine(db_settings.connection_string)

# Create tables
Base.metadata.create_all(engine)

# Use the session
Session = sessionmaker(bind=engine)
session = Session()

# Query using shared model
providers = session.query(Provider).filter(Provider.npi == "1234567890").all()
```

## Example 7: Complete Workflow

Here's how all packages work together:

```python
# 1. NPI Puller pulls data and saves to DB
from rehab_npi_puller.service import NPIPullerService
from rehab_common.database import Provider
from rehab_common.config import DatabaseSettings

puller = NPIPullerService()
provider_data = await puller.pull_npi_data("1234567890")
# Save to database...

# 2. Admin API triggers enrichment
from rehab_admin_api.app import app
# POST to /enqueue/enrich/1234567890
# Adds message to SQS queue

# 3. Enricher processes the NPI
from rehab_enricher.service import EnricherService
enricher = EnricherService()
enriched = await enricher.enrich_provider("1234567890")
# Enriched data saved to database
```

## Running All Services Together

**Terminal 1 - Admin API:**

```bash
make run-admin-dev
```

**Terminal 2 - NPI Puller:**

```bash
make run-npi-loop
```

**Terminal 3 - Enricher:**

```bash
make run-enricher
```

## Testing Imports

Create a test file to verify imports work:

**File: `test_imports.py` (in root)**

```python
# Test that all cross-package imports work
def test_common_imports():
    from rehab_common.models import ProviderCreate
    from rehab_common.database import Provider
    from rehab_common.config import DatabaseSettings
    print("✓ Common imports work")

def test_admin_imports():
    from rehab_admin_api.app import app
    print("✓ Admin API imports work")

def test_npi_imports():
    from rehab_npi_puller.service import NPIPullerService
    print("✓ NPI Puller imports work")

def test_enricher_imports():
    from rehab_enricher.service import EnricherService
    print("✓ Enricher imports work")

if __name__ == "__main__":
    test_common_imports()
    test_admin_imports()
    test_npi_imports()
    test_enricher_imports()
    print("\n✓ All imports successful!")
```

**Run:**

```bash
uv run python test_imports.py
```

## Key Takeaways

1. **Declare dependencies in `pyproject.toml`** - Add package names to dependencies list
2. **Import normally** - Use `from package_name.module import Class`
3. **Sync after changes** - Run `make setup` after modifying dependencies
4. **Common package** - Use for shared code (models, config, utilities)
5. **Service packages** - Can import common and each other (if declared)
