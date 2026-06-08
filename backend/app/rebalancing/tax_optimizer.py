"""
WealthPilot AI - Tax Optimization Engine

Mathematical Rules:
1. Holding Period (HP):
   HP = Current Date - Purchase Date
   - If HP > 365 days: Long-Term (LTCG / LTCL)
   - If HP <= 365 days: Short-Term (STCG / STCL)

2. Capital Gain / Loss (per share Delta):
   Delta = Current Price - Purchase Price

3. Tax Liability Rate (T) per share:
   T = Tax Rate * Delta
   where:
   - For Gains (Delta >= 0):
     - Short-Term: Ordinary Income Rate (default: 35%)
     - Long-Term: LTCG Rate (default: 15%)
   - For Losses (Delta < 0):
     - Short-Term: Ordinary Income Offset Rate (default: 35%)
     - Long-Term: LTCG Offset Rate (default: 15%)

4. Optimization Priority:
   To minimize tax liability, we sort available tax lots in ascending order of T.
   This automatically results in the following lot-picking hierarchy:
   - Priority 1: Large Short-Term Losses (most negative T)
   - Priority 2: Large Long-Term Losses (moderate negative T)
   - Priority 3: Small Long-Term Losses
   - Priority 4: Small Short-Term Losses
   - Priority 5: Small Long-Term Gains (smallest positive T)
   - Priority 6: Large Long-Term Gains
   - Priority 7: Small Short-Term Gains
   - Priority 8: Large Short-Term Gains (most positive T, deferred last)
"""

from datetime import datetime
from typing import Dict, List, Any, Tuple

class TaxOptimizer:
    def __init__(self, ordinary_rate: float = 0.35, ltcg_rate: float = 0.15):
        """
        Initializes the Tax Optimizer with specified tax brackets.
        """
        self.ordinary_rate = ordinary_rate
        self.ltcg_rate = ltcg_rate

    def classify_lot(
        self,
        lot: Dict[str, Any],
        current_price: float,
        current_date: datetime
    ) -> Dict[str, Any]:
        """
        Classifies a single tax lot and calculates its tax liability rate per share.
        """
        purchase_date = lot["purchase_date"]
        # Convert string to datetime if passed as string
        if isinstance(purchase_date, str):
            purchase_date = datetime.fromisoformat(purchase_date.replace("Z", ""))
            
        purchase_price = lot["purchase_price"]
        shares = lot["shares"]
        
        # 1. Holding Period Check
        holding_period = current_date - purchase_date
        is_long_term = holding_period.days > 365
        
        # 2. Gain / Loss Calculation
        gain_loss_per_share = current_price - purchase_price
        total_gain_loss = shares * gain_loss_per_share
        
        # 3. Tax Rate mapping and classification
        if gain_loss_per_share >= 0:
            # Gain lot
            tax_rate = self.ltcg_rate if is_long_term else self.ordinary_rate
            classification = "LTCG" if is_long_term else "STCG"
        else:
            # Loss lot (Offset savings rate)
            tax_rate = self.ltcg_rate if is_long_term else self.ordinary_rate
            classification = "LTCL" if is_long_term else "STCL"
            
        tax_liability_per_share = tax_rate * gain_loss_per_share
        total_tax_impact = shares * tax_liability_per_share
        
        return {
            "lot_id": lot["id"],
            "symbol": lot["symbol"],
            "shares": shares,
            "purchase_price": purchase_price,
            "purchase_date": purchase_date,
            "current_price": current_price,
            "gain_loss_per_share": round(gain_loss_per_share, 4),
            "total_gain_loss": round(total_gain_loss, 2),
            "is_long_term": is_long_term,
            "classification": classification,
            "tax_rate": tax_rate,
            "tax_liability_per_share": round(tax_liability_per_share, 4),
            "total_tax_impact": round(total_tax_impact, 2)
        }

    def optimize_sales(
        self,
        lots: List[Dict[str, Any]],
        current_prices: Dict[str, float],
        sell_targets: Dict[str, float],
        current_date: datetime
    ) -> Dict[str, Any]:
        """
        Compiles a tax-efficient list of trades given sell targets and available lots.
        """
        trade_list = []
        net_capital_gain_loss = 0.0
        net_tax_impact = 0.0
        
        # Group open lots by symbol
        lots_by_symbol = {}
        for lot in lots:
            sym = lot["symbol"]
            if sym not in lots_by_symbol:
                lots_by_symbol[sym] = []
            lots_by_symbol[sym].append(lot)
            
        # Process each sell target asset
        for symbol, target_shares_to_sell in sell_targets.items():
            if target_shares_to_sell <= 0:
                continue
                
            current_price = current_prices.get(symbol)
            if current_price is None:
                raise ValueError(f"Current price for asset {symbol} not provided.")
                
            asset_lots = lots_by_symbol.get(symbol, [])
            if not asset_lots:
                # No lots available to sell, cash/BIL representation or structural anomaly
                continue
                
            # Classify all available lots of this asset
            classified_lots = [self.classify_lot(lot, current_price, current_date) for lot in asset_lots]
            
            # Sort lots by tax liability rate per share ascending (most negative / tax-saving first)
            # This automatically harvests largest STCL first, LTCL second, and defers STCG to the absolute end.
            classified_lots.sort(key=lambda x: x["tax_liability_per_share"])
            
            shares_needed = target_shares_to_sell
            for lot in classified_lots:
                if shares_needed <= 0:
                    break
                    
                shares_available = lot["shares"]
                shares_selling = min(shares_available, shares_needed)
                shares_needed -= shares_selling
                
                # Pro-rate lot values
                ratio = shares_selling / shares_available
                lot_gain_loss = lot["total_gain_loss"] * ratio
                lot_tax_impact = lot["total_tax_impact"] * ratio
                
                net_capital_gain_loss += lot_gain_loss
                net_tax_impact += lot_tax_impact
                
                trade_list.append({
                    "lot_id": lot["lot_id"],
                    "symbol": symbol,
                    "action": "SELL",
                    "shares_sold": round(shares_selling, 4),
                    "purchase_price": lot["purchase_price"],
                    "purchase_date": lot["purchase_date"].isoformat() + "Z",
                    "execution_price": current_price,
                    "realized_gain_loss": round(lot_gain_loss, 2),
                    "tax_impact": round(lot_tax_impact, 2),
                    "classification": lot["classification"]
                })
                
            # If we went through all lots and still need shares, log warning or default to generic balance deduction
            if shares_needed > 0.0001:
                # This would occur if we tried to sell more than we own
                trade_list.append({
                    "symbol": symbol,
                    "action": "SELL_UNTRACKED",
                    "shares_sold": round(shares_needed, 4),
                    "execution_price": current_price,
                    "realized_gain_loss": 0.00,
                    "tax_impact": 0.00,
                    "classification": "UNTRACKED"
                })
                
        return {
            "proposed_trades": trade_list,
            "net_capital_gain_loss": round(net_capital_gain_loss, 2),
            "net_tax_impact": round(net_tax_impact, 2),
            "tax_savings_harvested": round(-net_tax_impact, 2) if net_tax_impact < 0 else 0.00
        }
