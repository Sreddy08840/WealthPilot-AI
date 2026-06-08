"""
WealthPilot AI - SEBI Compliance Validation Engine

SEBI Regulatory & Suitability Rules:
1. Single Asset Concentration:
   - Max 25% of portfolio value in any single stock or individual asset (excluding Liquid Cash / BIL equivalents).
2. Sector Exposure Limit:
   - Max 25% exposure in any single industry sector (e.g. Technology, Commodities, Corporate Debt).
3. Risk Suitability:
   - Checks suitability based on client profile (Low, Medium, High) vs portfolio risk category.
     - Low Risk Client: Only allowed "Conservative" portfolios.
     - Medium Risk Client: Allowed "Conservative" and "Balanced" portfolios.
     - High Risk Client: Allowed "Conservative", "Balanced", and "Aggressive" portfolios.
4. Asset Allocation Scheme Mandates:
   - Adherence to product risk definitions:
     - Conservative Portfolio: Must hold >= 50% in Debt/Fixed Income.
     - Aggressive Portfolio: Must hold >= 70% in Equities.
"""

from typing import Dict, List, Any, Tuple

# Default Asset to Sector and Class mappings
ASSET_METADATA = {
    "SPY": {"sector": "US Diversified Equity", "class": "Equity"},
    "QQQ": {"sector": "Technology", "class": "Equity"},
    "IWM": {"sector": "US Small Cap Equity", "class": "Equity"},
    "AGG": {"sector": "Government Debt", "class": "Debt"},
    "BND": {"sector": "Corporate Debt", "class": "Debt"},
    "GLD": {"sector": "Precious Metals", "class": "Alternative"},
    "BIL": {"sector": "Liquid Cash", "class": "Cash"},
    "CASH": {"sector": "Liquid Cash", "class": "Cash"}
}

