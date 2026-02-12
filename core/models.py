from pydantic import BaseModel, Field
from typing import Dict, Optional

class MetricPayload(BaseModel):
    agent_id: str
    timestamp: Optional[int] = None
    metrics: Dict[str, float]
    tags: Optional[Dict[str, str]] = Field(default_factory=dict)