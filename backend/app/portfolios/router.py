import json
from typing import List, Optional, Tuple, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.portfolios.models import Portfolio, RiskCategory, PortfolioHolding, Asset
from app.portfolios.schemas import PortfolioListItem, PortfolioDetail, HoldingSchema, AuditLogSchema
# Import AuditLog from audit module to resolve logs relationship
from app.audit.models import AuditLog

router = APIRouter(prefix="/portfolios", tags=["Portfolio Management"])

def calculate_portfolio_drift_details(portfolio: Portfolio, targets: Dict[str, float]) -> Tuple[float, Dict[str, float]]:
    """Helper to compute drift index and allocation mapping"""
    total_val = portfolio.current_value
    if total_val <= 0:
        return 0.0, {}
        
    holdings_dict = {h.asset_symbol: h.market_value for h in portfolio.holdings}
    current_allocations = {}
    
    # Calculate allocations for non-cash assets
    for symbol in targets:
        mkt_val = holdings_dict.get(symbol, 0.0)
        current_allocations[symbol] = mkt_val / total_val
        
    # Aggregate absolute drift differences
    drift_sum = 0.0
    for symbol, target_weight in targets.items():
        actual_weight = current_allocations.get(symbol, 0.0)
        drift_sum += abs(actual_weight - target_weight)
        
    # Return drift index (0.0 to 1.0)
    drift_pct = drift_sum / 2.0
    return drift_pct, current_allocations

@router.get("", response_model=Dict[str, Any])
def get_portfolios(
    page: int = 1,
    limit: int = 20,
    risk_category: Optional[str] = None,
    needs_rebalance: Optional[bool] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Paginated retrieval of client portfolios with calculated drifts (Authenticated)"""
    query = db.query(Portfolio)
    
    if risk_category:
        query = query.join(RiskCategory).filter(RiskCategory.name == risk_category)
        
    if search:
        query = query.filter(
            (Portfolio.client_name.like(f"%{search}%")) | 
            (Portfolio.account_number.like(f"%{search}%"))
        )
        
    total = query.count()
    portfolios = query.offset((page - 1) * limit).limit(limit).all()
    
    # Resolve risk allocations
    categories = db.query(RiskCategory).all()
    cat_targets = {c.id: json.loads(c.target_allocation) for c in categories}
    cat_names = {c.id: c.name for c in categories}
    
    data = []
    for p in portfolios:
        targets = cat_targets.get(p.risk_category_id, {})
        drift_pct, _ = calculate_portfolio_drift_details(p, targets)
        
        p_needs_rebalance = drift_pct >= 0.05
        if needs_rebalance is not None and p_needs_rebalance != needs_rebalance:
            continue
            
        data.append({
            "id": p.id,
            "account_number": p.account_number,
            "client_name": p.client_name,
            "risk_category": cat_names.get(p.risk_category_id, "Unknown"),
            "total_value": round(p.current_value, 2),
            "cash_balance": round(p.cash_balance, 2),
            "current_drift": round(drift_pct, 4),
            "needs_rebalance": p_needs_rebalance,
            "last_rebalanced": p.last_rebalanced.isoformat() + "Z"
        })
        
    return {
        "total": total,
        "page": page,
        "limit": limit,
        "data": data
    }

@router.get("/{portfolio_id}", response_model=PortfolioDetail)
def get_portfolio_detail(
    portfolio_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Fetch single portfolio holding breakdown and lot details (Authenticated)"""
    portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
    if not portfolio:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")
        
    cat = portfolio.risk_category
    targets = json.loads(cat.target_allocation)
    drift_pct, current_allocations = calculate_portfolio_drift_details(portfolio, targets)
    
    holdings_list = []
    for h in portfolio.holdings:
        symbol = h.asset_symbol
        holdings_list.append({
            "symbol": symbol,
            "name": h.asset.name,
            "asset_class": h.asset.asset_class,
            "shares": round(h.shares, 4),
            "market_value": round(h.market_value, 2),
            "current_weight": round(current_allocations.get(symbol, 0.0), 4),
            "target_weight": round(targets.get(symbol, 0.0), 4),
            "drift": round(current_allocations.get(symbol, 0.0) - targets.get(symbol, 0.0), 4)
        })
        
    # Append cash as pseudo holding
    cash_target = targets.get("BIL", 0.02)
    cash_alloc = portfolio.cash_balance / portfolio.current_value if portfolio.current_value > 0 else 0
    holdings_list.append({
        "symbol": "CASH",
        "name": "Cash Balance (USD)",
        "asset_class": "Cash",
        "shares": round(portfolio.cash_balance, 2),
        "market_value": round(portfolio.cash_balance, 2),
        "current_weight": round(cash_alloc, 4),
        "target_weight": round(cash_target, 4),
        "drift": round(cash_alloc - cash_target, 4)
    })
    
    # Fetch recent audit logs
    logs = db.query(AuditLog).filter(AuditLog.portfolio_id == portfolio_id).order_by(AuditLog.timestamp.desc()).limit(10).all()
    
    return {
        "id": portfolio.id,
        "account_number": portfolio.account_number,
        "client_name": portfolio.client_name,
        "risk_category": cat.name,
        "total_value": round(portfolio.current_value, 2),
        "cash_balance": round(portfolio.cash_balance, 2),
        "current_drift": round(drift_pct, 4),
        "needs_rebalance": drift_pct >= 0.05,
        "holdings": holdings_list,
        "audit_logs": [
            {
                "id": l.id,
                "event_type": l.event_type,
                "details": l.details,
                "timestamp": l.timestamp
            } for l in logs
        ]
    }
