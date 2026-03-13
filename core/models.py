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
        # Проверка: не старше 30 дней и не более чем на 5 минут вперёд
        if v < now - 30 * 24 * 3600:
            raise ValueError('timestamp too old (more than 30 days ago)')
        if v > now + 86400:  # допустим 1 час, чтобы обойти проблему времени
            raise ValueError('timestamp in future (more than 1 hour ahead)')
        return v

class MetricsBatch(BaseModel):
    batch: List[MetricPayload]