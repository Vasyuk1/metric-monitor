from pydantic import BaseModel, Field, validator
from typing import Dict, Optional, List
import time

class MetricPayload(BaseModel):
    agent_id: str
    timestamp: int
    metrics: Dict[str, float]
    tags: Optional[Dict[str, str]] = Field(default_factory=dict)

    @validator('timestamp')
    def validate_timestamp(cls, v):
        now = int(time.time())
        if v < now - 30 * 24 * 3600:
            raise ValueError('timestamp too old (more than 30 days ago)')
        if v > now + 86400:
            raise ValueError('timestamp in future (more than 24 hours ahead)')
        return v

class MetricsBatch(BaseModel):
    batch: List[MetricPayload]

class LoginRequest(BaseModel):
    login: str
    password: str