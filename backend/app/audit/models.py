import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database import Base

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
