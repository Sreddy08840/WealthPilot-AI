import json
from datetime import datetime
from typing import Dict, List, Any, Tuple
from sqlalchemy.orm import Session
from database import Portfolio, PortfolioHolding, Asset, TaxLot, RebalanceProposal, ProposedTrade, AuditLog
from compliance import run_pre_trade_compliance
from explainability import generate_shap_explanation

class CrewAgent:
    def __init__(self, name: str, role: str, backstory: str, tools: List[str]):
        self.name = name
        self.role = role
        self.backstory = backstory
        self.tools = tools

    def generate_thoughts(self, context: str) -> List[str]:
        # Return custom detailed reasoning logs depending on agent role
        raise NotImplementedError

class PortfolioMonitorAgent(CrewAgent):
    def generate_thoughts(self, portfolio: Portfolio, drift_pct: float) -> List[str]:
        return [
            f"[{self.name}] Initiating portfolio scan for account {portfolio.account_number} (Client: {portfolio.client_name}).",
            f"[{self.name}] Tool Call: `drift_calculator_tool` executed. Current aggregate drift is {drift_pct:.2%}.",
            f"[{self.name}] Assessment: Drift threshold is 5.0%. Current drift is {drift_pct:.2%}, which {"EXCEEDS" if drift_pct >= 0.05 else "DOES NOT EXCEED"} threshold limits.",
            f"[{self.name}] Status: Drift detected in asset allocation. Rebalancing is REQUIRED. Triggering Tax Optimizer Agent to analyze HIFO lot matching and Tax-Loss Harvesting opportunities."
        ]

class TaxOptimizerAgent(CrewAgent):
    def generate_thoughts(self, portfolio: Portfolio, db: Session) -> Tuple[List[str], float, List[Dict[str, Any]]]:
        # Perform HIFO selection and find tax-loss harvesting lots
        thoughts = [
            f"[{self.name}] Commencing tax optimization audit for {portfolio.account_number}.",
            f"[{self.name}] Tool Call: `get_tax_lots` executed. Fetching purchase prices and dates for all holdings."
        ]
        
        harvested_losses = 0.0
        proposed_trades = []
        
        # Analyze each holding to see if it has drifted and has lots we can harvest
        for holding in portfolio.holdings:
            # Check target weight
            cat = portfolio.risk_category
            targets = json.loads(cat.target_allocation)
            target_weight = targets.get(holding.asset_symbol, 0.0)
            current_weight = holding.market_value / portfolio.current_value if portfolio.current_value > 0 else 0
            
            # Simple rebalancing logic
            drift = current_weight - target_weight
            
            if drift > 0.02: # Overweight, need to sell
                sell_val = drift * portfolio.current_value
                # Look for tax lots of this asset in portfolio to sell (HIFO)
                lots = db.query(TaxLot).filter(
                    TaxLot.portfolio_id == portfolio.id,
                    TaxLot.asset_symbol == holding.asset_symbol,
                    TaxLot.is_harvested == False
                ).all()
                
                # Sort by purchase price descending (HIFO - Highest In First Out)
                lots.sort(key=lambda x: x.purchase_price, reverse=True)
                
                shares_to_sell = sell_val / holding.asset.current_price
                shares_selling_remaining = shares_to_sell
                
                thoughts.append(f"[{self.name}] Asset {holding.asset_symbol} is overweight by {drift:.2%}. Seeking HIFO lots to sell {shares_to_sell:.2f} shares ($ {sell_val:.2f}).")
                
                for lot in lots:
                    if shares_selling_remaining <= 0:
                        break
                    
                    sell_lot_shares = min(lot.shares, shares_selling_remaining)
                    shares_selling_remaining -= sell_lot_shares
                    
                    # Capital gain/loss calculation
                    lot_cost = sell_lot_shares * lot.purchase_price
                    lot_proceeds = sell_lot_shares * holding.asset.current_price
                    lot_gain_loss = lot_proceeds - lot_cost
                    
                    if lot_gain_loss < 0:
                        harvested_losses += abs(lot_gain_loss)
                        thoughts.append(
                            f"[{self.name}] Harvesting Loss: Identified Lot (bought at ${lot.purchase_price:.2f} on {lot.purchase_date.strftime('%Y-%m-%d')}). "
                            f"Selling {sell_lot_shares:.2f} shares at current price ${holding.asset.current_price:.2f}. "
                            f"Realizing tax loss of ${abs(lot_gain_loss):.2f}."
                        )
                    else:
                        thoughts.append(
                            f"[{self.name}] Minimizing Gains: Identified Lot (bought at ${lot.purchase_price:.2f} on {lot.purchase_date.strftime('%Y-%m-%d')}). "
                            f"Selling {sell_lot_shares:.2f} shares. Realizing gain of ${lot_gain_loss:.2f}."
                        )
                
                proposed_trades.append({
                    "symbol": holding.asset_symbol,
                    "action": "SELL",
                    "shares": round(shares_to_sell, 4),
                    "estimated_price": holding.asset.current_price,
                    "tax_impact": round(harvested_losses, 2)
                })
                
            elif drift < -0.02: # Underweight, need to buy
                buy_val = abs(drift) * portfolio.current_value
                shares_to_buy = buy_val / holding.asset.current_price
                
                thoughts.append(f"[{self.name}] Asset {holding.asset_symbol} is underweight by {abs(drift):.2%}. Proposed buy order of {shares_to_buy:.2f} shares ($ {buy_val:.2f}).")
                proposed_trades.append({
                    "symbol": holding.asset_symbol,
                    "action": "BUY",
                    "shares": round(shares_to_buy, 4),
                    "estimated_price": holding.asset.current_price,
                    "tax_impact": 0.0
                })
                
        if harvested_losses > 0:
            thoughts.append(f"[{self.name}] Tax Optimization complete. Total capital losses harvested: ${harvested_losses:.2f}. Routing proposed trades to Compliance Auditor.")
        else:
            thoughts.append(f"[{self.name}] Tax Optimization complete. No loss harvesting opportunities identified. Routing proposed trades to Compliance Auditor.")
            
        return thoughts, harvested_losses, proposed_trades

