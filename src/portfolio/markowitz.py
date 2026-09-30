"""Long-only fully invested portfolios. Inputs are MONTHLY simple returns."""
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from src.backtest.walk_forward import validate_returns


def estimate(history, ridge=1e-8):
    validate_returns(history)
    if len(history) < 2 or not np.isfinite(ridge) or ridge < 0:
        raise ValueError('Need at least two months and finite nonnegative ridge')
    mu = history.mean()
    sample = history.cov(ddof=1)
    covariance = sample + np.eye(len(mu)) * ridge
    return mu, covariance


def validate_inputs(mu, covariance):
    if not isinstance(mu, pd.Series) or not isinstance(covariance, pd.DataFrame):
        raise ValueError('Labeled Series and DataFrame required')
    if mu.empty or mu.index.has_duplicates or covariance.index.has_duplicates or covariance.columns.has_duplicates:
        raise ValueError('Empty/duplicate asset labels')
    if set(mu.index) != set(covariance.index) or set(mu.index) != set(covariance.columns):
        raise ValueError('Covariance labels must match expected returns')
    m = mu.to_numpy(float)
    c = covariance.loc[mu.index, mu.index].to_numpy(float)
    if not np.isfinite(m).all() or not np.isfinite(c).all() or not np.allclose(c, c.T, atol=1e-12):
        raise ValueError('Nonfinite or asymmetric inputs')
    if np.linalg.eigvalsh(c).min() <= 0:
        raise ValueError('Positive definite covariance required; choose and disclose ridge')
    return m, c


def solve(mu, covariance, objective='min_variance', rf=0., target=None):
    m, c = validate_inputs(mu, covariance)
    if not np.isfinite(rf):
        raise ValueError('RF must be a finite monthly return')
    n = len(m)
    scale = np.max(np.diag(c))
    cs = c / scale
    constraints = [{'type': 'eq', 'fun': lambda w: w.sum()-1,
                    'jac': lambda w: np.ones(n)}]
    if target is not None:
        if not np.isfinite(target) or target < m.min()-1e-12 or target > m.max()+1e-12:
            raise ValueError('Infeasible target return')
        if np.ptp(m) > 1e-12:
            constraints.append({'type':'eq', 'fun':lambda w: w @ m-target, 'jac':lambda w:m})
    if objective == 'min_variance':
        fun = lambda w: w @ cs @ w
        jac = lambda w: 2*cs @ w
        starts = [np.full(n, 1/n)]
    elif objective == 'max_sharpe' and target is None:
        excess = m-rf
        if excess.max() <= 0:
            # For negative numerators, the best ratio over a simplex is at a vertex.
            k = np.argmax(excess/np.sqrt(np.diag(c)))
            return pd.Series(np.eye(n)[k], index=mu.index)
        # Positive-excess Sharpe has an equivalent convex quadratic program:
        # minimize y' C y subject to y'e=1, y>=0; normalize y to weights.
        # Scaling e and C improves conditioning without changing the optimum.
        e=excess/excess.max()
        seed=np.eye(n)[int(np.argmax(e))]
        qp=minimize(lambda y:y@cs@y,seed,jac=lambda y:2*cs@y,
                    method='SLSQP',bounds=[(0.,None)]*n,
                    constraints=[{'type':'eq','fun':lambda y:y@e-1,'jac':lambda y:e}],
                    options={'ftol':1e-12,'maxiter':4000})
        if qp.success and np.isfinite(qp.x).all() and qp.x.min()>=-1e-10 and abs(qp.x@e-1)<1e-8:
            y=np.maximum(qp.x,0)
            return pd.Series(y/y.sum(),index=mu.index)
        fun = lambda w: -(w @ excess)/np.sqrt(w @ c @ w)
        jac = lambda w: -excess/np.sqrt(w @ c @ w) + (w @ excess)*(c @ w)/(w @ c @ w)**1.5
        starts = [np.full(n,1/n), np.eye(n)[np.argmax(excess/np.sqrt(np.diag(c)))]]
    else:
        raise ValueError('Unknown objective or target incompatible with Sharpe')
    candidates = []
    for initial in starts:
        result = minimize(fun, initial, jac=jac, method='SLSQP', bounds=[(0.,1.)]*n,
                          constraints=constraints, options={'ftol':1e-12, 'maxiter':2000})
        w = result.x
        if result.success and np.isfinite(w).all() and abs(w.sum()-1) < 1e-8 and w.min() >= -1e-10:
            w = np.maximum(w,0); w /= w.sum()
            if target is None or abs(w @ m-target) < 1e-8:
                candidates.append(w)
    if not candidates:
        raise RuntimeError('Optimizer failed; no equal-weight fallback')
    return pd.Series(min(candidates, key=fun), index=mu.index)


def portfolio_stats(weights, mu, covariance, rf):
    m,c = validate_inputs(mu,covariance)
    w = weights.reindex(mu.index).to_numpy(float)
    if not np.isfinite(w).all() or w.min() < 0 or not np.isclose(w.sum(),1):
        raise ValueError('Invalid portfolio weights')
    mean = w @ m
    vol = np.sqrt(w @ c @ w)
    return {'expected_return_monthly':float(mean), 'volatility_monthly':float(vol),
            'sharpe_annualized':float(np.sqrt(12)*(mean-rf)/vol)}


def frontier(mu, covariance, points=30):
    if not isinstance(points,int) or points < 2:
        raise ValueError('At least two frontier points required')
    minimum = solve(mu,covariance)
    targets = np.linspace(float(minimum @ mu),float(mu.max()),points)
    rows, weights = [], []
    for t in targets:
        w = solve(mu,covariance,target=float(t))
        rows.append(portfolio_stats(w,mu,covariance,0.))
        weights.append(w)
    return pd.DataFrame(rows), pd.DataFrame(weights)


def optimizer_factory(kind, rf_history, ridge=1e-8):
    """Expected RF = mean of RF in the SAME training window; no future RF."""
    def optimizer(history):
        mu,cov = estimate(history,ridge)
        rf = rf_history.reindex(history.index)
        if not np.isfinite(rf.to_numpy(float)).all():
            raise ValueError('RF missing in training window')
        return solve(mu,cov,kind,rf=float(rf.mean()))
    return optimizer
