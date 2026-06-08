import json
import random
from datetime import datetime, timedelta
from database import SessionLocal, RiskCategory, Portfolio, Asset, PortfolioHolding, TaxLot, init_db

# Assets and their current prices
ASSETS_DATA = [
    {"symbol": "SPY", "name": "SPDR S&P 500 ETF Trust", "asset_class": "Equity", "current_price": 515.20},
    {"symbol": "QQQ", "name": "Invesco QQQ Trust", "asset_class": "Equity", "current_price": 438.50},
    {"symbol": "IWM", "name": "iShares Russell 2000 ETF", "asset_class": "Equity", "current_price": 202.10},
    {"symbol": "AGG", "name": "iShares Core U.S. Aggregate Bond ETF", "asset_class": "Fixed Income", "current_price": 98.40},
    {"symbol": "BND", "name": "Vanguard Total Bond Market ETF", "asset_class": "Fixed Income", "current_price": 72.80},
    {"symbol": "GLD", "name": "SPDR Gold Shares", "asset_class": "Alternative", "current_price": 215.60},
    {"symbol": "BIL", "name": "SPDR Bloomberg 1-3 Month T-Bill ETF", "asset_class": "Cash", "current_price": 91.50},
]

# Risk Categories and target allocations
RISK_CATEGORIES_DATA = [
    {
        "id": 1,
        "name": "Conservative",
        "target_allocation": {"SPY": 0.15, "AGG": 0.50, "BIL": 0.30, "GLD": 0.05}
    },
    {
        "id": 2,
        "name": "Moderately Conservative",
        "target_allocation": {"SPY": 0.30, "AGG": 0.40, "BIL": 0.25, "GLD": 0.05}
    },
    {
        "id": 3,
        "name": "Balanced",
        "target_allocation": {"SPY": 0.45, "QQQ": 0.10, "AGG": 0.30, "BIL": 0.10, "GLD": 0.05}
    },
    {
        "id": 4,
        "name": "Growth",
        "target_allocation": {"SPY": 0.55, "QQQ": 0.15, "IWM": 0.05, "AGG": 0.15, "BIL": 0.05, "GLD": 0.05}
    },
    {
        "id": 5,
        "name": "Aggressive",
        "target_allocation": {"SPY": 0.60, "QQQ": 0.20, "IWM": 0.10, "AGG": 0.05, "GLD": 0.05}
    }
]

FIRST_NAMES = ["John", "Sarah", "Michael", "Emily", "David", "Jessica", "James", "Ashley", "Robert", "Amanda", 
               "Joseph", "Olivia", "Daniel", "Sophia", "Matthew", "Isabella", "William", "Mia", "Andrew", "Charlotte",
               "Thomas", "Emma", "Charles", "Grace", "Paul", "Lily", "Mark", "Ava", "Kevin", "Chloe"]
LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez", 
              "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin",
              "Lee", "Perez", "Thompson", "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson"]

