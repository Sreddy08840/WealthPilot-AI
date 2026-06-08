import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database import Base

class RiskCategory(Base):
    __tablename__ = "risk_categories"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    target_allocation = Column(Text, nullable=False) # JSON string of target allocations
    
    portfolios = relationship("Portfolio", back_populates="risk_category")

class Portfolio(Base):
    __tablename__ = "portfolios"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    account_number = Column(String, unique=True, index=True, nullable=False)
    client_name = Column(String, nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
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
    asset_class = Column(String, nullable=False) # Equity, Fixed Income, Alternative, Cash
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
