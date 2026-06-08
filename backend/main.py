import json
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
import database
from database import get_db, Portfolio, RiskCategory, PortfolioHolding, Asset, RebalanceProposal, ProposedTrade, AuditLog, TaxLot
from seeding import seed_database
from agents import CrewOrchestrator

app = FastAPI(title="WealthPilot AI Core Backend", version="1.0.0")

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup hook to initialize database and seed
@app.on_event("startup")
def startup_event():
    database.init_db()
    # Seed 5,000 portfolios (takes 2-3 seconds)
    seed_database(5000)

# Pydantic Schemas
class RebalanceTriggerRequest(BaseModel):
    trigger_type: str = "Threshold"
    portfolio_ids: Optional[List[str]] = None

class ApprovalActionRequest(BaseModel):
    action: str # APPROVED or REJECTED
    comments: Optional[str] = None

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

# REST API Endpoints

@app.get("/api/v1/metrics")
def get_dashboard_metrics(db: Session = Depends(get_db)):
    """Fetch aggregated metrics for the top dashboard cards"""
    portfolios_query = db.query(Portfolio).all()
    
    total_portfolios = len(portfolios_query)
    total_aum = sum(p.current_value for p in portfolios_query)
    
    # Pre-cache risk categories to avoid N+1 queries
    categories = db.query(RiskCategory).all()
    cat_targets = {c.id: json.loads(c.target_allocation) for c in categories}
    
    # Calculate drift metrics in python
    drift_sum = 0.0
    drift_count = 0
    drift_over_limit_count = 0
    
    for p in portfolios_query:
        targets = cat_targets.get(p.risk_category_id, {})
        drift_pct, _ = calculate_portfolio_drift_details(p, targets)
        drift_sum += drift_pct
        drift_count += 1
        if drift_pct >= 0.05:
            drift_over_limit_count += 1
            
    avg_drift = drift_sum / drift_count if drift_count > 0 else 0
    
    # Total tax savings harvested (sum of executed proposals tax impacts)
    tax_savings = db.query(ProposedTrade).join(RebalanceProposal).filter(
        RebalanceProposal.status == "Executed"
    ).sum(ProposedTrade.tax_impact) or 0.0
    
    # Pending approvals queue count
    pending_approvals = db.query(RebalanceProposal).filter(RebalanceProposal.status == "Pending").count()
    
    return {
        "total_portfolios": total_portfolios,
        "total_aum": round(total_aum, 2),
        "average_drift": round(avg_drift, 4),
        "drifted_count": drift_over_limit_count,
        "pending_approvals": pending_approvals,
        "tax_savings_harvested": round(tax_savings, 2)
    }

