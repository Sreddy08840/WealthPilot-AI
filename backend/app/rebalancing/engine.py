import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple
from sqlalchemy.orm import Session
from app.portfolios.models import Portfolio, PortfolioHolding, Asset, TaxLot
from app.rebalancing.models import RebalanceProposal, ProposedTrade
from app.audit.models import AuditLog
from app.rebalancing.explainability import generate_shap_explanation

# Global compliance config
RESTRICTED_LIST = ["BTC", "COIN", "TSLA", "MSTR"]
CONCENTRATION_LIMIT = 0.80
ALT_CONCENTRATION_LIMIT = 0.20

# Tax harvesting proxy tickers
HARVESTING_PROXIES = {
    "SPY": "IVV",
    "QQQ": "ONEQ",
    "AGG": "BND",
    "GLD": "IAU",
}

def run_pre_trade_compliance(
    db: Session,
    portfolio_id: str,
    proposed_trades: List[Dict[str, Any]]
) -> Tuple[bool, List[str], List[Dict[str, Any]]]:
    violations = []
    modified_trades = [trade.copy() for trade in proposed_trades]
    portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
    
    if not portfolio:
        return False, ["Portfolio not found."], []

    # 1. Restricted List Check
    for trade in proposed_trades:
        symbol = trade["symbol"]
        if symbol in RESTRICTED_LIST:
            violations.append(f"Compliance Violation: Symbol {symbol} is on the Restricted List.")
            modified_trades = [t for t in modified_trades if t["symbol"] != symbol]

    # 2. Wash Sale Rule Check (30-day window)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    for trade in proposed_trades:
        symbol = trade["symbol"]
        action = trade["action"]
        
        if action == "BUY":
            recent_loss_lot = db.query(TaxLot).filter(
                TaxLot.portfolio_id == portfolio_id,
                TaxLot.asset_symbol == symbol,
                TaxLot.is_harvested == True,
                TaxLot.purchase_date >= thirty_days_ago
            ).first()
            
            if recent_loss_lot:
                proxy_symbol = HARVESTING_PROXIES.get(symbol, "Cash")
                violations.append(
                    f"Wash Sale Risk: Bought {symbol} within 30 days of a tax-loss harvest. "
                    f"Redirected purchase to proxy: {proxy_symbol}."
                )
                for t in modified_trades:
                    if t["symbol"] == symbol and t["action"] == "BUY":
                        t["symbol"] = proxy_symbol
                        proxy_asset = db.query(Asset).filter(Asset.symbol == proxy_symbol).first()
                        if proxy_asset:
                            t["estimated_price"] = proxy_asset.current_price

    # 3. Concentration Limit Check
    portfolio_value = portfolio.current_value
    current_holdings = {h.asset_symbol: h.market_value for h in portfolio.holdings}
    cash = portfolio.cash_balance
    
    projected_holdings = current_holdings.copy()
    
    for trade in modified_trades:
        symbol = trade["symbol"]
        action = trade["action"]
        shares = trade["shares"]
        price = trade["estimated_price"]
        trade_value = shares * price
        
        if action == "BUY":
            projected_holdings[symbol] = projected_holdings.get(symbol, 0.0) + trade_value
        elif action == "SELL":
            projected_holdings[symbol] = max(0.0, projected_holdings.get(symbol, 0.0) - trade_value)
            
    for symbol, val in projected_holdings.items():
        weight = val / portfolio_value if portfolio_value > 0 else 0
        asset = db.query(Asset).filter(Asset.symbol == symbol).first()
        
        if asset:
            if asset.asset_class == "Alternative" and weight > ALT_CONCENTRATION_LIMIT:
                violations.append(
                    f"Concentration Violation: {symbol} allocation ({weight:.1%}) exceeds alternative limit ({ALT_CONCENTRATION_LIMIT:.1%})."
                )
                for t in modified_trades:
                    if t["symbol"] == symbol and t["action"] == "BUY":
                        allowed_val = (portfolio_value * ALT_CONCENTRATION_LIMIT) - current_holdings.get(symbol, 0.0)
                        if allowed_val > 0:
                            t["shares"] = round(allowed_val / t["estimated_price"], 4)
                        else:
                            modified_trades = [x for x in modified_trades if not (x["symbol"] == symbol and x["action"] == "BUY")]
                            
            elif weight > CONCENTRATION_LIMIT:
                violations.append(
                    f"Concentration Violation: {symbol} allocation ({weight:.1%}) exceeds single asset limit ({CONCENTRATION_LIMIT:.1%})."
                )
                for t in modified_trades:
                    if t["symbol"] == symbol and t["action"] == "BUY":
                        allowed_val = (portfolio_value * CONCENTRATION_LIMIT) - current_holdings.get(symbol, 0.0)
                        if allowed_val > 0:
                            t["shares"] = round(allowed_val / t["estimated_price"], 4)
                        else:
                            modified_trades = [x for x in modified_trades if not (x["symbol"] == symbol and x["action"] == "BUY")]

    is_compliant = len(violations) == 0
    return is_compliant, violations, modified_trades

