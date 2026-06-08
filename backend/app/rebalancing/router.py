import json
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.portfolios.models import Portfolio, RiskCategory, PortfolioHolding, Asset, TaxLot
from app.rebalancing.models import RebalanceProposal, ProposedTrade
from app.rebalancing.schemas import RebalanceProposalSchema, RebalanceTriggerRequest, ApprovalActionRequest
from app.rebalancing.engine import CrewOrchestrator
from app.audit.models import AuditLog

router = APIRouter(prefix="/rebalance", tags=["Rebalancing Engine"])

def calculate_portfolio_drift_details(portfolio: Portfolio, targets: Dict[str, float]) -> Tuple[float, Dict[str, float]]:
    total_val = portfolio.current_value
    if total_val <= 0:
        return 0.0, {}
        
    holdings_dict = {h.asset_symbol: h.market_value for h in portfolio.holdings}
    current_allocations = {}
    
    for symbol in targets:
        mkt_val = holdings_dict.get(symbol, 0.0)
        current_allocations[symbol] = mkt_val / total_val
        
    drift_sum = 0.0
    for symbol, target_weight in targets.items():
        actual_weight = current_allocations.get(symbol, 0.0)
        drift_sum += abs(actual_weight - target_weight)
        
    drift_pct = drift_sum / 2.0
    return drift_pct, current_allocations

@router.get("/metrics")
def get_dashboard_metrics(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Fetch dashboard metrics (Authenticated)"""
    portfolios_query = db.query(Portfolio).all()
    
    total_portfolios = len(portfolios_query)
    total_aum = sum(p.current_value for p in portfolios_query)
    
    categories = db.query(RiskCategory).all()
    cat_targets = {c.id: json.loads(c.target_allocation) for c in categories}
    
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
    
    tax_savings = db.query(ProposedTrade).join(RebalanceProposal).filter(
        RebalanceProposal.status == "Executed"
    ).sum(ProposedTrade.tax_impact) or 0.0
    
    pending_approvals = db.query(RebalanceProposal).filter(RebalanceProposal.status == "Pending").count()
    
    return {
        "total_portfolios": total_portfolios,
        "total_aum": round(total_aum, 2),
        "average_drift": round(avg_drift, 4),
        "drifted_count": drift_over_limit_count,
        "pending_approvals": pending_approvals,
        "tax_savings_harvested": round(tax_savings, 2)
    }

@router.get("/queue", response_model=List[RebalanceProposalSchema])
def get_rebalance_queue(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Fetch all pending proposals (Authenticated)"""
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
            "created_at": prop.created_at,
            "proposed_trades": trades,
            "shap_explanations": shap_data,
            "status": prop.status,
            "reviewer_comments": prop.reviewer_comments
        })
        
    return response

