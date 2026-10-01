"""Proportional fees per buy/sell notional, paid from portfolio wealth."""

import numpy as np
import pandas as pd


def validate_weights(weights, assets):
    if not isinstance(weights, pd.Series):
        raise ValueError("Optimizer must return a pandas Series indexed by ticker.")
    if weights.index.has_duplicates or set(weights.index) != set(assets):
        raise ValueError("Weight tickers must match return columns exactly.")
    aligned = weights.reindex(assets).to_numpy(dtype=float)
    if (
        not np.isfinite(aligned).all()
        or (aligned < 0).any()
        or not np.isclose(aligned.sum(), 1, atol=1e-10, rtol=0)
    ):
        raise ValueError("Weights must be finite, nonnegative and sum to one.")
    return aligned / aligned.sum()


def rebalance(holdings, cash, target, transaction_cost_rate):
    """Rebalance while paying transaction costs from portfolio wealth."""
    current = np.asarray(holdings, float)
    weights = np.asarray(target, float)
    rate = float(transaction_cost_rate)
    if (
        current.ndim != 1
        or current.shape != weights.shape
        or not np.isfinite(current).all()
        or (current < 0).any()
    ):
        raise ValueError("Invalid holdings.")
    if not np.isfinite(cash) or cash < 0 or not 0 <= rate < 1:
        raise ValueError("Cash must be nonnegative; fee rate must be in [0, 1).")
    if (
        not np.isfinite(weights).all()
        or (weights < 0).any()
        or not np.isclose(weights.sum(), 1, atol=1e-10, rtol=0)
    ):
        raise ValueError("Target must be long-only and sum to one.")
    weights = weights / weights.sum()
    wealth = float(current.sum() + cash)
    if wealth <= 0:
        raise ValueError("Portfolio has no positive wealth.")
    lower, upper = 0.0, wealth
    if rate == 0:
        after = wealth
    else:
        for _ in range(100):
            midpoint = (lower + upper) / 2
            if midpoint + rate * np.abs(weights * midpoint - current).sum() > wealth:
                upper = midpoint
            else:
                lower = midpoint
        after = (lower + upper) / 2
    new_holdings = weights * after
    trades = new_holdings - current
    traded = float(np.abs(trades).sum())
    fee = rate * traded
    if not np.isclose(new_holdings.sum() + fee, wealth, rtol=1e-11, atol=1e-10):
        raise ArithmeticError("Self-financing check failed.")
    return new_holdings, trades, fee, traded / wealth
