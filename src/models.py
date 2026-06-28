from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator

class IndustrialLead(BaseModel):
    id: int
    name: str = Field(default="Unknown Enterprise")
    lead_type: str = Field(..., alias="amenity")
    latitude: float
    longitude: float
    phone: Optional[str] = None
    website: Optional[str] = None
    address: Optional[str] = None

    @field_validator("name", mode="before")
    @classmethod
    def clean_name(cls, value: Any) -> str:
        if not value or str(value).strip() == "":
            return "Unknown Enterprise"
        return str(value).strip()

class ExtractorConfig(BaseModel):
    timeout: int = 30
    max_retries: int = 3
    backoff_factor: float = 2.0