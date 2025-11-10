"""Shared Pydantic models."""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class ProviderBase(BaseModel):
    """Base provider model used across services."""
    
    npi: str = Field(..., description="10-digit National Provider Identifier")
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class ProviderCreate(ProviderBase):
    """Model for creating a provider."""
    pass


class ProviderResponse(ProviderBase):
    """Model for provider API responses."""
    
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

