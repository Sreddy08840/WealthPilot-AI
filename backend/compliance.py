from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Any
from sqlalchemy.orm import Session
from database import TaxLot, Portfolio, PortfolioHolding, Asset

# Global compliance config
RESTRICTED_LIST = ["BTC", "COIN", "TSLA", "MSTR"]  # Example restricted tickers
CONCENTRATION_LIMIT = 0.80  # Max 80% in a single ETF
ALT_CONCENTRATION_LIMIT = 0.20 # Max 20% in alternative assets like GLD

# Tax harvesting proxy tickers to avoid wash sale rules
HARVESTING_PROXIES = {
    "SPY": "IVV", # S&P 500 alternative
    "QQQ": "ONEQ", # Nasdaq alternative
    "AGG": "BND", # Total bond alternative
    "GLD": "IAU", # Gold alternative
}

def run_pre_trade_compliance(
    db: Session,
    portfolio_id: str,
    proposed_trades: List[Dict[str, Any]]
) -> Tuple[bool, List[str], List[Dict[str, Any]]]:
    """
    Runs pre-trade compliance checks.
    Returns:
        is_compliant: bool
        violations: List[str]
        modified_trades: List[Dict[str, Any]] (modified to comply if necessary, or empty if blocked)
    """
    violations = []
    modified_trades = [trade.copy() for trade in proposed_trades]
    portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
    
    if not portfolio:
        return False, ["Portfolio not found."], []

    # 1. Restricted List Check
    for trade in proposed_trades:
        symbol = trade["symbol"]
        if symbol in RESTRICTED_LIST:
            violations.append(f"Compliance Violation: Symbol {symbol} is on the firm's Restricted List.")
            # Remove this trade from modified trades
            modified_trades = [t for t in modified_trades if t["symbol"] != symbol]

    # 2. Wash Sale Rule Check (30-day window)
    # Check if we are BUYING an asset where we have sold shares at a loss in the past 30 days
    # Or if we are SELLING at a loss to harvest, and buying the identical asset in the proposed trades.
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    
    # Query tax lots to see if we have recently harvested/sold this asset at a loss, or if we have a lot purchased at a loss
    # For a real system we look at transaction history, but we can look at our seeded tax lots
    for trade in proposed_trades:
        symbol = trade["symbol"]
        action = trade["action"]
        
        if action == "BUY":
            # Check if there is any harvested tax lot for this asset in the last 30 days that realized a loss
            # For simulation, let's check if the client recently executed a tax-loss harvest of this asset.
            # In our db, we can check if they have a TaxLot of this asset where purchase_price > current_price and is_harvested = True
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
                    f"Redirected proposed purchase to proxy asset: {proxy_symbol}."
                )
                
                # Modify trade to buy proxy instead of original symbol
                for t in modified_trades:
                    if t["symbol"] == symbol and t["action"] == "BUY":
                        t["symbol"] = proxy_symbol
                        # Update price to proxy price if available
                        proxy_asset = db.query(Asset).filter(Asset.symbol == proxy_symbol).first()
                        if proxy_asset:
                            t["estimated_price"] = proxy_asset.current_price

    # 3. Concentration Limit Check
    # Estimate post-trade weights for all holdings
    portfolio_value = portfolio.current_value
    current_holdings = {h.asset_symbol: h.market_value for h in portfolio.holdings}
    cash = portfolio.cash_balance
    
    # Apply proposed trades to estimate new values
    projected_holdings = current_holdings.copy()
    projected_cash = cash
    
    for trade in modified_trades:
        symbol = trade["symbol"]
        action = trade["action"]
        shares = trade["shares"]
        price = trade["estimated_price"]
        trade_value = shares * price
        
        if action == "BUY":
            projected_holdings[symbol] = projected_holdings.get(symbol, 0.0) + trade_value
            projected_cash -= trade_value
        elif action == "SELL":
            projected_holdings[symbol] = max(0.0, projected_holdings.get(symbol, 0.0) - trade_value)
            projected_cash += trade_value
            
    # Check concentration constraints on projected values
    for symbol, val in projected_holdings.items():
        weight = val / portfolio_value if portfolio_value > 0 else 0
        asset = db.query(Asset).filter(Asset.symbol == symbol).first()
        
        if asset:
            if asset.asset_class == "Alternative" and weight > ALT_CONCENTRATION_LIMIT:
                violations.append(
                    f"Concentration Violation: {symbol} allocation ({weight:.1%}) exceeds the alternative asset limit of {ALT_CONCENTRATION_LIMIT:.1%}."
                )
                # Scale down buy trade if applicable
                for t in modified_trades:
                    if t["symbol"] == symbol and t["action"] == "BUY":
                        allowed_val = (portfolio_value * ALT_CONCENTRATION_LIMIT) - current_holdings.get(symbol, 0.0)
                        if allowed_val > 0:
                            t["shares"] = round(allowed_val / t["estimated_price"], 4)
                        else:
                            modified_trades = [x for x in modified_trades if not (x["symbol"] == symbol and x["action"] == "BUY")]
                            
            elif weight > CONCENTRATION_LIMIT:
                violations.append(
                    f"Concentration Violation: {symbol} allocation ({weight:.1%}) exceeds single asset limit of {CONCENTRATION_LIMIT:.1%}."
                )
                # Scale down buy trade
                for t in modified_trades:
                    if t["symbol"] == symbol and t["action"] == "BUY":
                        allowed_val = (portfolio_value * CONCENTRATION_LIMIT) - current_holdings.get(symbol, 0.0)
                        if allowed_val > 0:
                            t["shares"] = round(allowed_val / t["estimated_price"], 4)
                        else:
                            modified_trades = [x for x in modified_trades if not (x["symbol"] == symbol and x["action"] == "BUY")]

    is_compliant = len(violations) == 0
    return is_compliant, violations, modified_trades
