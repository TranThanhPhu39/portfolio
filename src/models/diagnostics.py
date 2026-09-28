"""Inference and collinearity diagnostics for linear factor regressions."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from numbers import Integral

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.regression.linear_model import RegressionResultsWrapper
from statsmodels.stats.outliers_influence import variance_inflation_factor

from .regressions import _normalize_date_index, run_factor_regression


@dataclass(frozen=True)
class HACRegressionResult:
    """Baseline OLS and the same model with HAC covariance inference."""

    ols: RegressionResultsWrapper
    hac: RegressionResultsWrapper
    maxlags: int
    kernel: str
    use_correction: bool
    use_t: bool


def run_hac_regression(
    portfolio_returns: pd.Series,
    factors: pd.DataFrame,
    factor_cols: Sequence[str],
    *,
    maxlags: int,
    rf_col: str = "RF",
    kernel: str = "bartlett",
    use_correction: bool = True,
    use_t: bool = False,
) -> HACRegressionResult:
    """Fit the Step 2 OLS model and attach Newey-West HAC inference.

    HAC changes the covariance estimator and inferential statistics, not the
    OLS coefficient estimates. With ``use_t=False``, statsmodels reports
    asymptotic-normal p-values; the corresponding robust statistic is labelled
    a z-statistic in generated outputs.
    """
    if isinstance(maxlags, bool) or not isinstance(maxlags, Integral):
        raise TypeError("maxlags must be a non-negative integer")
    if maxlags < 0:
        raise ValueError("maxlags must be non-negative")
    if kernel not in {"bartlett", "uniform"}:
        raise ValueError("kernel must be 'bartlett' or 'uniform'")
    if not isinstance(use_correction, bool):
        raise TypeError("use_correction must be a bool")
    if not isinstance(use_t, bool):
        raise TypeError("use_t must be a bool")

    ols = run_factor_regression(
        portfolio_returns,
        factors,
        factor_cols,
        rf_col=rf_col,
    )
    if maxlags >= int(ols.nobs):
        raise ValueError(
            f"maxlags must be smaller than nobs (got {maxlags} for nobs={int(ols.nobs)})"
        )

    hac = ols.get_robustcov_results(
        cov_type="HAC",
        maxlags=int(maxlags),
        kernel=kernel,
        use_correction=use_correction,
        use_t=use_t,
    )
    if not np.allclose(
        np.asarray(ols.params, dtype=np.float64),
        np.asarray(hac.params, dtype=np.float64),
        rtol=0.0,
        atol=1e-12,
    ):
        raise RuntimeError("HAC covariance changed the OLS coefficient estimates")
    if not np.isfinite(np.asarray(hac.bse, dtype=np.float64)).all():
        raise ArithmeticError("HAC standard errors contain non-finite values")
    if (np.asarray(hac.bse, dtype=np.float64) <= 0.0).any():
        raise ArithmeticError("HAC standard errors must be positive")
    if not np.isfinite(np.asarray(hac.pvalues, dtype=np.float64)).all():
        raise ArithmeticError("HAC p-values contain non-finite values")
    if ((np.asarray(hac.pvalues) < 0.0) | (np.asarray(hac.pvalues) > 1.0)).any():
        raise ArithmeticError("HAC p-values must be between 0 and 1")

    return HACRegressionResult(
        ols=ols,
        hac=hac,
        maxlags=int(maxlags),
        kernel=kernel,
        use_correction=use_correction,
        use_t=use_t,
    )


def calculate_vif(
    factors: pd.DataFrame,
    factor_cols: Sequence[str],
) -> pd.DataFrame:
    """Calculate VIF for each selected RHS factor, excluding the intercept."""
    if not isinstance(factors, pd.DataFrame):
        raise TypeError("factors must be a pandas DataFrame")
    if not factors.columns.is_unique:
        raise ValueError("factors must not contain duplicate column names")
    if isinstance(factor_cols, str):
        raise TypeError("factor_cols must be a sequence of factor names")

    selected = list(factor_cols)
    if not selected:
        raise ValueError("factor_cols must contain at least one factor")
    if any(not isinstance(name, str) or not name.strip() for name in selected):
        raise ValueError("factor_cols entries must be non-empty strings")
    if len(set(selected)) != len(selected):
        raise ValueError("factor_cols must not contain duplicate names")
    missing = [name for name in selected if name not in factors.columns]
    if missing:
        raise KeyError(f"Missing factor columns for VIF: {missing}")

    sample = factors.loc[:, selected].copy()
    sample.index = _normalize_date_index(sample.index, "factors")
    for column in selected:
        sample[column] = pd.to_numeric(sample[column], errors="raise")
    sample = sample.sort_index().dropna()
    values = sample.to_numpy(dtype=np.float64)
    if sample.empty:
        raise ValueError("No complete observations available for VIF")
    if not np.isfinite(values).all():
        raise ValueError("VIF inputs contain non-finite values")
    if len(sample) <= len(selected) + 1:
        raise ValueError("Insufficient observations for the VIF auxiliary regressions")

    design = sm.add_constant(sample, has_constant="add").to_numpy(dtype=np.float64)

    rows = []
    for position, name in enumerate(selected, start=1):
        with np.errstate(divide="ignore", invalid="ignore"):
            vif = float(variance_inflation_factor(design, position))
        if np.isnan(vif) or vif < 1.0 - 1e-10:
            raise ArithmeticError(f"Invalid VIF for factor {name!r}: {vif}")
        rows.append({"factor": name, "vif": vif, "observations": len(sample)})
    return pd.DataFrame(rows)
