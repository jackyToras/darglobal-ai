from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import uuid

class Property(BaseModel):
    id: str
    platform: str
    title: str
    project_name: str
    developer: str
    brand_partner: Optional[str] = "None"
    country: str
    city: str
    district: str
    property_type: str
    listing_type: str
    price_sar: float
    currency: str
    bedrooms: int
    bathrooms: int
    area_sqm: str
    status: str
    description: str
    amenities: List[str]
    images: List[str]
    official_url: str

class ChatMessage(BaseModel):
    role: str
    content: str
    timestamp: Optional[float] = None

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    stream: bool = False
    filters: Optional[Dict[str, Any]] = None

class ChatResponse(BaseModel):
    reply: str
    session_id: str
    model_used: str
    properties: List[Dict[str, Any]] = Field(default_factory=list)
    latency_ms: float
    cached: bool = False
    guardrail_status: str = "passed"

class FilterParams(BaseModel):
    city: Optional[str] = None
    platform: Optional[str] = None
    property_type: Optional[str] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    bedrooms: Optional[int] = None
