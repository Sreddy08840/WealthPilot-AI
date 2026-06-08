import os
import sys
from datetime import datetime

# Path patch to locate modular app directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from app.rebalancing.xai_explainer import XAIExplainer

@pytest.fixture
def xai_explainer():
    return XAIExplainer()

def test_lime_surrogate_coefficients(xai_explainer):
    """
    Verify LIME local surrogate fitting:
    - Current state: moderate drift (0.06), some tax savings (0.005), moderate volatility (0.18)
    - Run LIME surrogate.
    - Check that coefficients exist for all 5 features.
    """
    current_state = {
        "drift_magnitude": 0.06,
        "tax_savings": 0.005,
        "cash_drift": 0.02,
        "transaction_cost": 0.0001,
        "market_volatility": 0.18
    }
    
    res = xai_explainer.run_lime_surrogate(current_state, num_perturbations=50)
    
    assert "intercept" in res
    assert "lime_coefficients" in res
    coefs = res["lime_coefficients"]
    
    # Assert all 5 features are represented
    assert "drift_magnitude" in coefs
    assert "tax_savings" in coefs
    assert "cash_drift" in coefs
    assert "transaction_cost" in coefs
    assert "market_volatility" in coefs

def test_shap_waterfall_accumulation(xai_explainer):
    """
    Test that the SHAP waterfall running values correctly sum to the final output.
    """
    mock_shap_explanation = {
        "base_value": 0.20,
        "output_value": 0.65,
        "shap_values": {
            "drift_magnitude": 0.30,
            "tax_savings": 0.15,
            "cash_drift": 0.05,
            "market_volatility": 0.05,
            "transaction_cost": -0.10
        }
    }
    
    waterfall = xai_explainer.get_shap_waterfall(mock_shap_explanation)
    
    assert len(waterfall) == 6 # Base + 5 features
    assert waterfall[0]["running_value"] == 0.20 # Base
    assert waterfall[5]["running_value"] == 0.65 # Final output value

def test_compiled_narrative_contents(xai_explainer):
    """
    Verify narrative compilers output customized reports injecting target details.
    """
    mock_shap = {
        "base_value": 0.20,
        "output_value": 0.65,
        "shap_values": {
            "drift_magnitude": 0.35,
            "tax_savings": 0.20
        }
    }
    
    reports = xai_explainer.compile_narratives(
        portfolio_id="p-uuid-00001",
        client_name="Sarah Connor",
        account_number="WP-000451",
        drift_pct=0.062,
        tax_savings=2976.00,
        is_compliant=True,
        shap_explanation=mock_shap
    )
    
    assert "client" in reports
    assert "advisor" in reports
    assert "compliance" in reports
    
    assert "Sarah Connor" in reports["client"]
    assert "2976.00" in reports["client"]
    assert "WP-000451" in reports["advisor"]
    assert "SEBI Pre-Trade Audit" in reports["compliance"]

def test_ascii_plots_rendering(xai_explainer):
    """
    Test that plot drawers generate strings containing characters and formatted values.
    """
    shap_vals = {
        "drift_magnitude": 0.45,
        "tax_savings": 0.35,
        "market_volatility": 0.20,
        "cash_drift": 0.05,
        "transaction_cost": -0.10
    }
    
    summary_plot = xai_explainer.draw_summary_plot(shap_vals)
    assert "drift_magnitude" in summary_plot
    assert "█" in summary_plot
    
    mock_shap = {
        "base_value": 0.20,
        "output_value": 0.65,
        "shap_values": shap_vals
    }
    waterfall = xai_explainer.get_shap_waterfall(mock_shap)
    waterfall_plot = xai_explainer.draw_waterfall_plot(waterfall)
    
    assert "Base Expectation" in waterfall_plot
    assert "Value:" in waterfall_plot
    assert "█" in waterfall_plot