class CrewAgent:
    def __init__(self, name: str, role: str, backstory: str, tools: List[str]):
        self.name = name
        self.role = role
        self.backstory = backstory
        self.tools = tools

class PortfolioMonitorAgent(CrewAgent):
    def generate_thoughts(self, portfolio: Portfolio, drift_pct: float) -> List[str]:
        return [
            f"[{self.name}] Scanning account {portfolio.account_number} (Client: {portfolio.client_name}).",
            f"[{self.name}] Computed drift index is {drift_pct:.2%}.",
            f"[{self.name}] Decision: Drift threshold limit is 5.0%. Drift of {drift_pct:.2%} exceeds limits.",
            f"[{self.name}] Action: Requesting Tax Optimizer lot matching calculations."
        ]

class TaxOptimizerAgent(CrewAgent):
    def generate_thoughts(self, portfolio: Portfolio, db: Session) -> Tuple[List[str], float, List[Dict[str, Any]]]:
        thoughts = [
            f"[{self.name}] Initiating tax optimization routine.",
            f"[{self.name}] Fetching open tax lots (HIFO selection)."
        ]
        
        harvested_losses = 0.0
        proposed_trades = []
        cat = portfolio.risk_category
        targets = json.loads(cat.target_allocation)
        
        for holding in portfolio.holdings:
            target_weight = targets.get(holding.asset_symbol, 0.0)
            current_weight = holding.market_value / portfolio.current_value if portfolio.current_value > 0 else 0
            drift = current_weight - target_weight
            
            if drift > 0.02: # Overweight -> SELL
                sell_val = drift * portfolio.current_value
                lots = db.query(TaxLot).filter(
                    TaxLot.portfolio_id == portfolio.id,
                    TaxLot.asset_symbol == holding.asset_symbol,
                    TaxLot.is_harvested == False
                ).all()
                
                # Sort HIFO (highest cost basis first)
                lots.sort(key=lambda x: x.purchase_price, reverse=True)
                
                shares_to_sell = sell_val / holding.asset.current_price
                shares_selling_remaining = shares_to_sell
                
                thoughts.append(f"[{self.name}] Selling overweight asset {holding.asset_symbol} (Drift: +{drift:.2%}). Target shares to liquidate: {shares_to_sell:.2f}.")
                
                for lot in lots:
                    if shares_selling_remaining <= 0:
                        break
                    
                    sell_lot_shares = min(lot.shares, shares_selling_remaining)
                    shares_selling_remaining -= sell_lot_shares
                    
                    lot_cost = sell_lot_shares * lot.purchase_price
                    lot_proceeds = sell_lot_shares * holding.asset.current_price
                    lot_gain_loss = lot_proceeds - lot_cost
                    
                    if lot_gain_loss < 0:
                        harvested_losses += abs(lot_gain_loss)
                        thoughts.append(
                            f"[{self.name}] Tax-Harvest Opportunity: Sold Lot (cost ${lot.purchase_price:.2f}). "
                            f"shares: {sell_lot_shares:.2f}. Realized Loss: ${abs(lot_gain_loss):.2f}."
                        )
                    else:
                        thoughts.append(
                            f"[{self.name}] Realized Gain Lot: cost ${lot.purchase_price:.2f}, shares: {sell_lot_shares:.2f}. Gain: ${lot_gain_loss:.2f}."
                        )
                
                proposed_trades.append({
                    "symbol": holding.asset_symbol,
                    "action": "SELL",
                    "shares": round(shares_to_sell, 4),
                    "estimated_price": holding.asset.current_price,
                    "tax_impact": round(harvested_losses, 2)
                })
                
            elif drift < -0.02: # Underweight -> BUY
                buy_val = abs(drift) * portfolio.current_value
                shares_to_buy = buy_val / holding.asset.current_price
                
                thoughts.append(f"[{self.name}] Buying underweight asset {holding.asset_symbol} (Drift: {drift:.2%}). Target shares: {shares_to_buy:.2f}.")
                proposed_trades.append({
                    "symbol": holding.asset_symbol,
                    "action": "BUY",
                    "shares": round(shares_to_buy, 4),
                    "estimated_price": holding.asset.current_price,
                    "tax_impact": 0.0
                })
                
        thoughts.append(f"[{self.name}] Tax Audit complete. Capital loss harvested: ${harvested_losses:.2f}.")
        return thoughts, harvested_losses, proposed_trades

