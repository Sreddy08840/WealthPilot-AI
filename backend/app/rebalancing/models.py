import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Float, Text
from sqlalchemy.orm import relationship
from app.database import Base

class RebalanceProposal(Base):
    __tablename__ = "rebalance_proposals"
    
    id = Column(String, primary_key=True, default=lambda: f"prop_{uuid.uuid4().hex[:8]}")
    portfolio_id = Column(String, ForeignKey("portfolios.id"), nullable=False)
    trigger_type = Column(String, nullable=False) # Threshold, Calendar, Event
    status = Column(String, default="Pending") # Pending, Approved, Rejected, Executed
    reason = Column(String, nullable=True)
    shap_explanations = Column(Text, nullable=True) # Serialized JSON string of SHAP values
    reviewer_comments = Column(Text, nullable=True) # Supervisor comments
    created_at = Column(DateTime, default=datetime.utcnow)
    
    portfolio = relationship("Portfolio", back_populates="proposals")
    trades = relationship("ProposedTrade", back_populates="proposal", cascade="all, delete-orphan")

class ProposedTrade(Base):
    __tablename__ = "proposed_trades"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    proposal_id = Column(String, ForeignKey("rebalance_proposals.id"), nullable=False)
    asset_symbol = Column(String, ForeignKey("assets.symbol"), nullable=False)
    action = Column(String, nullable=False) # BUY or SELL
    shares = Column(Float, nullable=False)
    estimated_price = Column(Float, nullable=False)
    tax_impact = Column(Float, default=0.0) # Calculated realized gain/loss
    
    proposal = relationship("RebalanceProposal", back_populates="trades")
    asset = relationship("Asset")
