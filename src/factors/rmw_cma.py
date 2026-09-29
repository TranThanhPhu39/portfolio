"""Construction of profitability (RMW) and investment (CMA) factors."""

from __future__ import annotations

import pandas as pd

from .portfolio_sort import portfolio_sort
from .smb_hml import portfolio_returns


def _factor_from_sort(
    returns: pd.DataFrame,
    size: pd.Series,
    characteristic: pd.Series,
    labels: tuple[str, str, str, str, str, str],
    high_minus_low: bool,
    weights: pd.Series | pd.DataFrame | None,
) -> pd.Series:
    groups = portfolio_sort(size, characteristic, labels=labels)
    portfolios = portfolio_returns(returns, groups, weights, required_groups=labels)
    sl, _, sh, bl, _, bh = labels
    high = portfolios[[sh, bh]].mean(axis=1)
    low = portfolios[[sl, bl]].mean(axis=1)
    return high - low if high_minus_low else low - high


def compute_rmw(
    returns: pd.DataFrame,
    size: pd.Series,
    operating_profitability: pd.Series,
    weights: pd.Series | pd.DataFrame | None = None,
) -> pd.Series:
    """Robust Minus Weak profitability factor."""
    factor = _factor_from_sort(
        returns, size, operating_profitability,
        ("SW", "SN", "SR", "BW", "BN", "BR"), True, weights,
    )
    return factor.rename("RMW")


def compute_cma(
    returns: pd.DataFrame,
    size: pd.Series,
    investment: pd.Series,
    weights: pd.Series | pd.DataFrame | None = None,
) -> pd.Series:
    """Conservative Minus Aggressive investment factor."""
    factor = _factor_from_sort(
        returns, size, investment,
        ("SC", "SN", "SA", "BC", "BN", "BA"), False, weights,
    )
    return factor.rename("CMA")