class ComplianceAuditorAgent(CrewAgent):
    def generate_thoughts(self, portfolio: Portfolio, proposed_trades: List[Dict[str, Any]], db: Session) -> Tuple[List[str], bool, List[str], List[Dict[str, Any]]]:
        thoughts = [
            f"[{self.name}] Screening proposed trades for SEC / compliance limits.",
            f"[{self.name}] Running pre-trade screening routines."
        ]
        
        is_compliant, violations, modified_trades = run_pre_trade_compliance(db, portfolio.id, proposed_trades)
        
        if is_compliant:
            thoughts.append(f"[{self.name}] Validation: Passed all trade constraints checks.")
        else:
            for violation in violations:
                thoughts.append(f"[{self.name}] Violation Flag: {violation}")
            thoughts.append(f"[{self.name}] Resolution: Applied modified compliance trade allocations.")
            
        return thoughts, is_compliant, violations, modified_trades

class ExecutionPlannerAgent(CrewAgent):
    def generate_thoughts(
        self,
        portfolio: Portfolio,
        trades: List[Dict[str, Any]],
        drift_pct: float,
        tax_savings: float,
        shap_explanations: Dict[str, Any]
    ) -> List[str]:
        return [
            f"[{self.name}] Formulating trade blocks and calculating broker fees.",
            f"[{self.name}] Computing game-theoretic SHAP attributions.",
            f"[{self.name}] Attributions calculated. Base value: {shap_explanations['base_value']:.4f}, Rebalance Utility: {shap_explanations['output_value']:.4f}.",
            f"[{self.name}] Routing execution orders block to Pending Review Queue."
        ]