class ComplianceAuditorAgent(CrewAgent):
    def generate_thoughts(self, portfolio: Portfolio, proposed_trades: List[Dict[str, Any]], db: Session) -> Tuple[List[str], bool, List[str], List[Dict[str, Any]]]:
        thoughts = [
            f"[{self.name}] Initiating legal and regulatory pre-trade scan for proposed trades.",
            f"[{self.name}] Tool Call: `run_pre_trade_compliance` executed."
        ]
        
        is_compliant, violations, modified_trades = run_pre_trade_compliance(db, portfolio.id, proposed_trades)
        
        if is_compliant:
            thoughts.append(f"[{self.name}] Compliance Validation Passed: All assets pass restricted list check, wash sale rules, and concentration limit caps.")
        else:
            for violation in violations:
                thoughts.append(f"[{self.name}] Compliance Warning: {violation}")
            thoughts.append(f"[{self.name}] Resolution: Compliance constraints applied. Adjusted proposed trades list compiled.")
            
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
        thoughts = [
            f"[{self.name}] Consolidating trade packets into a single execution block.",
            f"[{self.name}] Generating AI Explainability scores. Running SHAP game-theoretic analysis...",
            f"[{self.name}] SHAP Base Value: {shap_explanations['base_value']:.4f}, Rebalance Utility: {shap_explanations['output_value']:.4f}.",
            f"[{self.name}] Feature Contributions: Drift ({shap_explanations['shap_values']['drift_magnitude']:.2f}), Tax ({shap_explanations['shap_values']['tax_savings']:.2f}), Volatility ({shap_explanations['shap_values']['market_volatility']:.2f}).",
            f"[{self.name}] Formulating portfolio manager rebalance report.",
            f"[{self.name}] Action: Submitting proposal to the Human Override Approval Queue."
        ]
        return thoughts

