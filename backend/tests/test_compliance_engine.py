import os
import sys

# Path patch to locate modular app directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from app.rebalancing.compliance_engine import SEBIComplianceEngine

@pytest.fixture
def compliance_engine():
    return SEBIComplianceEngine(single_asset_limit=0.25, sector_limit=0.25)

def test_risk_suitability_routing(compliance_engine):
    """
    Test risk suitability checks:
    - Low Risk client: Conservative (Pass), Balanced (Fail), Aggressive (Fail)
    - High Risk client: Conservative (Pass), Balanced (Pass), Aggressive (Pass)
    """
    # Low Risk Client
    ok1, msg1 = compliance_engine.validate_risk_suitability("Low", "Conservative")
    assert ok1 is True
    
    ok2, msg2 = compliance_engine.validate_risk_suitability("Low", "Balanced")
    assert ok2 is False
    assert "Suitability Failure" in msg2
    
    ok3, msg3 = compliance_engine.validate_risk_suitability("Low", "Aggressive")
    assert ok3 is False

    # High Risk Client
    ok4, msg4 = compliance_engine.validate_risk_suitability("High", "Aggressive")
    assert ok4 is True

def test_single_asset_concentration_ceiling(compliance_engine):
    """
    Test that holding more than 25% in a non-cash individual security triggers a violation.
    GLD is Alternative class. Holding 28% should fail.
    """
    holdings = [
        {"symbol": "SPY", "market_value": 72000.0}, # 72%
        {"symbol": "GLD", "market_value": 28000.0}  # 28% (Exceeds 25% limit)
    ]
    
    res = compliance_engine.validate_portfolio(
        client_risk_profile="High",
        portfolio_risk_category="Balanced",
        current_holdings=holdings,
        cash_balance=0.0,
        total_value=100000.0
    )
    
    assert res["status"] == "FAIL"
    assert any("Concentration Violation" in v and "GLD" in v for v in res["violations"])

def test_sector_exposure_ceiling(compliance_engine):
    """
    Test that holding more than 25% in a narrow industry sector (e.g. Technology) triggers a violation.
    QQQ maps to Technology sector. Holding 30% Tech exposure should fail.
    """
    holdings = [
        {"symbol": "SPY", "market_value": 70000.0}, # US Diversified Equity (Exempt)
        {"symbol": "QQQ", "market_value": 30000.0}  # Technology sector (30% -> exceeds 25%)
    ]
    
    res = compliance_engine.validate_portfolio(
        client_risk_profile="High",
        portfolio_risk_category="Balanced",
        current_holdings=holdings,
        cash_balance=0.0,
        total_value=100000.0
    )
    
    assert res["status"] == "FAIL"
    assert any("Sector Exposure Violation" in v and "Technology" in v for v in res["violations"])

def test_pre_trade_clearance_projections(compliance_engine):
    """
    Verify pre-trade clearance:
    - Current holdings are compliant: SPY (80%), QQQ (20%). Technology = 20%.
    - Proposed trade: BUY QQQ worth $8,000 (raises QQQ to 28% weight).
    - Result should project post-trade state, fail validation, and flag Technology sector violation.
    """
    holdings = [
        {"symbol": "SPY", "market_value": 80000.0},
        {"symbol": "QQQ", "market_value": 20000.0}
    ]
    
    # BUY trade that pushes QQQ past concentration limits
    trades = [
        {"symbol": "QQQ", "action": "BUY", "shares": 80.0, "price": 100.0} # $8,000 value
    ]
    
    res = compliance_engine.validate_portfolio(
        client_risk_profile="High",
        portfolio_risk_category="Balanced",
        current_holdings=holdings,
        cash_balance=10000.0,
        total_value=110000.0,
        proposed_trades=trades
    )
    
    assert res["status"] == "FAIL"
    assert any("Technology" in v for v in res["violations"])
