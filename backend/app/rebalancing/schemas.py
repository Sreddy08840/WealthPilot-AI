from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

class ProposedTradeSchema(BaseModel):
    symbol: str
    action: str
    shares: float
    estimated_price: float
    tax_impact: float

    class Config:
        from_attributes = True

class RebalanceProposalSchema(BaseModel):
    proposal_id: str
    portfolio_id: str
    account_number: str
    client_name: str
    trigger_type: str
    reason: str
    created_at: datetime
    proposed_trades: List[ProposedTradeSchema]
    shap_explanations: Dict[str, Any]
    status: Optional[str] = "Pending"
    reviewer_comments: Optional[str] = None

class RebalanceTriggerRequest(BaseModel):
    trigger_type: str = "Threshold"
    portfolio_ids: Optional[List[str]] = None

class ApprovalActionRequest(BaseModel):
    action: str # APPROVED or REJECTED
    comments: Optional[str] = None