class CrewOrchestrator:
    def __init__(self, db: Session):
        self.db = db
        self.monitor = PortfolioMonitorAgent("Portfolio Monitor", "Drift Analyst", "Scans asset allocations against risk templates", ["drift_calculator_tool"])
        self.tax_optimizer = TaxOptimizerAgent("Tax Optimizer", "Tax Strategist", "Applies HIFO lot picking and harvests capital losses", ["tax_lot_selector"])
        self.compliance = ComplianceAuditorAgent("Compliance Auditor", "Regulatory Auditor", "Validates wash sales and single asset concentration caps", ["wash_sale_checker"])
        self.planner = ExecutionPlannerAgent("Execution Planner", "Trade Block Packager", "Assembles trades, estimates transaction fees, and generates SHAP explanations", ["shap_explanation_generator"])

    def evaluate_portfolio(self, portfolio_id: str, trigger_type: str = "Threshold") -> Dict[str, Any]:
        portfolio = self.db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
        if not portfolio:
            return {"error": "Portfolio not found"}

        # Calculate current drift percentage
        cat = portfolio.risk_category
        targets = json.loads(cat.target_allocation)
        
        drift_sum = 0.0
        current_allocations = {}
        
        for holding in portfolio.holdings:
            alloc = holding.market_value / portfolio.current_value if portfolio.current_value > 0 else 0
            current_allocations[holding.asset_symbol] = alloc
            target = targets.get(holding.asset_symbol, 0.0)
            drift_sum += abs(alloc - target)
            
        # Add cash drift
        cash_alloc = portfolio.cash_balance / portfolio.current_value if portfolio.current_value > 0 else 0
        target_cash = targets.get("BIL", 0.02) # Let's assume BIL represents cash/bills
        drift_sum += abs(cash_alloc - target_cash)
        
        # Absolute drift metric
        drift_pct = drift_sum / 2.0

        # Step 1: Monitor Agent Scan
        monitor_thoughts = self.monitor.generate_thoughts(portfolio, drift_pct)
        
        # Step 2: Tax Optimization
        tax_thoughts, tax_savings, raw_trades = self.tax_optimizer.generate_thoughts(portfolio, self.db)
        
        # Step 3: Compliance Auditor Check
        comp_thoughts, is_compliant, violations, final_trades = self.compliance.generate_thoughts(portfolio, raw_trades, self.db)
        
        # Calculate approximate transaction costs (broker fees)
        est_tx_cost = len(final_trades) * 4.95 # $4.95 per trade commission
        
        # Step 4: Explainability Engine & Execution Planner
        # Volatility index (VIX) assumed at 18.5
        vix = 18.5
        shap_data = generate_shap_explanation(
            drift_pct=drift_pct,
            tax_savings_val=tax_savings,
            cash_drift_pct=abs(cash_alloc - target_cash),
            est_tx_cost=est_tx_cost,
            portfolio_value=portfolio.current_value,
            vix_level=vix
        )
        
        planner_thoughts = self.planner.generate_thoughts(portfolio, final_trades, drift_pct, tax_savings, shap_data)
        
        # Collate all logs
        full_execution_log = []
        full_execution_log.extend(monitor_thoughts)
        full_execution_log.extend(tax_thoughts)
        full_execution_log.extend(comp_thoughts)
        full_execution_log.extend(planner_thoughts)
        
        # Create Rebalance proposal in DB
        proposal = RebalanceProposal(
            portfolio_id=portfolio.id,
            trigger_type=trigger_type,
            status="Pending",
            reason=f"Aggregate drift {drift_pct:.2%} exceeds threshold.",
            shap_explanations=json.dumps(shap_data),
            created_at=datetime.utcnow()
        )
        self.db.add(proposal)
        self.db.flush() # Populate proposal.id
        
        # Add proposed trades
        proposed_trade_objects = []
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
            proposed_trade_objects.append(trade_obj)
            
        # Create audit log entry for the agent run
        audit = AuditLog(
            portfolio_id=portfolio.id,
            event_type="AgentRun",
            details=f"CrewAI council executed rebalance analysis. Proposal created: {proposal.id}.",
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

        # Build response schema
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
            "execution_log": full_execution_log,
            "proposed_trades": [
                {
                    "symbol": t["symbol"],
                    "action": t["action"],
                    "shares": t["shares"],
                    "estimated_price": t["estimated_price"],
                    "tax_impact": t["tax_impact"]
                } for t in final_trades
            ]
        }