def seed_database(num_portfolios=5000):
    db = SessionLocal()
    try:
        # Check if database is already seeded
        if db.query(Asset).first() is not None:
            print("Database already seeded. Skipping...")
            return

        print("Initializing tables...")
        init_db()

        print("Seeding Assets...")
        assets = []
        prices_dict = {}
        for asset_data in ASSETS_DATA:
            asset = Asset(**asset_data)
            db.add(asset)
            assets.append(asset)
            prices_dict[asset_data["symbol"]] = asset_data["current_price"]
        db.commit()

        print("Seeding Risk Categories...")
        categories = []
        for cat_data in RISK_CATEGORIES_DATA:
            cat = RiskCategory(
                id=cat_data["id"],
                name=cat_data["name"],
                target_allocation=json.dumps(cat_data["target_allocation"])
            )
            db.add(cat)
            categories.append(cat)
        db.commit()

        print(f"Generating {num_portfolios} portfolios...")
        
        # We will collect all portfolios, holdings, and tax lots to bulk save them
        portfolios_to_insert = []
        holdings_to_insert = []
        tax_lots_to_insert = []
        
        for i in range(1, num_portfolios + 1):
            p_id = f"p-uuid-{i:05d}"
            account_number = f"WP-{i:06d}"
            client_name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
            
            # 5 risk categories, weighted towards Balanced & Growth
            cat_choice = random.choices(categories, weights=[15, 20, 35, 20, 10], k=1)[0]
            cat_id = cat_choice.id
            targets = json.loads(cat_choice.target_allocation)
            
            # Value of the portfolio
            total_value = round(random.lognormvariate(11.5, 1.2), 2)
            if total_value < 10000:
                total_value = 10000.00
            elif total_value > 5000000:
                total_value = 5000000.00
                
            # Random cash balance (between 0.5% and 5% typically, occasionally more)
            cash_pct = random.choices([0.01, 0.02, 0.05, 0.12], weights=[60, 25, 10, 5], k=1)[0]
            cash_balance = round(total_value * cash_pct, 2)
            investable_value = total_value - cash_balance
            
            # Auto rebalance flag
            auto_rebalance = random.choice([True, False])
            
            # Drift simulation:
            # - 70% portfolios have small/healthy drift (0% to 4%)
            # - 30% portfolios have drifted out of bounds (> 5% drift, up to 18%)
            is_drifted = random.random() < 0.30
            
            actual_allocations = {}
            if not is_drifted:
                # Close to targets
                remaining = 1.0
                target_keys = list(targets.keys())
                for sym in target_keys[:-1]:
                    noise = random.uniform(-0.015, 0.015)
                    actual_allocations[sym] = max(0.01, targets[sym] + noise)
                    remaining -= actual_allocations[sym]
                actual_allocations[target_keys[-1]] = max(0.01, remaining)
            else:
                # Highly drifted allocation
                remaining = 1.0
                target_keys = list(targets.keys())
                for sym in target_keys[:-1]:
                    # Significant positive or negative drift
                    drift = random.uniform(-0.12, 0.12)
                    actual_allocations[sym] = max(0.01, targets[sym] + drift)
                    remaining -= actual_allocations[sym]
                actual_allocations[target_keys[-1]] = max(0.01, remaining)
                
            # Normalize actual allocations to equal 1.0
            sum_allocs = sum(actual_allocations.values())
            for sym in actual_allocations:
                actual_allocations[sym] /= sum_allocs
                
            portfolio_obj = Portfolio(
                id=p_id,
                account_number=account_number,
                client_name=client_name,
                risk_category_id=cat_id,
                current_value=total_value,
                cash_balance=cash_balance,
                last_rebalanced=datetime.utcnow() - timedelta(days=random.randint(5, 120)),
                auto_rebalance=auto_rebalance
            )
            portfolios_to_insert.append(portfolio_obj)
            
            # Build holdings and tax lots
            for symbol, weight in actual_allocations.items():
                price = prices_dict[symbol]
                holding_value = investable_value * weight
                shares = holding_value / price
                
                holding_obj = PortfolioHolding(
                    id=f"h-uuid-{p_id}-{symbol}",
                    portfolio_id=p_id,
                    asset_symbol=symbol,
                    shares=shares,
                    market_value=holding_value
                )
                holdings_to_insert.append(holding_obj)
                
                # Split holding into 2-3 tax lots for HIFO and tax harvesting checks
                num_lots = random.randint(2, 3)
                lot_shares_remaining = shares
                
                for lot_idx in range(num_lots):
                    if lot_idx == num_lots - 1:
                        lot_shares = lot_shares_remaining
                    else:
                        lot_shares = lot_shares_remaining * random.uniform(0.3, 0.6)
                        lot_shares_remaining -= lot_shares
                        
                    # Let purchase price have some variance to simulate gains vs losses
                    # Some purchased in bull market (higher than current price -> loss lot)
                    # Some purchased earlier (lower than current price -> gain lot)
                    price_multiplier = random.choice([0.80, 0.90, 0.95, 1.05, 1.15])
                    purchase_price = round(price * price_multiplier, 2)
                    
                    # Purchase date between 10 days and 2 years ago
                    purchase_date = datetime.utcnow() - timedelta(days=random.randint(10, 730))
                    
                    lot_obj = TaxLot(
                        id=f"lot-uuid-{p_id}-{symbol}-{lot_idx}",
                        portfolio_id=p_id,
                        asset_symbol=symbol,
                        shares=lot_shares,
                        purchase_price=purchase_price,
                        purchase_date=purchase_date,
                        is_harvested=False
                    )
                    tax_lots_to_insert.append(lot_obj)
                    
        print(f"Bulk inserting {len(portfolios_to_insert)} portfolios...")
        db.bulk_save_objects(portfolios_to_insert)
        
        print(f"Bulk inserting {len(holdings_to_insert)} holdings...")
        db.bulk_save_objects(holdings_to_insert)
        
        print(f"Bulk inserting {len(tax_lots_to_insert)} tax lots...")
        db.bulk_save_objects(tax_lots_to_insert)
        
        db.commit()
        print("Database seeded successfully!")
        
    except Exception as e:
        db.rollback()
        print(f"Error during seeding: {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    seed_database(5000)
