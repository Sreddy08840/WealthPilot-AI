from datetime import datetime
from typing import Optional
from pydantic import BaseModel

class AuditLogOut(BaseModel):
    id: str
    portfolio_id: str
    event_type: str
    details: str
    state_before: Optional[str] = None
    state_after: Optional[str] = None
    timestamp: datetime

    class Config:
        from_attributes = True
