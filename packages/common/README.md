# Rehab Common

Common utilities, models, and database schemas shared across all rehab-app-ingestion packages.

## Contents

- Database schemas and models (SQLModel)
- Shared utilities
- Common configurations
- Data models used across services

## Database Setup

### 1. Create .env file

Copy `.env.example` to `.env` in this directory:

```bash
cp .env.example .env
```

Then fill in your AWS RDS credentials (get password from AWS Secrets Manager).

### 2. Run Migrations

From the `packages/common` directory:

```bash
# Create a new migration (after changing models)
uv run alembic revision --autogenerate -m "description of changes"

# Apply migrations
uv run alembic upgrade head

# Downgrade one version
uv run alembic downgrade -1

# Show current version
uv run alembic current

# Show migration history
uv run alembic history
```

### 3. Get RDS Password

If using AWS RDS with Secrets Manager:

```bash
# Get the secret name from CDK output
aws secretsmanager get-secret-value \
  --secret-id <your-secret-name> \
  --query SecretString \
  --output text | jq -r .password
```

## Models

### ProspectiveRehabs

Table for tracking prospective rehabilitation facilities from NPI data.

### InsuranceProvider

Table for insurance provider information.

## Usage in Other Packages

```python
from rehab_common.models import ProspectiveRehabs, InsuranceProvider
from rehab_common.database import AsyncSessionLocal, init_models

# Use async session
async with AsyncSessionLocal() as session:
    result = await session.execute(select(ProspectiveRehabs))
    rehabs = result.scalars().all()
```