@app.get("/api/v1/portfolios")
def get_portfolios(
    page: int = 1,
    limit: int = 20,
    risk_category: Optional[str] = None,
    needs_rebalance: Optional[bool] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Paginated retrieval of client portfolios with calculated drifts"""
    query = db.query(Portfolio)
    
    if risk_category:
        query = query.join(RiskCategory).filter(RiskCategory.name == risk_category)
        
    if search:
        query = query.filter(
            (Portfolio.client_name.like(f"%{search}%")) | 
            (Portfolio.account_number.like(f"%{search}%"))
        )
        
    # Get total before slicing
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
        
        # Filter on drift
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

@app.get("/api/v1/portfolios/{portfolio_id}")
def get_portfolio_detail(portfolio_id: str, db: Session = Depends(get_db)):
    """Fetch single portfolio holding breakdown and lot details"""
    portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
        
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
    cash_target = targets.get("BIL", 0.02) # assume BIL target as cash baseline if no specific cash key
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
                "timestamp": l.timestamp.isoformat() + "Z"
            } for l in logs
        ]
    }

@app.post("/api/v1/rebalance/trigger")
def trigger_rebalance_agents(request: RebalanceTriggerRequest, db: Session = Depends(get_db)):
    """Triggers the CrewAI agent assessment council for portfolios"""
    orchestrator = CrewOrchestrator(db)
    results = []
    
    # If portfolio IDs specified, run on them.
    # Otherwise, scan and run on top 5 highly drifted portfolios for visual demo efficiency
    p_ids = request.portfolio_ids
    if not p_ids:
        # Fetch risk category targets
        categories = db.query(RiskCategory).all()
        cat_targets = {c.id: json.loads(c.target_allocation) for c in categories}
        
        all_portfolios = db.query(Portfolio).all()
        drifted_portfolios = []
        for p in all_portfolios:
            targets = cat_targets.get(p.risk_category_id, {})
            drift_pct, _ = calculate_portfolio_drift_details(p, targets)
            if drift_pct >= 0.05:
                drifted_portfolios.append((p.id, drift_pct))
                
        # Sort by drift descending and pick top 5
        drifted_portfolios.sort(key=lambda x: x[1], reverse=True)
        p_ids = [item[0] for item in drifted_portfolios[:5]]
        
    if not p_ids:
        return {"status": "SUCCESS", "message": "No portfolios exceeded drift limits. No agents triggered.", "data": []}
        
    for pid in p_ids:
        res = orchestrator.evaluate_portfolio(pid, trigger_type=request.trigger_type)
        results.append(res)
        
    return {
        "status": "SUCCESS",
        "message": f"CrewAI Agents evaluated {len(p_ids)} portfolios. Proposals submitted to dashboard review queue.",
        "data": results
    }

@app.get("/api/v1/rebalance/queue")
def get_rebalance_queue(db: Session = Depends(get_db)):
    """Fetches the human-in-the-loop pending approval queue"""
    proposals = db.query(RebalanceProposal).filter(
        RebalanceProposal.status == "Pending"
    ).order_by(RebalanceProposal.created_at.desc()).all()
    
    response = []
    for prop in proposals:
        p = prop.portfolio
        shap_data = json.loads(prop.shap_explanations) if prop.shap_explanations else {}
        
        trades = []
        for t in prop.trades:
            trades.append({
                "symbol": t.asset_symbol,
                "action": t.action,
                "shares": round(t.shares, 4),
                "estimated_price": round(t.estimated_price, 2),
                "tax_impact": round(t.tax_impact, 2)
            })
            
        response.append({
            "proposal_id": prop.id,
            "portfolio_id": p.id,
            "account_number": p.account_number,
            "client_name": p.client_name,
            "trigger_type": prop.trigger_type,
            "reason": prop.reason,
            "created_at": prop.created_at.isoformat() + "Z",
            "proposed_trades": trades,
            "shap_explanations": shap_data
        })
        
    return response

@app.post("/api/v1/rebalance/{proposal_id}/action")
def take_approval_action(proposal_id: str, request: ApprovalActionRequest, db: Session = Depends(get_db)):
    """Approves or Rejects a proposal. If approved, order execution is simulated in DB"""
    proposal = db.query(RebalanceProposal).filter(RebalanceProposal.id == proposal_id).first()
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
        
    if proposal.status != "Pending":
        raise HTTPException(status_code=400, detail="Proposal is already processed.")
        
    portfolio = proposal.portfolio
    
    if request.action == "REJECTED":
        proposal.status = "Rejected"
        
        audit = AuditLog(
            portfolio_id=portfolio.id,
            event_type="OrderApproval",
            details=f"Rebalance order rejected by manager. Comments: {request.comments or 'None'}",
            timestamp=datetime.utcnow()
        )
        db.add(audit)
        db.commit()
        return {"status": "REJECTED", "proposal_id": proposal_id}
        
    elif request.action == "APPROVED":
        # Simulate execution
        # Capture current allocations before trades
        before_state = {
            "cash": portfolio.cash_balance,
            "holdings": {h.asset_symbol: h.shares for h in portfolio.holdings}
        }
        
        # Apply trades
        for trade in proposal.trades:
            symbol = trade.asset_symbol
            action = trade.action
            shares = trade.shares
            price = trade.estimated_price
            trade_value = shares * price
            
            # Find the holding object in DB
            holding = db.query(PortfolioHolding).filter(
                PortfolioHolding.portfolio_id == portfolio.id,
                PortfolioHolding.asset_symbol == symbol
            ).first()
            
            if action == "SELL":
                # Sell from holding
                if holding:
                    holding.shares = max(0.0, holding.shares - shares)
                    holding.market_value = holding.shares * price
                    if holding.shares <= 0.0001:
                        db.delete(holding)
                # Add to cash
                portfolio.cash_balance += trade_value
                
                # Mark tax lots as harvested if they match the sale
                # For simplicity, mark the oldest lots up to the shares sold
                lots = db.query(TaxLot).filter(
                    TaxLot.portfolio_id == portfolio.id,
                    TaxLot.asset_symbol == symbol,
                    TaxLot.is_harvested == False
                ).order_by(TaxLot.purchase_price.desc()).all()
                
                shares_to_mark = shares
                for lot in lots:
                    if shares_to_mark <= 0:
                        break
                    if lot.shares <= shares_to_mark:
                        lot.is_harvested = True
                        shares_to_mark -= lot.shares
                    else:
                        # Split lot
                        lot.shares -= shares_to_mark
                        new_lot = TaxLot(
                            portfolio_id=portfolio.id,
                            asset_symbol=symbol,
                            shares=shares_to_mark,
                            purchase_price=lot.purchase_price,
                            purchase_date=lot.purchase_date,
                            is_harvested=True
                        )
                        db.add(new_lot)
                        shares_to_mark = 0
                        
            elif action == "BUY":
                # Deduct cash
                portfolio.cash_balance = max(0.0, portfolio.cash_balance - trade_value)
                
                if holding:
                    holding.shares += shares
                    holding.market_value = holding.shares * price
                else:
                    new_holding = PortfolioHolding(
                        portfolio_id=portfolio.id,
                        asset_symbol=symbol,
                        shares=shares,
                        market_value=trade_value
                    )
                    db.add(new_holding)
                    
                # Create a new tax lot for this purchase
                new_lot = TaxLot(
                    portfolio_id=portfolio.id,
                    asset_symbol=symbol,
                    shares=shares,
                    purchase_price=price,
                    purchase_date=datetime.utcnow(),
                    is_harvested=False
                )
                db.add(new_lot)
                
        # Re-calculate total portfolio value
        db.flush() # Sync delete objects
        
        # Calculate new value
        new_total_val = portfolio.cash_balance
        for h in portfolio.holdings:
            # Re-read price from Asset table
            asset = db.query(Asset).filter(Asset.symbol == h.asset_symbol).first()
            h.market_value = h.shares * asset.current_price
            new_total_val += h.market_value
            
        portfolio.current_value = new_total_val
        portfolio.last_rebalanced = datetime.utcnow()
        proposal.status = "Executed"
        
        # Create execution audit log
        after_state = {
            "cash": portfolio.cash_balance,
            "holdings": {h.asset_symbol: h.shares for h in portfolio.holdings}
        }
        
        audit = AuditLog(
            portfolio_id=portfolio.id,
            event_type="OrderExecution",
            details=f"Rebalance orders successfully executed at custodian. Proposals ID: {proposal_id}.",
            state_before=json.dumps(before_state),
            state_after=json.dumps(after_state),
            timestamp=datetime.utcnow()
        )
        db.add(audit)
        db.commit()
        return {"status": "SUCCESS", "proposal_id": proposal_id}
        
    raise HTTPException(status_code=400, detail="Invalid action parameter.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
