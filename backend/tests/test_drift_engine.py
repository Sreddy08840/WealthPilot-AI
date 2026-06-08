import os
import sys

# Path patch to locate modular app directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from app.rebalancing.drift_engine import DriftDetectionEngine

@pytest.fixture
def drift_engine():
    return DriftDetectionEngine()

def test_zero_drift_portfolio(drift_engine):
    """
    Test that when current weights match target weights perfectly:
    - Absolute Drift = 0.0
    - Tracking Error = 0.0
    - No triggers are fired
    """
    target = {"SPY": 0.50, "AGG": 0.50}
    current = {"SPY": 0.50, "AGG": 0.50}
    
    abs_drift = drift_engine.calculate_absolute_drift(current, target)
    te = drift_engine.calculate_tracking_error(current, target)
    triggers = drift_engine.check_rebalance_triggers(current, target)
    
    assert abs_drift == 0.0
    assert te == 0.0
    assert triggers["rebalance_required"] is False
    assert triggers["triggers"]["drift_triggered"] is False
    assert triggers["triggers"]["tracking_error_triggered"] is False

def test_drift_threshold_trigger(drift_engine):
    """
    Test that aggregate drift exceeding the 5% threshold fires a trigger
    """
    # Current has drifted by 6.0% absolute (SPY overweight by 6%, AGG underweight by 6%)
    # D_abs = 0.5 * (|0.56 - 0.50| + |0.44 - 0.50|) = 0.5 * (0.06 + 0.06) = 0.06 (6%)
    target = {"SPY": 0.50, "AGG": 0.50}
    current = {"SPY": 0.56, "AGG": 0.44}
    
    abs_drift = drift_engine.calculate_absolute_drift(current, target)
    triggers = drift_engine.check_rebalance_triggers(current, target, drift_threshold=0.05)
    
    assert abs_drift == pytest.approx(0.06)
    assert triggers["rebalance_required"] is True
    assert triggers["triggers"]["drift_triggered"] is True

def test_tracking_error_trigger(drift_engine):
    """
    Test that massive differences in equity/bond allocations generate high tracking error
    and trigger a rebalance even if we set drift threshold high.
    Target: 100% AGG (Bonds)
    Current: 100% SPY (S&P 500 Equities)
    """
    target = {"AGG": 1.0}
    current = {"SPY": 1.0}
    
    te = drift_engine.calculate_tracking_error(current, target)
    triggers = drift_engine.check_rebalance_triggers(
        current, target, 
        drift_threshold=1.5, # set high to isolate TE check
        te_limit=0.02
    )
    
    # SPY vol = 16%, AGG vol = 5%, corr = -0.10.
    # Active weights vector: a = [w_spy_curr - w_spy_targ, w_agg_curr - w_agg_targ] = [1.0 - 0.0, 0.0 - 1.0] = [1.0, -1.0]
    # Variance of active weights:
    # var_te = 1.0^2 * sigma_spy^2 + (-1.0)^2 * sigma_agg^2 + 2 * (1.0) * (-1.0) * cov_spy_agg
    #        = 0.16^2 + 0.05^2 - 2 * (-0.10 * 0.16 * 0.05)
    #        = 0.0256 + 0.0025 + 0.0016 = 0.0297
    # TE = sqrt(0.0297) = 0.1723 (17.23%)
    assert te > 0.15 # tracking error should be high (approx 17.2%)
    assert triggers["rebalance_required"] is True
    assert triggers["triggers"]["tracking_error_triggered"] is True

def test_volatility_risk_increase_trigger(drift_engine):
    """
    Test that a significant increase in portfolio risk score (volatility) triggers a rebalance.
    """
    # Baseline was low risk: 100% Bonds (AGG)
    # Volatility of AGG is 5% -> Risk Score = 5.0
    baseline_risk_score = 5.0
    
    # Current shifts to high risk: 100% Equities (QQQ)
    # Volatility of QQQ is 20% -> Risk Score = 20.0
    current_high_risk = {"QQQ": 1.0}
    
    triggers = drift_engine.check_rebalance_triggers(
        current_weights=current_high_risk,
        target_weights={"QQQ": 1.0}, # targets are matching to isolate risk trigger
        previous_risk_score=baseline_risk_score,
        risk_increase_limit=2.0
    )
    
    assert triggers["risk_score"] == 20.0
    assert triggers["rebalance_required"] is True
    assert triggers["triggers"]["risk_triggered"] is True