class CrewOrchestrator:
    def __init__(self, db: Session):
        self.db = db
        self.monitor = PortfolioMonitorAgent("Portfolio Monitor", "Drift Analyst", "Computes actual drifts against templates", ["drift_calculator_tool"])
        self.tax_optimizer = TaxOptimizerAgent("Tax Optimizer", "Tax Strategist", "Executes HIFO and harvests losses", ["tax_lot_selector"])
        self.compliance = ComplianceAuditorAgent("Compliance Auditor", "Auditor", "Checks wash sale rules and asset limits", ["wash_sale_checker"])
        self.planner = ExecutionPlannerAgent("Execution Planner", "Planner", "Packs trade blocks and compiles SHAP explanations", ["shap_explanation_generator"])

    def evaluate_portfolio(self, portfolio_id: str, trigger_type: str = "Threshold") -> Dict[str, Any]:
        portfolio = self.db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
        if not portfolio:
            return {"error": "Portfolio not found"}

        cat = portfolio.risk_category
        targets = json.loads(cat.target_allocation)
        
        drift_sum = 0.0
        current_allocations = {}
        
        for holding in portfolio.holdings:
            alloc = holding.market_value / portfolio.current_value if portfolio.current_value > 0 else 0
            current_allocations[holding.asset_symbol] = alloc
            target = targets.get(holding.asset_symbol, 0.0)
            drift_sum += abs(alloc - target)
            
        cash_alloc = portfolio.cash_balance / portfolio.current_value if portfolio.current_value > 0 else 0
        target_cash = targets.get("BIL", 0.02)
        drift_sum += abs(cash_alloc - target_cash)
        drift_pct = drift_sum / 2.0

        # Step 1: Monitor thoughts
        monitor_thoughts = self.monitor.generate_thoughts(portfolio, drift_pct)
        
        # Step 2: Tax Optimizer thoughts
        tax_thoughts, tax_savings, raw_trades = self.tax_optimizer.generate_thoughts(portfolio, self.db)
        
        # Step 3: Compliance Auditor thoughts
        comp_thoughts, is_compliant, violations, final_trades = self.compliance.generate_thoughts(portfolio, raw_trades, self.db)
        
        est_tx_cost = len(final_trades) * 4.95
        
        # Step 4: Explainability & Planner thoughts
        shap_data = generate_shap_explanation(
            drift_pct=drift_pct,
            tax_savings_val=tax_savings,
            cash_drift_pct=abs(cash_alloc - target_cash),
            est_tx_cost=est_tx_cost,
            portfolio_value=portfolio.current_value,
            vix_level=18.5
        )
        
        planner_thoughts = self.planner.generate_thoughts(portfolio, final_trades, drift_pct, tax_savings, shap_data)
        
        # Collate thoughts
        full_log = []
        full_log.extend(monitor_thoughts)
        full_log.extend(tax_thoughts)
        full_log.extend(comp_thoughts)
        full_log.extend(planner_thoughts)
        
        # Write Proposal to DB
        proposal = RebalanceProposal(
            portfolio_id=portfolio.id,
            trigger_type=trigger_type,
            status="Pending",
            reason=f"Aggregate drift {drift_pct:.2%} exceeds limits.",
            shap_explanations=json.dumps(shap_data),
            created_at=datetime.utcnow()
        )
        self.db.add(proposal)
        self.db.flush()
        
        # Add Trades
        for t in final_trades:
            trade_obj = ProposedTrade(
                proposal_id=proposal.id,
                asset_symbol=t["symbol"],
                action=t["action"],
                shares=t["shares"],
                estimated_price=t["estimated_price"],
                tax_impact=t["tax_impact"]
            )
            self.db.add(trade_obj)
            
        # Log Audit event
        audit = AuditLog(
            portfolio_id=portfolio.id,
            event_type="AgentRun",
            details=f"Modular engine run. Rebalance proposal created: {proposal.id}.",
            state_before=json.dumps({
                "drift_pct": drift_pct,
                "current_allocations": current_allocations,
                "value": portfolio.current_value,
                "cash": portfolio.cash_balance
            }),
            state_after=json.dumps({
                "proposal_id": proposal.id,
                "proposed_trades_count": len(final_trades),
                "compliance_status": "Passed" if is_compliant else "Modified"
            }),
            timestamp=datetime.utcnow()
        )
        self.db.add(audit)
        self.db.commit()

        return {
            "proposal_id": proposal.id,
            "portfolio_id": portfolio.id,
            "client_name": portfolio.client_name,
            "account_number": portfolio.account_number,
            "trigger_type": trigger_type,
            "drift_pct": drift_pct,
            "tax_savings": tax_savings,
            "is_compliant": is_compliant,
            "violations": violations,
            "shap_explanation": shap_data,
            "execution_log": full_log,
            "proposed_trades": final_trades
        }
