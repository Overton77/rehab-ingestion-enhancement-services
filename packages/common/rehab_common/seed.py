import asyncio
from pathlib import Path
from typing import List

import pandas as pd

# These come from ariadne-codegen output
# If __init__.py re-exports them, you *might* be able to do:
#   from graphql_client import RehabApiClient, CreateProspectiveRehabInput
# but the following is the safe/explicit import:
from graphql_client.client import RehabApiClient
from graphql_client.input_types import CreateProspectiveRehabInput 
from pathlib import Path 

here = Path(__file__).parent.parent  


# Adjust if your API runs elsewhere
GRAPHQL_ENDPOINT = "http://localhost:3000/graphql"

# CSV path relative to the repo root (where you're running `uv run`)
CSV_PATH = here / "prospectiverehabs_rows.csv"

CHUNK_SIZE = 100  # how many records per createManyRehabs call


def load_rehabs_from_csv() -> List[CreateProspectiveRehabInput]:
    """
    Read the CSV with pandas and map rows to CreateProspectiveRehabInput.
    Only uses the specified columns.
    """
    if not CSV_PATH.exists():
        raise FileNotFoundError(f"CSV file not found at: {CSV_PATH.resolve()}")

    # Read as strings so we don't get weird float NaNs
    df = pd.read_csv(CSV_PATH, dtype=str)

    # Keep only the columns we care about
    expected_cols = [
        "npi_number",
        "organization_name",
        "last_updated_nppes",
        "facility_name",
        "address",
        "city",
        "state",
        "postal_code",
        "phone",
        "taxonomy_code",
        "last_updated",
    ]
    missing = [c for c in expected_cols if c not in df.columns]
    if missing:
        raise ValueError(f"CSV is missing expected columns: {missing}")

    # Drop rows that are missing required fields
    df = df.dropna(subset=["npi_number", "organization_name"])

    # Parse last_updated as datetime if present
    # (CreateProspectiveRehabInput.last_updated is a DateTime, so Python datetime is fine)
    df["last_updated_parsed"] = pd.to_datetime(
        df["last_updated"], errors="coerce", utc=True
    )

    def to_optional(value: object) -> str | None:
        if pd.isna(value):
            return None
        s = str(value).strip()
        return s or None

    items: List[CreateProspectiveRehabInput] = []

    for _, row in df.iterrows():
        last_updated = row["last_updated_parsed"]
        last_updated = None if pd.isna(last_updated) else last_updated.to_pydatetime()

        item = CreateProspectiveRehabInput(
            npi_number=str(row["npi_number"]).strip(),
            organization_name=str(row["organization_name"]).strip(),
            # If you want to prefer facility_name when org name is missing,
            # you could adjust that mapping here.

            address=to_optional(row["address"]),
            city=to_optional(row["city"]),
            state=to_optional(row["state"]),
            postal_code=to_optional(row["postal_code"]),
            phone=to_optional(row["phone"]),
            taxonomy_code=to_optional(row["taxonomy_code"]),
            taxonomy_desc=None,  # CSV doesn't have this; set if you add a column later
            last_updated=last_updated,
            # ingested defaults to false at the GraphQL level, but we can be explicit:
            ingested=False,
        )
        items.append(item)

    return items


async def seed_rehabs():
    client = RehabApiClient(GRAPHQL_ENDPOINT)

    rehabs = load_rehabs_from_csv()
    total = len(rehabs)
    print(f"Loaded {total} rehabs from CSV")

    if total == 0:
        print("Nothing to seed. Exiting.")
        return

    # Send in chunks so we don't blow up any GraphQL limits
    for start in range(0, total, CHUNK_SIZE):
        end = min(start + CHUNK_SIZE, total)
        batch = rehabs[start:end]
        print(f"Seeding rehabs {start + 1}..{end} of {total}")

        # This calls your `CreateManyRehabs` mutation:
        # mutation CreateManyRehabs($data: [CreateProspectiveRehabInput!]!) { ... }
        resp = await client.create_many_rehabs(data=batch)

        # Depending on how ariadne-codegen named the field, you may have:
        #   resp.create_many_rehabs
        # or it may mirror the GraphQL field name exactly.
        # You can print `resp` to see its structure if unsure.
        print("Batch completed:", resp)

    print("Seeding complete ✅")


if __name__ == "__main__": 
    print(here)
    asyncio.run(seed_rehabs())
    