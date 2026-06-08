"""
WealthPilot AI - Portfolio Drift Detection Engine

Mathematical Formulations:

1. Absolute Drift:
   Measures the aggregate mismatch in allocations across the portfolio.
   D_abs = 0.5 * sum(|w_i - w_i*|)
   where w_i is the current weight of asset i and w_i* is the target weight.

2. Relative Drift (per asset i):
   D_rel_i = |w_i - w_i*| / w_i*

3. Portfolio Variance:
   sigma_p^2 = w^T * Sigma * w
   where w is the weight vector and Sigma is the covariance matrix of asset returns.

4. Tracking Error (Active Volatility):
   TE = sqrt((w - w*)^T * Sigma * (w - w*))
   measures the standard deviation of active returns relative to the target benchmark.

5. Risk Score:
   Standardized mapping representing the annualized portfolio volatility as a percentage.
   Risk Score = sigma_p * 100
"""

import numpy as np
from typing import Dict, List, Any, Optional, Tuple

# Default Volatilities (Annualised Std Dev) for seeded assets
DEFAULT_VOLATILITIES = {
    "SPY": 0.160,    # S&P 500 Equity
    "QQQ": 0.200,    # Nasdaq Equity
    "IWM": 0.220,    # Small-cap Equity
    "AGG": 0.050,    # Aggregate Bonds
    "BND": 0.052,    # Vanguard Bonds
    "GLD": 0.120,    # Gold Alternative
    "BIL": 0.005,    # Short-term T-Bills (Cash)
    "CASH": 0.000    # Pure Cash
}

# Default Correlation Matrix pairs R_ij
DEFAULT_CORRELATIONS = {
    ("SPY", "QQQ"): 0.90,
    ("SPY", "IWM"): 0.85,
    ("SPY", "AGG"): -0.10,
    ("SPY", "BND"): -0.10,
    ("SPY", "GLD"): 0.10,
    ("SPY", "BIL"): 0.00,
    ("SPY", "CASH"): 0.00,
    
    ("QQQ", "IWM"): 0.80,
    ("QQQ", "AGG"): -0.15,
    ("QQQ", "BND"): -0.15,
    ("QQQ", "GLD"): 0.08,
    ("QQQ", "BIL"): 0.00,
    ("QQQ", "CASH"): 0.00,
    
    ("IWM", "AGG"): -0.05,
    ("IWM", "BND"): -0.05,
    ("IWM", "GLD"): 0.12,
    ("IWM", "BIL"): 0.00,
    ("IWM", "CASH"): 0.00,
    
    ("AGG", "BND"): 0.95,
    ("AGG", "GLD"): 0.20,
    ("AGG", "BIL"): 0.00,
    ("AGG", "CASH"): 0.00,
    
    ("BND", "GLD"): 0.20,
    ("BND", "BIL"): 0.00,
    ("BND", "CASH"): 0.00,
    
    ("GLD", "BIL"): 0.00,
    ("GLD", "CASH"): 0.00,
    
    ("BIL", "CASH"): 0.00
}

