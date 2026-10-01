"""Long-only fully invested portfolios. Inputs are monthly simple returns."""

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from src.backtest.walk_forward import validate_returns


def estimate(history, ridge=1e-8):
    validate_returns(history)
    if len(history) < 2 or not np.isfinite(ridge) or ridge < 0:
        raise ValueError("Need at least two months and finite nonnegative ridge")
    mu = history.mean()
    sample = history.cov(ddof=1)
    covariance = sample + np.eye(len(mu)) * ridge
    return mu, covariance


def validate_inputs(mu, covariance):
    if not isinstance(mu, pd.Series) or not isinstance(covariance, pd.DataFrame):
        raise ValueError("Labeled Series and DataFrame required")
    if (
        mu.empty
        or mu.index.has_duplicates
        or covariance.index.has_duplicates
        or covariance.columns.has_duplicates
    ):
        raise ValueError("Empty/duplicate asset labels")
    if set(mu.index) != set(covariance.index) or set(mu.index) != set(covariance.columns):
        raise ValueError("Covariance labels must match expected returns")
    mean = mu.to_numpy(float)
    cov = covariance.loc[mu.index, mu.index].to_numpy(float)
    if (
        not np.isfinite(mean).all()
        or not np.isfinite(cov).all()
        or not np.allclose(cov, cov.T, atol=1e-12)
    ):
        raise ValueError("Nonfinite or asymmetric inputs")
    if np.linalg.eigvalsh(cov).min() <= 0:
        raise ValueError("Positive definite covariance required; choose and disclose ridge")
    return mean, cov


def solve(mu, covariance, objective="min_variance", rf=0.0, target=None):
    mean, cov = validate_inputs(mu, covariance)
    if not np.isfinite(rf):
        raise ValueError("RF must be a finite monthly return")
    n_assets = len(mean)
    scale = np.max(np.diag(cov))
    scaled_cov = cov / scale
    constraints = [
        {
            "type": "eq",
            "fun": lambda weights: weights.sum() - 1,
            "jac": lambda weights: np.ones(n_assets),
        }
    ]
    if target is not None:
        if (
            not np.isfinite(target)
            or target < mean.min() - 1e-12
            or target > mean.max() + 1e-12
        ):
            raise ValueError("Infeasible target return")
        if np.ptp(mean) > 1e-12:
            constraints.append(
                {
                    "type": "eq",
                    "fun": lambda weights: weights @ mean - target,
                    "jac": lambda weights: mean,
                }
            )
    if objective == "min_variance":
        objective_function = lambda weights: weights @ scaled_cov @ weights
        gradient = lambda weights: 2 * scaled_cov @ weights
        starts = [np.full(n_assets, 1 / n_assets)]
    elif objective == "max_sharpe" and target is None:
        excess = mean - rf
        if excess.max() <= 0:
            best = np.argmax(excess / np.sqrt(np.diag(cov)))
            return pd.Series(np.eye(n_assets)[best], index=mu.index)
        scaled_excess = excess / excess.max()
        seed = np.eye(n_assets)[int(np.argmax(scaled_excess))]
        qp = minimize(
            lambda values: values @ scaled_cov @ values,
            seed,
            jac=lambda values: 2 * scaled_cov @ values,
            method="SLSQP",
            bounds=[(0.0, None)] * n_assets,
            constraints=[
                {
                    "type": "eq",
                    "fun": lambda values: values @ scaled_excess - 1,
                    "jac": lambda values: scaled_excess,
                }
            ],
            options={"ftol": 1e-12, "maxiter": 4000},
        )
        if (
            qp.success
            and np.isfinite(qp.x).all()
            and qp.x.min() >= -1e-10
            and abs(qp.x @ scaled_excess - 1) < 1e-8
        ):
            values = np.maximum(qp.x, 0)
            return pd.Series(values / values.sum(), index=mu.index)
        objective_function = lambda weights: -(weights @ excess) / np.sqrt(
            weights @ cov @ weights
        )
        gradient = lambda weights: (
            -excess / np.sqrt(weights @ cov @ weights)
            + (weights @ excess)
            * (cov @ weights)
            / (weights @ cov @ weights) ** 1.5
        )
        starts = [
            np.full(n_assets, 1 / n_assets),
            np.eye(n_assets)[np.argmax(excess / np.sqrt(np.diag(cov)))],
        ]
    else:
        raise ValueError("Unknown objective or target incompatible with Sharpe")
    candidates = []
    for initial in starts:
        result = minimize(
            objective_function,
            initial,
            jac=gradient,
            method="SLSQP",
            bounds=[(0.0, 1.0)] * n_assets,
            constraints=constraints,
            options={"ftol": 1e-12, "maxiter": 2000},
        )
        weights = result.x
        if (
            result.success
            and np.isfinite(weights).all()
            and abs(weights.sum() - 1) < 1e-8
            and weights.min() >= -1e-10
        ):
            weights = np.maximum(weights, 0)
            weights /= weights.sum()
            if target is None or abs(weights @ mean - target) < 1e-8:
                candidates.append(weights)
    if not candidates:
        raise RuntimeError("Optimizer failed; no equal-weight fallback")
    return pd.Series(min(candidates, key=objective_function), index=mu.index)


def portfolio_stats(weights, mu, covariance, rf):
    mean, cov = validate_inputs(mu, covariance)
    aligned_weights = weights.reindex(mu.index).to_numpy(float)
    if (
        not np.isfinite(aligned_weights).all()
        or aligned_weights.min() < 0
        or not np.isclose(aligned_weights.sum(), 1)
    ):
        raise ValueError("Invalid portfolio weights")
    expected_return = aligned_weights @ mean
    volatility = np.sqrt(aligned_weights @ cov @ aligned_weights)
    return {
        "expected_return_monthly": float(expected_return),
        "volatility_monthly": float(volatility),
        "sharpe_annualized": float(np.sqrt(12) * (expected_return - rf) / volatility),
    }


def frontier(mu, covariance, points=30):
    if not isinstance(points, int) or points < 2:
        raise ValueError("At least two frontier points required")
    minimum = solve(mu, covariance)
    targets = np.linspace(float(minimum @ mu), float(mu.max()), points)
    rows = []
    weights = []
    for target in targets:
        solution = solve(mu, covariance, target=float(target))
        rows.append(portfolio_stats(solution, mu, covariance, 0.0))
        weights.append(solution)
    return pd.DataFrame(rows), pd.DataFrame(weights)


def optimizer_factory(kind, rf_history, ridge=1e-8):
    """Use the mean RF from the same training window; never future RF."""

    def optimizer(history):
        mu, covariance = estimate(history, ridge)
        rf = rf_history.reindex(history.index)
        if not np.isfinite(rf.to_numpy(float)).all():
            raise ValueError("RF missing in training window")
        return solve(mu, covariance, kind, rf=float(rf.mean()))

    return optimizer
