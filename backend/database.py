import os
import uuid
from datetime import datetime
from sqlalchemy import create_engine, Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./wealthpilot.db")

engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class RiskCategory(Base):
    __tablename__ = "risk_categories"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    # Target allocation serialized as JSON, e.g. {"SPY": 0.60, "AGG": 0.30, "GLD": 0.05, "BIL": 0.05}
    target_allocation = Column(Text, nullable=False)
    
    portfolios = relationship("Portfolio", back_populates="risk_category")

class Portfolio(Base):
    __tablename__ = "portfolios"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    account_number = Column(String, unique=True, index=True, nullable=False)
    client_name = Column(String, nullable=False)
    risk_category_id = Column(Integer, ForeignKey("risk_categories.id"), nullable=False)
    current_value = Column(Float, default=0.0)
    cash_balance = Column(Float, default=0.0)
    last_rebalanced = Column(DateTime, default=datetime.utcnow)
    auto_rebalance = Column(Boolean, default=False)
    
    risk_category = relationship("RiskCategory", back_populates="portfolios")
    holdings = relationship("PortfolioHolding", back_populates="portfolio", cascade="all, delete-orphan")
    tax_lots = relationship("TaxLot", back_populates="portfolio", cascade="all, delete-orphan")
    proposals = relationship("RebalanceProposal", back_populates="portfolio", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="portfolio", cascade="all, delete-orphan")

class Asset(Base):
    __tablename__ = "assets"
    
    symbol = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    asset_class = Column(String, nullable=False) # e.g. Equity, Fixed Income, Alternative, Cash
    current_price = Column(Float, nullable=False)

class PortfolioHolding(Base):
    __tablename__ = "portfolio_holdings"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    portfolio_id = Column(String, ForeignKey("portfolios.id"), nullable=False)
    asset_symbol = Column(String, ForeignKey("assets.symbol"), nullable=False)
    shares = Column(Float, default=0.0)
    market_value = Column(Float, default=0.0)
    
    portfolio = relationship("Portfolio", back_populates="holdings")
    asset = relationship("Asset")

class TaxLot(Base):
    __tablename__ = "tax_lots"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    portfolio_id = Column(String, ForeignKey("portfolios.id"), nullable=False)
    asset_symbol = Column(String, ForeignKey("assets.symbol"), nullable=False)
    shares = Column(Float, nullable=False)
    purchase_price = Column(Float, nullable=False)
    purchase_date = Column(DateTime, nullable=False)
    is_harvested = Column(Boolean, default=False)
    
    portfolio = relationship("Portfolio", back_populates="tax_lots")
    asset = relationship("Asset")

class RebalanceProposal(Base):
    __tablename__ = "rebalance_proposals"
    
    id = Column(String, primary_key=True, default=lambda: f"prop_{uuid.uuid4().hex[:8]}")
    portfolio_id = Column(String, ForeignKey("portfolios.id"), nullable=False)
    trigger_type = Column(String, nullable=False) # Threshold, Calendar, Event
    status = Column(String, default="Pending") # Pending, Approved, Rejected, Executed
    reason = Column(String, nullable=True)
    # Serialized SHAP values: e.g. {"drift_magnitude": 0.45, "tax_savings": 0.35, "market_volatility": 0.15, ...}
    shap_explanations = Column(Text, nullable=True)
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

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    portfolio_id = Column(String, ForeignKey("portfolios.id"), nullable=False)
    event_type = Column(String, nullable=False) # Trigger, AgentRun, OrderApproval, OrderExecution, ComplianceFailure
    details = Column(Text, nullable=False)
    state_before = Column(Text, nullable=True) # JSON snapshot
    state_after = Column(Text, nullable=True) # JSON snapshot
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    portfolio = relationship("Portfolio", back_populates="audit_logs")

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
