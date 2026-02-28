from typing import Dict, Optional, List
from pydantic import BaseModel, Field

class MetricPayload(BaseModel):
    agent_id: str
    timestamp: Optional[int] = None
    metrics: Dict[str, float]
    tags: Optional[Dict[str, str]] = Field(default_factory=dict)

class MetricsBatch(BaseModel):
    batch: List[MetricPayload]