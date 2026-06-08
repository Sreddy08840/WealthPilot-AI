from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel

class AssetSchema(BaseModel):
    symbol: str
    name: str
    asset_class: str
    current_price: float

    class Config:
        from_attributes = True

class HoldingSchema(BaseModel):
    symbol: str
    name: str
    asset_class: str
    shares: float
    market_value: float
    current_weight: float
    target_weight: float
    drift: float

class AuditLogSchema(BaseModel):
    id: str
    event_type: str
    details: str
    timestamp: datetime

    class Config:
        from_attributes = True

class PortfolioListItem(BaseModel):
    id: str
    account_number: str
    client_name: str
    risk_category: str
    total_value: float
    cash_balance: float
    current_drift: float
    needs_rebalance: bool
    last_rebalanced: str

class PortfolioDetail(BaseModel):
    id: str
    account_number: str
    client_name: str
    risk_category: str
    total_value: float
    cash_balance: float
    current_drift: float
    needs_rebalance: bool
    holdings: List[HoldingSchema]
    audit_logs: List[AuditLogSchema]
