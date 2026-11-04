from typing import Any

from pydantic import BaseModel


class LiveMetricEvent(BaseModel):
    metric: str
    data: dict[str, Any] | None = None
    error: str | None = None
