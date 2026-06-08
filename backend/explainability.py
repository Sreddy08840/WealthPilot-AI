import math
import itertools
from typing import Dict, List, Any

# Feature Names
FEATURE_NAMES = [
    "drift_magnitude",      # Aggregate drift of assets
    "tax_savings",          # Capital losses to harvest (tax shield)
    "cash_drift",           # Cash deviation from target allocation
    "transaction_cost",      # Estimated trading commissions & slippage
    "market_volatility"     # VIX level / market volatility factor
]

def calculate_rebalance_utility(features: Dict[str, float]) -> float:
    """
    Characteristic utility function v(S) for a given state of features.
    Returns a score representing the rebalancing urgency/utility (usually between -0.5 and 1.5).
    """
    # Feature weights (coefficients)
    w_drift = 8.5          # High drift -> high utility
    w_tax = 15.0           # Tax savings -> increases utility
    w_cash = 3.0           # Cash drift -> increases utility
    w_cost = -12.0         # High transaction cost -> reduces utility
    w_vol = 1.5            # Volatility -> adds minor urgency

    # Raw features
    drift = features.get("drift_magnitude", 0.0)
    tax = features.get("tax_savings", 0.0)
    cash = features.get("cash_drift", 0.0)
    cost = features.get("transaction_cost", 0.0)
    vol = features.get("market_volatility", 0.15) # Default 15% VIX

    # Calculate utility
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
    """
    Computes exact Shapley values for the rebalancing utility function.
    Uses the game-theoretic formulation to evaluate marginal contributions.
    """
    n = len(FEATURE_NAMES)
    shapley_values = {}
    
    # Pre-calculate factorials for weighting
    factorials = [math.factorial(i) for i in range(n + 1)]

    # Compute Shapley value for each feature
    for feature in FEATURE_NAMES:
        phi = 0.0
        # The set of other features
        other_features = [f for f in FEATURE_NAMES if f != feature]
        
        # Iterate over all possible subsets of other features
        for r in range(len(other_features) + 1):
            subsets = list(itertools.combinations(other_features, r))
            
            # Weight for a subset S of size r
            # Weight = |S|! * (n - |S| - 1)! / n!
            weight = (factorials[r] * factorials[n - r - 1]) / factorials[n]
            
            for S in subsets:
                # Construct feature values for S (active features have actual values, others have baseline values)
                features_without = {}
                features_with = {}
                
                for f in FEATURE_NAMES:
                    if f in S:
                        # Feature in subset gets actual value
                        features_without[f] = actual_features[f]
                        features_with[f] = actual_features[f]
                    elif f == feature:
                        # The feature being analyzed gets baseline for 'without' and actual for 'with'
                        features_without[f] = baseline_features[f]
                        features_with[f] = actual_features[f]
                    else:
                        # Features not in subset get baseline value
                        features_without[f] = baseline_features[f]
                        features_with[f] = baseline_features[f]
                
                # Marginal contribution: v(S U {i}) - v(S)
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
    """
    Convenience wrapper to compute SHAP values for a specific portfolio.
    """
    # Normalize features relative to portfolio size
    normalized_tax = tax_savings_val / portfolio_value if portfolio_value > 0 else 0
    normalized_cost = est_tx_cost / portfolio_value if portfolio_value > 0 else 0
    normalized_vix = vix_level / 100.0 # e.g. VIX 20 = 0.20

    actual = {
        "drift_magnitude": drift_pct,
        "tax_savings": normalized_tax,
        "cash_drift": cash_drift_pct,
        "transaction_cost": normalized_cost,
        "market_volatility": normalized_vix
    }

    # Baseline features represent an ideal, balanced portfolio:
    # 0 drift, 0 tax savings, 0 cash drift, 0 transaction costs, and standard 15% VIX volatility.
    baseline = {
        "drift_magnitude": 0.0,
        "tax_savings": 0.0,
        "cash_drift": 0.0,
        "transaction_cost": 0.0,
        "market_volatility": 0.15
    }

    shap_vals = compute_exact_shapley_values(actual, baseline)
    
    # Calculate base value (utility at baseline)
    base_value = calculate_rebalance_utility(baseline)
    # Calculate final output value (utility at actual)
    output_value = calculate_rebalance_utility(actual)
    
    return {
        "shap_values": shap_vals,
        "base_value": round(base_value, 4),
        "output_value": round(output_value, 4),
        "trigger_probability": round(1 / (1 + math.exp(-output_value)), 4) # Sigmoid mapping to probability
    }
