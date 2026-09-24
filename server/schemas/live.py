from typing import Any, Dict, Optional
from pydantic import BaseModel


class LiveMetricEvent(BaseModel):
    metric: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
