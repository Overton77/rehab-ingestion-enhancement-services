# Python Monorepo Setup Guide

This guide explains how the monorepo is structured and how to work with it.

## 🏗️ Structure

```
rehab-app-ingestion/
├── pyproject.toml              # Root workspace configuration
├── Makefile                    # Convenient commands
├── packages/
│   ├── common/                 # Shared utilities and models
│   │   ├── pyproject.toml
│   │   └── rehab_common/
│   │       ├── __init__.py
│   │       ├── models.py       # Shared Pydantic models
│   │       ├── database.py     # SQLAlchemy models
│   │       └── config.py       # Shared configuration
│   │
│   ├── admin-api/             # FastAPI admin service
│   │   ├── pyproject.toml
│   │   └── rehab_admin_api/
│   │       ├── __init__.py
│   │       ├── __main__.py     # Entry point
│   │       └── app.py          # FastAPI app
│   │
│   ├── npi-puller/            # NPI pulling service
│   │   ├── pyproject.toml
│   │   └── rehab_npi_puller/
│   │       ├── __init__.py
│   │       ├── __main__.py     # Entry point
│   │       └── service.py
│   │
│   └── enricher/              # Data enrichment service
│       ├── pyproject.toml
│       └── rehab_enricher/
│           ├── __init__.py
│           ├── __main__.py     # Entry point
│           └── service.py
```

## 🚀 Quick Start

### 1. Initial Setup

```bash
# Sync all packages and install dependencies
make setup

# Or directly with uv
uv sync --all-packages
```

### 2. Running Services

```bash
# Run any service using Make
make run-admin       # Admin API
make run-npi         # NPI Puller
make run-enricher    # Enricher

# Or run with uv directly
uv run --package rehab-admin-api python -m rehab_admin_api
uv run --package rehab-npi-puller python -m rehab_npi_puller
uv run --package rehab-enricher python -m rehab_enricher

# Run admin API in development mode (with hot reload)
make run-admin-dev
```

### 3. Development Commands

```bash
make help           # Show all available commands
make lint           # Run linter
make format         # Format code
make type           # Type checking
make test           # Run tests
make clean          # Clean cache files
```

## 📦 Package Structure

### Each Package Contains:

1. **pyproject.toml** - Package configuration with:

   - Package name (e.g., `rehab-admin-api`)
   - Dependencies (including other workspace packages)
   - Build configuration

2. **Module Directory** (e.g., `rehab_admin_api/`)
   - `__init__.py` - Package initialization
   - `__main__.py` - Entry point for `python -m package_name`
   - Other module files

## 🔗 Cross-Package Imports

### How It Works

1. **Declare Dependency** in `pyproject.toml`:

```toml
[project]
dependencies = [
    "rehab-common",  # Import the common package
    "other-deps>=1.0.0",
]
```

2. **Import in Code**:

```python
# In any package that depends on rehab-common
from rehab_common.models import ProviderCreate
from rehab_common.database import Provider
from rehab_common.config import DatabaseSettings

# Use the shared models
provider = ProviderCreate(npi="1234567890", first_name="John", last_name="Doe")
db_settings = DatabaseSettings()
```

### Example: Admin API Importing Common

**File: `packages/admin-api/pyproject.toml`**

```toml
dependencies = [
    "rehab-common",  # Declare dependency
    "fastapi>=0.121.1",
]
```

**File: `packages/admin-api/rehab_admin_api/app.py`**

```python
from fastapi import FastAPI
from rehab_common.models import ProviderCreate  # Import works!
from rehab_common.config import AWSSettings

app = FastAPI()
aws_settings = AWSSettings()

@app.post("/providers")
def create_provider(provider: ProviderCreate):
    return {"provider": provider.model_dump()}
```

## 🎯 Running Packages

### Method 1: Using Make (Recommended)

```bash
make run-admin        # Simple
make run-admin-dev    # With hot reload for admin API
make run-npi-loop     # NPI puller in loop mode
```

### Method 2: Using uv with --package

```bash
# Run a specific package
uv run --package rehab-admin-api python -m rehab_admin_api
uv run --package rehab-npi-puller python -m rehab_npi_puller loop
uv run --package rehab-enricher python -m rehab_enricher
```

### Method 3: Using installed scripts

After `make setup`, you can use the installed scripts:

```bash
uv run rehab-admin-api
uv run rehab-npi-puller
uv run rehab-enricher
```

### Method 4: Direct Module Execution

```bash
# From the package directory
cd packages/admin-api
uv run python -m rehab_admin_api

# Or with -m from root
uv run -p packages/admin-api python -m rehab_admin_api
```

## 📝 Running Submodules

### Example: Running a specific module function

**Create a file: `packages/enricher/rehab_enricher/service.py`**

```python
from rehab_common.models import ProviderCreate

class EnricherService:
    def enrich(self, npi: str):
        print(f"Enriching {npi}")
        return ProviderCreate(npi=npi, first_name="Test", last_name="User")
```

**Run it from `__main__.py`:**

```python
# packages/enricher/rehab_enricher/__main__.py
from rehab_enricher.service import EnricherService

def main():
    service = EnricherService()
    result = service.enrich("1234567890")
    print(result)

if __name__ == "__main__":
    main()
```

**Execute:**

```bash
uv run --package rehab-enricher python -m rehab_enricher
```

## 🔧 Adding a New Package

1. **Create package structure:**

```bash
mkdir -p packages/new-package/rehab_new_package
touch packages/new-package/pyproject.toml
touch packages/new-package/README.md
touch packages/new-package/rehab_new_package/__init__.py
touch packages/new-package/rehab_new_package/__main__.py
```

2. **Create `pyproject.toml`:**

```toml
[project]
name = "rehab-new-package"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "rehab-common",  # Add common package
]

[project.scripts]
rehab-new-package = "rehab_new_package.__main__:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["rehab_new_package"]
```

3. **Add to workspace in root `pyproject.toml`:**

```toml
[tool.uv.workspace]
members = [
  "packages/common",
  "packages/new-package",  # Add this line
  # ... other packages
]
```

4. **Sync workspace:**

```bash
make setup
```

## 📚 Best Practices

### 1. **Shared Code Goes in Common**

- Database models → `rehab_common/database.py`
- Pydantic models → `rehab_common/models.py`
- Configuration → `rehab_common/config.py`
- Utilities → `rehab_common/utils.py`

### 2. **Package Naming**

- Project name: `rehab-package-name` (with hyphens)
- Module name: `rehab_package_name` (with underscores)
- Import as: `from rehab_package_name import something`

### 3. **Dependencies**

- Always declare package dependencies in `pyproject.toml`
- Use workspace packages by name: `"rehab-common"`
- Version external packages: `"fastapi>=0.121.1"`

### 4. **Entry Points**

- Use `__main__.py` for executable packages
- Define `main()` function
- Register in `[project.scripts]`

### 5. **Testing**

```bash
# Run all tests
make test

# Test specific package
uv run --package rehab-admin-api pytest packages/admin-api/tests/
```

## 🐛 Troubleshooting

### Import errors?

```bash
# Re-sync packages
make setup

# Check installed packages
uv tree
```

### Module not found?

- Ensure package is listed in workspace `members`
- Check dependency declared in `pyproject.toml`
- Verify module name matches directory name

### Changes not reflected?

```bash
# Clean and reinstall
make clean
make setup
```

## 📖 Additional Resources

- [uv Documentation](https://github.com/astral-sh/uv)
- [Python Packaging Guide](https://packaging.python.org/)
- Run `make help` to see all available commands