class DriftDetectionEngine:
    def __init__(self, custom_cov: Optional[Dict[str, Dict[str, float]]] = None):
        """
        Initializes the drift engine.
        Accepts a custom covariance dictionary or constructs one using defaults.
        """
        if custom_cov:
            self.cov = custom_cov
        else:
            self.cov = {}
            # Auto-construct the covariance matrix based on default vols and correlations
            for asset1 in DEFAULT_VOLATILITIES:
                self.cov[asset1] = {}
                for asset2 in DEFAULT_VOLATILITIES:
                    if asset1 == asset2:
                        self.cov[asset1][asset2] = DEFAULT_VOLATILITIES[asset1] ** 2
                    else:
                        pair = (asset1, asset2) if (asset1, asset2) in DEFAULT_CORRELATIONS else (asset2, asset1)
                        corr = DEFAULT_CORRELATIONS.get(pair, 0.0)
                        self.cov[asset1][asset2] = corr * DEFAULT_VOLATILITIES[asset1] * DEFAULT_VOLATILITIES[asset2]

    def calculate_absolute_drift(self, current_weights: Dict[str, float], target_weights: Dict[str, float]) -> float:
        """
        D_abs = 0.5 * sum(|w_i - w_i*|)
        """
        all_symbols = set(current_weights.keys()).union(target_weights.keys())
        total_abs_diff = 0.0
        
        for symbol in all_symbols:
            w_curr = current_weights.get(symbol, 0.0)
            w_targ = target_weights.get(symbol, 0.0)
            total_abs_diff += abs(w_curr - w_targ)
            
        return total_abs_diff / 2.0

    def calculate_relative_drifts(self, current_weights: Dict[str, float], target_weights: Dict[str, float]) -> Dict[str, float]:
        """
        D_rel_i = |w_i - w_i*| / w_i*
        """
        relative_drifts = {}
        for symbol, w_targ in target_weights.items():
            if w_targ <= 0:
                relative_drifts[symbol] = 0.0
                continue
            w_curr = current_weights.get(symbol, 0.0)
            relative_drifts[symbol] = abs(w_curr - w_targ) / w_targ
            
        return relative_drifts

    def _get_active_covariance_matrix(self, symbols: List[str]) -> np.ndarray:
        """Helper to subset the covariance matrix for a specific set of symbols"""
        n = len(symbols)
        sigma = np.zeros((n, n))
        for i, s1 in enumerate(symbols):
            for j, s2 in enumerate(symbols):
                # Map CASH to BIL or defaults if missing
                s1_lookup = "BIL" if s1 == "CASH" else s1
                s2_lookup = "BIL" if s2 == "CASH" else s2
                sigma[i, j] = self.cov.get(s1_lookup, {}).get(s2_lookup, 0.0)
        return sigma

    def calculate_portfolio_variance(self, weights: Dict[str, float]) -> float:
        """
        sigma_p^2 = w^T * Sigma * w
        """
        symbols = list(weights.keys())
        w_vec = np.array([weights[sym] for sym in symbols])
        
        sigma = self._get_active_covariance_matrix(symbols)
        variance = np.dot(w_vec.T, np.dot(sigma, w_vec))
        return float(variance)

    def calculate_tracking_error(self, current_weights: Dict[str, float], target_weights: Dict[str, float]) -> float:
        """
        TE = sqrt((w - w*)^T * Sigma * (w - w*))
        """
        symbols = list(set(current_weights.keys()).union(target_weights.keys()))
        
        # Calculate active weight vector (current - target)
        active_w = np.array([current_weights.get(sym, 0.0) - target_weights.get(sym, 0.0) for sym in symbols])
        
        sigma = self._get_active_covariance_matrix(symbols)
        te_variance = np.dot(active_w.T, np.dot(sigma, active_w))
        
        # Return tracking error (active standard deviation), ensuring float safety against rounding noise
        return float(np.sqrt(max(0.0, te_variance)))

    def calculate_risk_score(self, weights: Dict[str, float]) -> float:
        """
        Risk Score = sigma_p * 100 (annualized volatility percentage)
        """
        variance = self.calculate_portfolio_variance(weights)
        volatility = np.sqrt(max(0.0, variance))
        return round(float(volatility * 100), 2)

    def check_rebalance_triggers(
        self,
        current_weights: Dict[str, float],
        target_weights: Dict[str, float],
        previous_risk_score: Optional[float] = None,
        drift_threshold: float = 0.05,
        te_limit: float = 0.02,
        risk_increase_limit: float = 2.0
    ) -> Dict[str, Any]:
        """
        Evaluates trigger limits and flags if rebalancing is required.
        """
        abs_drift = self.calculate_absolute_drift(current_weights, target_weights)
        relative_drifts = self.calculate_relative_drifts(current_weights, target_weights)
        te = self.calculate_tracking_error(current_weights, target_weights)
        current_risk_score = self.calculate_risk_score(current_weights)
        
        drift_trigger = abs_drift >= drift_threshold
        te_trigger = te >= te_limit
        
        risk_trigger = False
        risk_diff = 0.0
        if previous_risk_score is not None:
            risk_diff = current_risk_score - previous_risk_score
            risk_trigger = risk_diff >= risk_increase_limit
            
        rebalance_required = drift_trigger or te_trigger or risk_trigger
        
        reasons = []
        if drift_trigger:
            reasons.append(f"Absolute drift index ({abs_drift:.2%}) matches/exceeds trigger limit ({drift_threshold:.2%})")
        if te_trigger:
            reasons.append(f"Active tracking error ({te:.2%}) matches/exceeds volatility cap ({te_limit:.2%})")
        if risk_trigger:
            reasons.append(f"Risk score increase (+{risk_diff:.2f}) matches/exceeds deviation allowance (+{risk_increase_limit:.2f})")
            
        return {
            "rebalance_required": rebalance_required,
            "absolute_drift": round(abs_drift, 5),
            "relative_drifts": {k: round(v, 5) for k, v in relative_drifts.items()},
            "tracking_error": round(te, 5),
            "risk_score": current_risk_score,
            "triggers": {
                "drift_triggered": drift_trigger,
                "tracking_error_triggered": te_trigger,
                "risk_triggered": risk_trigger
            },
            "reasons": reasons
        }
