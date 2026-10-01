"""Proportional fees per buy/sell notional, paid from portfolio wealth."""
import numpy as np


def validate_weights(weights, assets):
    import pandas as pd
    if not isinstance(weights, pd.Series):
        raise ValueError("Optimizer must return a pandas Series indexed by ticker.")
    if weights.index.has_duplicates or set(weights.index) != set(assets):
        raise ValueError("Weight tickers must match return columns exactly.")
    w = weights.reindex(assets).to_numpy(dtype=float)
    if not np.isfinite(w).all() or (w < 0).any() or not np.isclose(w.sum(), 1, atol=1e-10, rtol=0):
        raise ValueError("Weights must be finite, nonnegative and sum to one.")
    return w / w.sum()


def rebalance(holdings, cash, target, transaction_cost_rate):
    """Solve V_after + c*sum(abs(w*V_after - holdings)) = V_before.

    Holdings are currency amounts, not shares. Initial deployment is charged.
    Target is long-only and fully invested. No tax/slippage outside supplied c.
    """
    h, w = np.asarray(holdings, float), np.asarray(target, float)
    c = float(transaction_cost_rate)
    if h.ndim != 1 or h.shape != w.shape or not np.isfinite(h).all() or (h < 0).any():
        raise ValueError("Invalid holdings.")
    if not np.isfinite(cash) or cash < 0 or not 0 <= c < 1:
        raise ValueError("Cash must be nonnegative; fee rate must be in [0, 1).")
    if not np.isfinite(w).all() or (w < 0).any() or not np.isclose(w.sum(), 1, atol=1e-10, rtol=0):
        raise ValueError("Target must be long-only and sum to one.")
    w = w / w.sum()
    wealth = float(h.sum() + cash)
    if wealth <= 0:
        raise ValueError("Portfolio has no positive wealth.")
    lo, hi = 0., wealth
    if c == 0:
        after = wealth
    else:
        for _ in range(100):
            mid = (lo + hi) / 2
            if mid + c * np.abs(w * mid - h).sum() > wealth:
                hi = mid
            else:
                lo = mid
        after = (lo + hi) / 2
    new_holdings = w * after
    trades = new_holdings - h
    traded = float(np.abs(trades).sum())
    fee = c * traded
    if not np.isclose(new_holdings.sum() + fee, wealth, rtol=1e-11, atol=1e-10):
        raise ArithmeticError("Self-financing check failed.")
    return new_holdings, trades, fee, traded / wealth
