import os
import sys
from datetime import datetime, timedelta

# Path patch to support running tests from any folder context
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from app.rebalancing.tax_optimizer import TaxOptimizer

@pytest.fixture
def tax_optimizer():
    return TaxOptimizer(ordinary_rate=0.35, ltcg_rate=0.15)

def test_holding_period_and_gain_classification(tax_optimizer):
    """
    Test lot classifications:
    - Lot 1: bought 10 days ago, current price < purchase price -> STCL
    - Lot 2: bought 400 days ago, current price > purchase price -> LTCG
    - Lot 3: bought 10 days ago, current price > purchase price -> STCG
    - Lot 4: bought 400 days ago, current price < purchase price -> LTCL
    """
    now = datetime(2026, 6, 8)
    current_price = 500.0
    
    # Lot 1: short-term loss
    lot1 = {
        "id": "lot-1", "symbol": "SPY", "shares": 100.0,
        "purchase_price": 550.0, "purchase_date": now - timedelta(days=10)
    }
    res1 = tax_optimizer.classify_lot(lot1, current_price, now)
    assert res1["classification"] == "STCL"
    assert res1["is_long_term"] is False
    assert res1["total_gain_loss"] == -5000.0
    assert res1["total_tax_impact"] == -1750.0 # -5000 * 0.35
    
    # Lot 2: long-term gain
    lot2 = {
        "id": "lot-2", "symbol": "SPY", "shares": 100.0,
        "purchase_price": 400.0, "purchase_date": now - timedelta(days=400)
    }
    res2 = tax_optimizer.classify_lot(lot2, current_price, now)
    assert res2["classification"] == "LTCG"
    assert res2["is_long_term"] is True
    assert res2["total_gain_loss"] == 10000.0
    assert res2["total_tax_impact"] == 1500.0 # 10000 * 0.15

def test_tax_loss_harvesting_priority(tax_optimizer):
    """
    Given two loss lots:
    - Lot A: purchase price $550, bought 10 days ago (STCL) -> T = 0.35 * -50 = -17.5
    - Lot B: purchase price $540, bought 400 days ago (LTCL) -> T = 0.15 * -40 = -6.0
    We want to sell 50 shares of SPY (current price $500).
    The optimizer must prioritize Lot A (STCL) because it has the most negative tax liability rate (largest tax saving).
    """
    now = datetime(2026, 6, 8)
    current_prices = {"SPY": 500.0}
    sell_targets = {"SPY": 50.0}
    
    lots = [
        {"id": "lot-A", "symbol": "SPY", "shares": 100.0, "purchase_price": 550.0, "purchase_date": now - timedelta(days=10)},
        {"id": "lot-B", "symbol": "SPY", "shares": 100.0, "purchase_price": 540.0, "purchase_date": now - timedelta(days=400)}
    ]
    
    result = tax_optimizer.optimize_sales(lots, current_prices, sell_targets, now)
    proposed = result["proposed_trades"]
    
    assert len(proposed) == 1
    assert proposed[0]["lot_id"] == "lot-A"
    assert proposed[0]["shares_sold"] == 50.0
    assert proposed[0]["classification"] == "STCL"

def test_gain_deferral_priority(tax_optimizer):
    """
    Given two gain lots:
    - Lot C: purchase price $400, bought 10 days ago (STCG) -> T = 0.35 * 100 = +35.0
    - Lot D: purchase price $410, bought 400 days ago (LTCG) -> T = 0.15 * 90 = +13.5
    We want to sell 50 shares of SPY (current price $500).
    The optimizer must prioritize Lot D (LTCG) because it has a lower tax liability rate (LTCG tax rate 15% is less than ordinary rate 35%).
    This defers the higher-tax short-term gain of Lot C.
    """
    now = datetime(2026, 6, 8)
    current_prices = {"SPY": 500.0}
    sell_targets = {"SPY": 50.0}
    
    lots = [
        {"id": "lot-C", "symbol": "SPY", "shares": 100.0, "purchase_price": 400.0, "purchase_date": now - timedelta(days=10)},
        {"id": "lot-D", "symbol": "SPY", "shares": 100.0, "purchase_price": 410.0, "purchase_date": now - timedelta(days=400)}
    ]
    
    result = tax_optimizer.optimize_sales(lots, current_prices, sell_targets, now)
    proposed = result["proposed_trades"]
    
    assert len(proposed) == 1
    assert proposed[0]["lot_id"] == "lot-D"
    assert proposed[0]["shares_sold"] == 50.0
    assert proposed[0]["classification"] == "LTCG"

def test_partial_lot_split_execution(tax_optimizer):
    """
    Test lot splitting when the sell target exceeds the first lot size.
    Sell target = 150 shares.
    - Lot A: 100 shares of SPY (STCL, priority 1)
    - Lot B: 100 shares of SPY (LTCG, priority 2)
    Result should fully liquidate Lot A (100 shares) and partially sell from Lot B (50 shares).
    """
    now = datetime(2026, 6, 8)
    current_prices = {"SPY": 500.0}
    sell_targets = {"SPY": 150.0}
    
    lots = [
        {"id": "lot-A", "symbol": "SPY", "shares": 100.0, "purchase_price": 550.0, "purchase_date": now - timedelta(days=10)},
        {"id": "lot-B", "symbol": "SPY", "shares": 100.0, "purchase_price": 450.0, "purchase_date": now - timedelta(days=400)}
    ]
    
    result = tax_optimizer.optimize_sales(lots, current_prices, sell_targets, now)
    proposed = result["proposed_trades"]
    
    assert len(proposed) == 2
    
    # Trade 1: Full sale of Lot A
    assert proposed[0]["lot_id"] == "lot-A"
    assert proposed[0]["shares_sold"] == 100.0
    
    # Trade 2: Partial sale of Lot B
    assert proposed[1]["lot_id"] == "lot-B"
    assert proposed[1]["shares_sold"] == 50.0
