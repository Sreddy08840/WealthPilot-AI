import math
import itertools
from typing import Dict, List, Any

FEATURE_NAMES = [
    "drift_magnitude",
    "tax_savings",
    "cash_drift",
    "transaction_cost",
    "market_volatility"
]

def calculate_rebalance_utility(features: Dict[str, float]) -> float:
    w_drift = 8.5
    w_tax = 15.0
    w_cash = 3.0
    w_cost = -12.0
    w_vol = 1.5

    drift = features.get("drift_magnitude", 0.0)
    tax = features.get("tax_savings", 0.0)
    cash = features.get("cash_drift", 0.0)
    cost = features.get("transaction_cost", 0.0)
    vol = features.get("market_volatility", 0.15)

    utility = (
        (w_drift * drift) +
        (w_tax * tax) +
        (w_cash * cash) +
        (w_cost * cost) +
        (w_vol * vol)
    )
    return utility

def compute_exact_shapley_values(
    actual_features: Dict[str, float],
    baseline_features: Dict[str, float]
) -> Dict[str, float]:
    n = len(FEATURE_NAMES)
    shapley_values = {}
    factorials = [math.factorial(i) for i in range(n + 1)]

    for feature in FEATURE_NAMES:
        phi = 0.0
        other_features = [f for f in FEATURE_NAMES if f != feature]
        
        for r in range(len(other_features) + 1):
            subsets = list(itertools.combinations(other_features, r))
            weight = (factorials[r] * factorials[n - r - 1]) / factorials[n]
            
            for S in subsets:
                features_without = {}
                features_with = {}
                
                for f in FEATURE_NAMES:
                    if f in S:
                        features_without[f] = actual_features[f]
                        features_with[f] = actual_features[f]
                    elif f == feature:
                        features_without[f] = baseline_features[f]
                        features_with[f] = actual_features[f]
                    else:
                        features_without[f] = baseline_features[f]
                        features_with[f] = baseline_features[f]
                
                marginal = calculate_rebalance_utility(features_with) - calculate_rebalance_utility(features_without)
                phi += weight * marginal
                
        shapley_values[feature] = round(phi, 4)
        
    return shapley_values

def generate_shap_explanation(
    drift_pct: float,
    tax_savings_val: float,
    cash_drift_pct: float,
    est_tx_cost: float,
    portfolio_value: float,
    vix_level: float = 20.0
) -> Dict[str, Any]:
    normalized_tax = tax_savings_val / portfolio_value if portfolio_value > 0 else 0
    normalized_cost = est_tx_cost / portfolio_value if portfolio_value > 0 else 0
    normalized_vix = vix_level / 100.0

    actual = {
        "drift_magnitude": drift_pct,
        "tax_savings": normalized_tax,
        "cash_drift": cash_drift_pct,
        "transaction_cost": normalized_cost,
        "market_volatility": normalized_vix
    }

    baseline = {
        "drift_magnitude": 0.0,
        "tax_savings": 0.0,
        "cash_drift": 0.0,
        "transaction_cost": 0.0,
        "market_volatility": 0.15
    }

    shap_vals = compute_exact_shapley_values(actual, baseline)
    base_value = calculate_rebalance_utility(baseline)
    output_value = calculate_rebalance_utility(actual)
    
    return {
        "shap_values": shap_vals,
        "base_value": round(base_value, 4),
        "output_value": round(output_value, 4),
        "trigger_probability": round(1 / (1 + math.exp(-output_value)), 4)
    }