class SEBIComplianceEngine:
    def __init__(
        self,
        single_asset_limit: float = 0.25,
        sector_limit: float = 0.25,
        ordinary_debt_min_conservative: float = 0.50,
        equity_min_aggressive: float = 0.70
    ):
        self.single_asset_limit = single_asset_limit
        self.sector_limit = sector_limit
        self.ordinary_debt_min_conservative = ordinary_debt_min_conservative
        self.equity_min_aggressive = equity_min_aggressive

    def validate_risk_suitability(self, client_risk_profile: str, portfolio_risk_category: str) -> Tuple[bool, str]:
        """
        Verifies that the portfolio risk category does not exceed the client's risk tolerance.
        """
        profile_levels = {"Low": 1, "Medium": 2, "High": 3}
        category_levels = {
            "Conservative": 1,
            "Moderately Conservative": 1,
            "Balanced": 2,
            "Growth": 3,
            "Aggressive": 3
        }
        
        client_val = profile_levels.get(client_risk_profile, 1)
        portfolio_val = category_levels.get(portfolio_risk_category, 1)
        
        if portfolio_val > client_val:
            return False, (
                f"Suitability Failure: Client risk tolerance profile '{client_risk_profile}' (level {client_val}) "
                f"is insufficient for portfolio risk rating '{portfolio_risk_category}' (level {portfolio_val})."
            )
        return True, "Passed risk suitability check."

    def validate_portfolio_allocations(
        self,
        weights: Dict[str, float],
        risk_category: str
    ) -> List[str]:
        """
        Checks asset class levels against scheme mandates.
        """
        violations = []
        equity_total = 0.0
        debt_total = 0.0
        
        for symbol, weight in weights.items():
            meta = ASSET_METADATA.get(symbol, {"class": "Cash"})
            if meta["class"] == "Equity":
                equity_total += weight
            elif meta["class"] == "Debt":
                debt_total += weight

        if risk_category == "Conservative" and debt_total < self.ordinary_debt_min_conservative:
            violations.append(
                f"Scheme Mandate Violation: Conservative portfolio requires at least "
                f"{self.ordinary_debt_min_conservative:.1%} in Fixed Income/Debt. Current: {debt_total:.1%}."
            )
        elif risk_category == "Aggressive" and equity_total < self.equity_min_aggressive:
            violations.append(
                f"Scheme Mandate Violation: Aggressive portfolio requires at least "
                f"{self.equity_min_aggressive:.1%} in Equities. Current: {equity_total:.1%}."
            )
            
        return violations

    def validate_concentration_limits(self, weights: Dict[str, float]) -> List[str]:
        """
        Checks single asset concentration and sector limits.
        """
        violations = []
        sector_weights = {}
        
        for symbol, weight in weights.items():
            # Exclude liquid cash/BIL equivalents from single-ticker concentration penalty
            meta = ASSET_METADATA.get(symbol, {"sector": "Liquid Cash", "class": "Cash"})
            
            # 1. Single Asset Concentration check
            if meta["class"] != "Cash" and weight > self.single_asset_limit:
                violations.append(
                    f"Concentration Violation: Ticker '{symbol}' weight ({weight:.1%}) "
                    f"exceeds single-security cap of {self.single_asset_limit:.1%}."
                )
                
            # 2. Sector aggregation
            sector = meta["sector"]
            sector_weights[sector] = sector_weights.get(sector, 0.0) + weight

        # 3. Sector Limits check (Exempting US Diversified Equity index and Cash)
        for sector, weight in sector_weights.items():
            if sector not in ["US Diversified Equity", "Liquid Cash"] and weight > self.sector_limit:
                violations.append(
                    f"Sector Exposure Violation: Industry sector '{sector}' allocation ({weight:.1%}) "
                    f"exceeds SEBI exposure ceiling of {self.sector_limit:.1%}."
                )
                
        return violations

    def validate_portfolio(
        self,
        client_risk_profile: str,
        portfolio_risk_category: str,
        current_holdings: List[Dict[str, Any]],
        cash_balance: float,
        total_value: float,
        proposed_trades: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Aggregates suitability, concentration, and asset class checks.
        Computes both current and projected post-trade compliance states.
        """
        violations = []
        
        # 1. Suitability check
        suit_ok, suit_msg = self.validate_risk_suitability(client_risk_profile, portfolio_risk_category)
        if not suit_ok:
            violations.append(suit_msg)

        # 2. Compute allocations weights
        weights = {}
        if total_value > 0:
            for h in current_holdings:
                weights[h["symbol"]] = h["market_value"] / total_value
            weights["CASH"] = cash_balance / total_value
            
        # 3. Apply projected trades if provided
        projected_weights = weights.copy()
        if proposed_trades and total_value > 0:
            projected_cash = cash_balance
            projected_market_values = {h["symbol"]: h["market_value"] for h in current_holdings}
            
            for trade in proposed_trades:
                symbol = trade["symbol"]
                action = trade["action"]
                trade_shares = trade["shares"]
                price = trade["price"]
                trade_value = trade_shares * price
                
                if action == "BUY":
                    projected_market_values[symbol] = projected_market_values.get(symbol, 0.0) + trade_value
                    projected_cash -= trade_value
                elif action == "SELL":
                    projected_market_values[symbol] = max(0.0, projected_market_values.get(symbol, 0.0) - trade_value)
                    projected_cash += trade_value
                    
            # Normalize projected weights
            for sym, val in projected_market_values.items():
                projected_weights[sym] = val / total_value
            projected_weights["CASH"] = projected_cash / total_value

        # 4. Run rules on the target validation state (projected if trades provided, else current)
        target_weights = projected_weights if proposed_trades else weights
        
        allocation_violations = self.validate_portfolio_allocations(target_weights, portfolio_risk_category)
        violations.extend(allocation_violations)
        
        concentration_violations = self.validate_concentration_limits(target_weights)
        violations.extend(concentration_violations)
        
        status = "PASS" if len(violations) == 0 else "FAIL"
        
        return {
            "status": status,
            "violations": violations,
            "pre_trade_compliant": status == "PASS",
            "evaluated_weights": {k: round(v, 4) for k, v in target_weights.items()}
        }
