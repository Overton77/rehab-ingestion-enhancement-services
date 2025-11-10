from fastapi import FastAPI, HTTPException
import os
import boto3

# Import from common package - shared models and config
from rehab_common.models import ProviderCreate, ProviderResponse
from rehab_common.config import AWSSettings

app = FastAPI(
    title="Rehab Admin API",
    description="Admin API for managing rehab app ingestion",
    version="0.1.0"
)

# Use shared AWS settings
aws_settings = AWSSettings()
SQS_ENRICH_URL = os.getenv("SQS_ENRICH_URL", "")
sqs = boto3.client("sqs", region_name=aws_settings.region) if SQS_ENRICH_URL else None


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"ok": True, "service": "admin-api"}


@app.post("/enqueue/enrich/{npi}")
def enqueue_enrich(npi: str):
    """Enqueue a provider NPI for enrichment."""
    if not sqs:
        return {"queued": False, "reason": "SQS not configured"}
    
    # Validate NPI format (should be 10 digits)
    if len(npi) != 10 or not npi.isdigit():
        raise HTTPException(status_code=400, detail="NPI must be 10 digits")
    
    sqs.send_message(QueueUrl=SQS_ENRICH_URL, MessageBody=f'{{"npi":"{npi}"}}')
    return {"queued": True, "npi": npi}


@app.post("/providers", response_model=dict)
def create_provider(provider: ProviderCreate):
    """
    Create a new provider.
    
    This endpoint demonstrates using shared models from rehab_common.
    """
    # In a real implementation, this would save to database
    return {
        "message": "Provider would be created",
        "provider": provider.model_dump(),
        "note": "This is a demo endpoint showing cross-package imports"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)