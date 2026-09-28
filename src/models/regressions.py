"""Time-series factor regressions for portfolio returns."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.regression.linear_model import RegressionResultsWrapper


def _normalize_date_index(index: pd.Index, source_name: str) -> pd.DatetimeIndex:
    if isinstance(index, pd.MultiIndex):
        raise TypeError(f"{source_name} must have a single-level date index")
    if isinstance(index, pd.PeriodIndex):
        normalized = index.to_timestamp()
    elif pd.api.types.is_numeric_dtype(index.dtype):
        raise TypeError(f"{source_name} index must contain dates, not numeric labels")
    else:
        try:
            normalized = pd.DatetimeIndex(pd.to_datetime(index, errors="raise"))
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError(f"{source_name} index must contain parseable dates") from exc

    if normalized.hasnans:
        raise ValueError(f"{source_name} index contains missing dates")
    if normalized.has_duplicates:
        raise ValueError(f"{source_name} index contains duplicate dates")
    if normalized.tz is not None:
        normalized = normalized.tz_convert("UTC").tz_localize(None)
    return normalized


def run_factor_regression(
    portfolio_returns: pd.Series,
    factors: pd.DataFrame,
    factor_cols: Sequence[str],
    *,
    rf_col: str = "RF",
) -> RegressionResultsWrapper:
    """Regress one portfolio's excess return on selected factor columns.

    ``portfolio_returns`` contains raw decimal returns. The function subtracts
    the date-aligned risk-free return from ``rf_col`` before fitting OLS. The
    returned statsmodels result exposes ``summary()``, ``params``, ``tvalues``,
    ``rsquared`` and ``nobs``. HAC covariance is added in the later diagnostics
    step; this function fits the baseline OLS model.
    """
    if not isinstance(portfolio_returns, pd.Series):
        raise TypeError("portfolio_returns must be a pandas Series")
    if not isinstance(factors, pd.DataFrame):
        raise TypeError("factors must be a pandas DataFrame")
    if not factors.columns.is_unique:
        raise ValueError("factors must not contain duplicate column names")
    if isinstance(factor_cols, str):
        raise TypeError("factor_cols must be a sequence of column names")

    selected_cols = list(factor_cols)
    if not selected_cols:
        raise ValueError("factor_cols must contain at least one factor")
    if any(not isinstance(column, str) or not column.strip() for column in selected_cols):
        raise ValueError("factor_cols entries must be non-empty strings")
    if len(set(selected_cols)) != len(selected_cols):
        raise ValueError("factor_cols must not contain duplicate names")
    if rf_col in selected_cols:
        raise ValueError(f"{rf_col!r} is used to form excess returns, not as a regressor")
    if "const" in selected_cols:
        raise ValueError("'const' is reserved for the regression intercept")

    missing = [column for column in [rf_col, *selected_cols] if column not in factors.columns]
    if missing:
        raise KeyError(f"Missing required factor columns: {missing}")

    returns = pd.to_numeric(portfolio_returns.copy(), errors="raise")
    returns.index = _normalize_date_index(returns.index, "portfolio_returns")
    returns.name = "__portfolio_return"

    factor_data = factors.loc[:, [rf_col, *selected_cols]].copy()
    factor_data.index = _normalize_date_index(factor_data.index, "factors")
    for column in factor_data.columns:
        factor_data[column] = pd.to_numeric(factor_data[column], errors="raise")

    aligned = pd.concat([returns, factor_data], axis=1, join="inner").sort_index().dropna()
    if aligned.empty:
        raise ValueError("No complete overlapping dates between returns and factors")

    values = aligned.to_numpy(dtype=np.float64)
    if not np.isfinite(values).all():
        raise ValueError("returns and factors must contain only finite numeric values")
    if len(aligned) <= len(selected_cols) + 1:
        raise ValueError(
            "Insufficient complete observations for the selected factors and intercept"
        )

    excess_returns = aligned["__portfolio_return"] - aligned[rf_col]
    excess_returns.name = portfolio_returns.name or "portfolio_excess_return"
    design = sm.add_constant(aligned.loc[:, selected_cols], has_constant="add")
    if np.linalg.matrix_rank(design.to_numpy(dtype=np.float64)) < design.shape[1]:
        raise ValueError("The selected factors are linearly dependent on the sample")

    return sm.OLS(excess_returns, design, missing="raise").fit()
