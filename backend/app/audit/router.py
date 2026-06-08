from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.audit.models import AuditLog
from app.audit.schemas import AuditLogOut

router = APIRouter(prefix="/audit", tags=["Audit Trails"])

@router.get("/logs", response_model=Dict[str, Any])
def get_audit_logs(
    page: int = 1,
    limit: int = 20,
    event_type: Optional[str] = None,
    portfolio_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve audit logs across system events (Authenticated)"""
    query = db.query(AuditLog)
    
    if event_type:
        query = query.filter(AuditLog.event_type == event_type)
        
    if portfolio_id:
        query = query.filter(AuditLog.portfolio_id == portfolio_id)
        
    total = query.count()
    logs = query.order_by(AuditLog.timestamp.desc()).offset((page - 1) * limit).limit(limit).all()
    
    return {
        "total": total,
        "page": page,
        "limit": limit,
        "data": [AuditLogOut.from_orm(l) for l in logs]
    }
