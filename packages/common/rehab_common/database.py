"""Database schemas and models."""

from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class Provider(Base):
    """Provider model - example database schema."""
    
    __tablename__ = "providers"
    
    id = Column(Integer, primary_key=True, index=True)
    npi = Column(String(10), unique=True, index=True, nullable=False)
    first_name = Column(String(100))
    last_name = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<Provider(npi={self.npi}, name={self.first_name} {self.last_name})>"


class EnrichmentData(Base):
    """Enrichment data model - example database schema."""
    
    __tablename__ = "enrichment_data"
    
    id = Column(Integer, primary_key=True, index=True)
    provider_npi = Column(String(10), index=True, nullable=False)
    data_source = Column(String(100))
    data = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<EnrichmentData(npi={self.provider_npi}, source={self.data_source})>"

