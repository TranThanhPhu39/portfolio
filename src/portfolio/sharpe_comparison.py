"""Like-for-like in-sample Sharpe comparison, without forcing an ordering."""
import json
import numpy as np
import pandas as pd
from src.backtest.walk_forward import validate_returns
from src.backtest.benchmark import align_series
from src.backtest.transaction_costs import validate_weights


def compare_sharpes(history, risk_free, max_sharpe_weights):
    validate_returns(history)
    if len(history) < 2:
        raise ValueError('At least two common monthly observations required')
    rf = align_series(risk_free, history.index, 'risk_free')
    w = validate_weights(max_sharpe_weights, history.columns)
    shared = dict(start_date=history.index[0].date().isoformat(),
                  end_date=history.index[-1].date().isoformat(), months=len(history),
                  rf_mean_monthly=float(rf.mean()), sample='in_sample', fee_rate=0.)
    rows = []
    def row(name, kind, returns):
        excess = returns - rf
        sd = float(excess.std(ddof=1))
        return dict(name=name, kind=kind, **shared,
                    mean_return_monthly=float(returns.mean()),
                    mean_excess_monthly=float(excess.mean()), excess_sd_monthly=sd,
                    sharpe_annualized=float(np.sqrt(12)*excess.mean()/sd) if sd > 1e-14 else np.nan)
    rows.append(row('MaxSharpe', 'portfolio', history.astype(float) @ w))
    for asset in history.columns:
        rows.append(row(str(asset), 'asset', history[asset].astype(float)))
    individual = np.array([r['sharpe_annualized'] for r in rows[1:]])
    valid = bool(np.isfinite(individual).all())
    avg = float(individual.mean()) if valid else np.nan
    rows.append(dict(name='MeanAssetSharpe', kind='arithmetic_mean_of_asset_sharpes',
                     **shared, mean_return_monthly=np.nan, mean_excess_monthly=np.nan,
                     excess_sd_monthly=np.nan, sharpe_annualized=avg))
    table = pd.DataFrame(rows)
    score = rows[0]['sharpe_annualized']
    def difference(value):
        return float(score-value) if np.isfinite(score) and np.isfinite(value) else None
    best = float(individual.max()) if valid else np.nan
    metadata = dict(**shared, assets=len(individual), valid_asset_sharpes=int(np.isfinite(individual).sum()),
        max_sharpe_minus_mean_asset=difference(avg), max_sharpe_minus_best_asset=difference(best),
        formula='sqrt(12) * mean(r_t - RF_t) / sample_std(r_t - RF_t), ddof=1',
        portfolio_return='Each month: sum(first-window target weights * asset monthly returns); no fees',
        mean_definition='Arithmetic mean of ALL individual asset Sharpes; not Sharpe of equal-weight portfolio',
        missing_rule='Reject missing returns or RF; undefined asset Sharpe makes the overall mean undefined',
        interpretation='In-sample descriptive comparison, not an out-of-sample guarantee. Empirical excess-return SD does not include covariance ridge; variable RF can differ from the optimizer objective.')
    return table, metadata


def export_sharpe_comparison(out, history, risk_free, weights):
    table, metadata = compare_sharpes(history, risk_free, weights)
    table.to_csv(out/'05_sharpe_assets_comparison.csv', index=False)
    (out/'05_sharpe_comparison_metadata.json').write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    # Preserve exact observations and weights used so teammates can reproduce the table.
    inputs = history.copy()
    inputs.to_csv(out/'05_sharpe_input_returns.csv', index_label='date')
    align_series(risk_free, history.index, 'risk_free').to_csv(out/'05_sharpe_input_rf.csv',index_label='date',header=['rf_return'])
    weights.reindex(history.columns).to_csv(out/'05_sharpe_input_weights.csv',index_label='ticker',header=['weight'])
    return table