@router.get("/history", response_model=List[RebalanceProposalSchema])
def get_rebalance_history(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Fetch all processed proposals (Executed or Rejected) (Authenticated)"""
    proposals = db.query(RebalanceProposal).filter(
        RebalanceProposal.status.in_(["Executed", "Rejected"])
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
            "created_at": prop.created_at,
            "proposed_trades": trades,
            "shap_explanations": shap_data,
            "status": prop.status,
            "reviewer_comments": prop.reviewer_comments
        })
        
    return response

@router.post("/trigger", response_model=Dict[str, Any])
def trigger_rebalance_agents(
    request: RebalanceTriggerRequest, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Triggers the CrewAI agent assessment council for portfolios (Authenticated)"""
    orchestrator = CrewOrchestrator(db)
    results = []
    
    p_ids = request.portfolio_ids
    if not p_ids:
        categories = db.query(RiskCategory).all()
        cat_targets = {c.id: json.loads(c.target_allocation) for c in categories}
        
        all_portfolios = db.query(Portfolio).all()
        drifted_portfolios = []
        for p in all_portfolios:
            targets = cat_targets.get(p.risk_category_id, {})
            drift_pct, _ = calculate_portfolio_drift_details(p, targets)
            if drift_pct >= 0.05:
                drifted_portfolios.append((p.id, drift_pct))
                
        drifted_portfolios.sort(key=lambda x: x[1], reverse=True)
        p_ids = [item[0] for item in drifted_portfolios[:5]]
        
    if not p_ids:
        return {"status": "SUCCESS", "message": "No portfolios exceeded drift limits. No agents triggered.", "data": []}
        
    for pid in p_ids:
        res = orchestrator.evaluate_portfolio(pid, trigger_type=request.trigger_type)
        results.append(res)
        
    return {
        "status": "SUCCESS",
        "message": f"CrewAI Agents evaluated {len(p_ids)} portfolios.",
        "data": results
    }

@router.post("/{proposal_id}/action", response_model=Dict[str, Any])
def take_approval_action(
    proposal_id: str, 
    request: ApprovalActionRequest, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Approve or Reject a proposal (Authenticated)"""
    proposal = db.query(RebalanceProposal).filter(RebalanceProposal.id == proposal_id).first()
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
        
    if proposal.status != "Pending":
        raise HTTPException(status_code=400, detail="Proposal is already processed.")
        
    portfolio = proposal.portfolio
    
    if request.action == "REJECTED":
        proposal.status = "Rejected"
        proposal.reviewer_comments = request.comments
        audit = AuditLog(
            portfolio_id=portfolio.id,
            event_type="OrderApproval",
            details=f"Rebalance rejected by user {current_user.email}. Comments: {request.comments or 'None'}",
            timestamp=datetime.utcnow()
        )
        db.add(audit)
        db.commit()
        return {"status": "REJECTED", "proposal_id": proposal_id}
        
    elif request.action == "APPROVED":
        before_state = {
            "cash": portfolio.cash_balance,
            "holdings": {h.asset_symbol: h.shares for h in portfolio.holdings}
        }
        
        # Apply proposed trades
        for trade in proposal.trades:
            symbol = trade.asset_symbol
            action = trade.action
            shares = trade.shares
            price = trade.estimated_price
            trade_value = shares * price
            
            holding = db.query(PortfolioHolding).filter(
                PortfolioHolding.portfolio_id == portfolio.id,
                PortfolioHolding.asset_symbol == symbol
            ).first()
            
            if action == "SELL":
                if holding:
                    holding.shares = max(0.0, holding.shares - shares)
                    holding.market_value = holding.shares * price
                    if holding.shares <= 0.0001:
                        db.delete(holding)
                portfolio.cash_balance += trade_value
                
                # Mark tax lots
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
                    
                new_lot = TaxLot(
                    portfolio_id=portfolio.id,
                    asset_symbol=symbol,
                    shares=shares,
                    purchase_price=price,
                    purchase_date=datetime.utcnow(),
                    is_harvested=False
                )
                db.add(new_lot)
                
        db.flush()
        
        # Calculate new portfolio totals
        new_total_val = portfolio.cash_balance
        for h in portfolio.holdings:
            asset = db.query(Asset).filter(Asset.symbol == h.asset_symbol).first()
            h.market_value = h.shares * asset.current_price
            new_total_val += h.market_value
            
        portfolio.current_value = new_total_val
        portfolio.last_rebalanced = datetime.utcnow()
        proposal.status = "Executed"
        proposal.reviewer_comments = request.comments
        
        after_state = {
            "cash": portfolio.cash_balance,
            "holdings": {h.asset_symbol: h.shares for h in portfolio.holdings}
        }
        
        audit = AuditLog(
            portfolio_id=portfolio.id,
            event_type="OrderExecution",
            details=f"Trades executed at custodian. Approved by: {current_user.email}. Proposal ID: {proposal_id}. Comments: {request.comments or 'None'}",
            state_before=json.dumps(before_state),
            state_after=json.dumps(after_state),
            timestamp=datetime.utcnow()
        )
        db.add(audit)
        db.commit()
        return {"status": "SUCCESS", "proposal_id": proposal_id}
        
    raise HTTPException(status_code=400, detail="Invalid action.")
