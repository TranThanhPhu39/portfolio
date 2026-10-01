"""Monthly ex-post metrics. RF must already be monthly simple returns."""
import numpy as np
import pandas as pd
from .benchmark import align_series
from .walk_forward import validate_returns


def metrics(net_returns, risk_free):
    validate_returns(net_returns.to_frame('portfolio'))
    if len(net_returns) < 2:
        raise ValueError('At least two out-of-sample months required.')
    rf = align_series(risk_free, net_returns.index, 'risk_free')
    excess = net_returns.astype(float) - rf
    sd = excess.std(ddof=1)
    sharpe = float(np.sqrt(12)*excess.mean()/sd) if sd > 1e-14 else float('nan')
    wealth = (1 + net_returns).cumprod()
    # Include initial capital in peak; first-period loss must count as drawdown.
    peak = np.maximum.accumulate(np.r_[1., wealth.to_numpy()])[1:]
    return dict(months=len(net_returns), sharpe=sharpe,
        cagr=float(wealth.iloc[-1]**(12/len(net_returns))-1),
        max_drawdown=float((wealth.to_numpy()/peak-1).min()),
        total_return=float(wealth.iloc[-1]-1))


def comparison_table(results, risk_free, benchmark):
    rows = []
    dates = next(iter(results.values())).periods.index
    for rate, result in results.items():
        if not result.periods.index.equals(dates):
            raise ValueError('Scenarios have unequal out-of-sample periods.')
        rows.append(dict(name='strategy', transaction_cost_rate=rate,
            **metrics(result.periods.net_return, risk_free),
            total_fee=float(result.periods.fee.sum()),
            total_turnover_two_way=float(result.periods.turnover_two_way.sum())))
    b = align_series(benchmark, dates, 'benchmark')
    rows.append(dict(name='benchmark', transaction_cost_rate=np.nan,
        **metrics(b, risk_free), total_fee=np.nan, total_turnover_two_way=np.nan))
    return pd.DataFrame(rows)


def fee_crossings(table):
    """Report observed brackets, never claim an exact/monotonic threshold."""
    strategy = table[table.name == 'strategy'].sort_values('transaction_cost_rate')
    b = table.loc[table.name == 'benchmark', 'sharpe'].iloc[0]
    rates = strategy.transaction_cost_rate.to_numpy()
    diff = strategy.sharpe.to_numpy() - b
    if not np.isfinite(diff).all():
        return {'status': 'undefined_sharpe', 'brackets': []}
    if len(rates) == 0 or rates[0] != 0:
        return {'status': 'zero_cost_baseline_missing', 'brackets': []}
    if diff[0] <= 0:
        return {'status': 'no_positive_advantage_at_zero_cost', 'brackets': []}
    brackets = [(float(rates[i-1]),float(rates[i])) for i in range(1,len(rates))
                if diff[i-1] > 0 and diff[i] <= 0]
    return {'status': 'crossing_bracket_found' if brackets else 'no_crossing_in_tested_range',
            'brackets': brackets}
