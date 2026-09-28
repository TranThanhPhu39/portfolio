"""Finite-sample Gibbons-Ross-Shanken tests for linear factor models."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats

from .regressions import _normalize_date_index, run_factor_regression


@dataclass(frozen=True)
class GRSResult:
    """GRS joint-alpha test result and its fitted intercepts."""

    statistic: float
    p_value: float
    numerator_df: int
    denominator_df: int
    observations: int
    n_portfolios: int
    n_factors: int
    factor_sharpe_squared: float
    alphas: pd.Series


def grs_test(
    portfolio_returns: pd.DataFrame,
    factors: pd.DataFrame,
    factor_cols: Sequence[str],
    *,
    rf_col: str = "RF",
) -> GRSResult:
    """Test whether all portfolio intercepts are jointly zero.

    ``portfolio_returns`` contains raw decimal returns. RF is subtracted from
    every portfolio before fitting its time-series regression. The finite-sample
    F statistic uses the unbiased residual covariance with divisor ``T-K-1``
    and the unbiased factor covariance with divisor ``T-1``.
    """
    if not isinstance(portfolio_returns, pd.DataFrame):
        raise TypeError("portfolio_returns must be a pandas DataFrame")
    if not isinstance(factors, pd.DataFrame):
        raise TypeError("factors must be a pandas DataFrame")
    if portfolio_returns.empty or portfolio_returns.shape[1] == 0:
        raise ValueError("portfolio_returns must contain at least one portfolio")
    if not portfolio_returns.columns.is_unique:
        raise ValueError("portfolio_returns must not have duplicate column names")
    if any(
        not isinstance(name, str) or not name.strip()
        for name in portfolio_returns.columns
    ):
        raise ValueError("portfolio_returns column names must be non-empty strings")
    if not isinstance(rf_col, str) or not rf_col.strip():
        raise ValueError("rf_col must be a non-empty string")
    if not factors.columns.is_unique:
        raise ValueError("factors must not have duplicate column names")
    if isinstance(factor_cols, str):
        raise TypeError("factor_cols must be a sequence of factor names")

    selected_factors = list(factor_cols)
    if not selected_factors:
        raise ValueError("factor_cols must contain at least one factor")
    if any(not isinstance(name, str) or not name.strip() for name in selected_factors):
        raise ValueError("factor_cols entries must be non-empty strings")
    if len(set(selected_factors)) != len(selected_factors):
        raise ValueError("factor_cols must not contain duplicate names")
    if rf_col in selected_factors:
        raise ValueError(f"{rf_col!r} forms excess returns and cannot be an RHS factor")

    required_factors = [rf_col, *selected_factors]
    missing_factors = [name for name in required_factors if name not in factors.columns]
    if missing_factors:
        raise KeyError(f"Missing required factor columns: {missing_factors}")

    returns = portfolio_returns.copy()
    returns.index = _normalize_date_index(returns.index, "portfolio_returns")
    for column in returns.columns:
        returns[column] = pd.to_numeric(returns[column], errors="raise")

    factor_data = factors.loc[:, required_factors].copy()
    factor_data.index = _normalize_date_index(factor_data.index, "factors")
    for column in factor_data.columns:
        factor_data[column] = pd.to_numeric(factor_data[column], errors="raise")

    n_portfolios = returns.shape[1]
    left = returns.copy()
    left.columns = [f"__lhs_{position}" for position in range(n_portfolios)]
    right = factor_data.copy()
    right.columns = [f"__factor_{position}" for position in range(len(required_factors))]
    aligned = pd.concat([left, right], axis=1, join="inner").sort_index().dropna()
    if aligned.empty:
        raise ValueError("No complete overlapping dates between returns and factors")

    values = aligned.to_numpy(dtype=np.float64)
    if not np.isfinite(values).all():
        raise ValueError("returns and factors must contain only finite numeric values")

    observations = len(aligned)
    n_factors = len(selected_factors)
    if observations <= n_portfolios + n_factors:
        raise ValueError(
            "Insufficient observations for GRS: require T > N + K "
            f"(got T={observations}, N={n_portfolios}, K={n_factors})"
        )
    residual_df = observations - n_factors - 1
    denominator_df = observations - n_portfolios - n_factors

    aligned_returns = aligned.iloc[:, :n_portfolios].copy()
    aligned_returns.columns = returns.columns
    aligned_factors = aligned.iloc[:, n_portfolios:].copy()
    aligned_factors.columns = required_factors

    alpha_values: list[float] = []
    residual_values: list[np.ndarray] = []
    for column in aligned_returns.columns:
        result = run_factor_regression(
            aligned_returns[column],
            aligned_factors,
            selected_factors,
            rf_col=rf_col,
        )
        if int(result.nobs) != observations:
            raise RuntimeError(
                f"Portfolio {column!r} used {int(result.nobs)} observations; "
                f"expected {observations}"
            )
        if not result.resid.index.equals(aligned.index):
            raise RuntimeError(f"Portfolio {column!r} residual dates do not align")
        alpha_values.append(float(result.params["const"]))
        residual_values.append(result.resid.to_numpy(dtype=np.float64))

    alpha = np.asarray(alpha_values, dtype=np.float64)
    residuals = np.column_stack(residual_values)
    factor_matrix = aligned_factors.loc[:, selected_factors].to_numpy(dtype=np.float64)
    factor_mean = factor_matrix.mean(axis=0)
    centered_factors = factor_matrix - factor_mean

    residual_covariance = residuals.T @ residuals / residual_df
    factor_covariance = centered_factors.T @ centered_factors / (observations - 1)
    try:
        residual_cholesky = np.linalg.cholesky(residual_covariance)
        factor_cholesky = np.linalg.cholesky(factor_covariance)
    except np.linalg.LinAlgError as exc:
        raise ValueError(
            "GRS requires positive-definite residual and factor covariance matrices"
        ) from exc

    residual_solution = np.linalg.solve(
        residual_cholesky.T,
        np.linalg.solve(residual_cholesky, alpha),
    )
    factor_solution = np.linalg.solve(
        factor_cholesky.T,
        np.linalg.solve(factor_cholesky, factor_mean),
    )
    alpha_quadratic = float(alpha @ residual_solution)
    factor_sharpe_squared = float(factor_mean @ factor_solution)
    if not np.isfinite(factor_sharpe_squared) or factor_sharpe_squared < -1e-12:
        raise ArithmeticError("Invalid factor Sharpe-ratio quadratic form in GRS")
    factor_sharpe_squared = max(factor_sharpe_squared, 0.0)
    grs_denominator = 1.0 + factor_sharpe_squared
    if not np.isfinite(alpha_quadratic) or alpha_quadratic < -1e-12:
        raise ArithmeticError("Invalid quadratic form for the joint alpha vector")
    if not np.isfinite(grs_denominator) or grs_denominator <= 0.0:
        raise ArithmeticError("Invalid factor Sharpe-ratio denominator in GRS")

    statistic = (
        observations
        / n_portfolios
        * denominator_df
        / residual_df
        * max(alpha_quadratic, 0.0)
        / grs_denominator
    )
    p_value = float(stats.f.sf(statistic, n_portfolios, denominator_df))
    if not np.isfinite(statistic) or statistic < 0.0:
        raise ArithmeticError("GRS statistic must be finite and non-negative")
    if not np.isfinite(p_value) or not 0.0 <= p_value <= 1.0:
        raise ArithmeticError("GRS p-value must be finite and between 0 and 1")

    alpha_series = pd.Series(
        alpha,
        index=aligned_returns.columns,
        name="alpha",
    )
    return GRSResult(
        statistic=float(statistic),
        p_value=p_value,
        numerator_df=n_portfolios,
        denominator_df=denominator_df,
        observations=observations,
        n_portfolios=n_portfolios,
        n_factors=n_factors,
        factor_sharpe_squared=factor_sharpe_squared,
        alphas=alpha_series,
    )
