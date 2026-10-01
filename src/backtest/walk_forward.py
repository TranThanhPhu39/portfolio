"""Monthly, fixed-universe research engine. See README for execution limits."""
from dataclasses import dataclass
import numpy as np
import pandas as pd
from .transaction_costs import validate_weights, rebalance


def validate_returns(returns):
    if not isinstance(returns, pd.DataFrame) or returns.empty or returns.shape[1] == 0:
        raise ValueError("Returns must be a nonempty DataFrame.")
    if not isinstance(returns.index, pd.DatetimeIndex) or returns.index.hasnans:
        raise ValueError("Returns require valid datetime index.")
    months = returns.index.to_period('M')
    if not returns.index.is_monotonic_increasing or months.has_duplicates:
        raise ValueError("Supply sorted observations with exactly one row per month.")
    if len(months) > 1 and not np.all(np.diff(months.asi8) == 1):
        raise ValueError("Missing month: do not silently compress time.")
    if returns.columns.has_duplicates:
        raise ValueError("Duplicate asset names.")
    values = returns.to_numpy(dtype=float)
    if not np.isfinite(values).all() or (values <= -1).any():
        raise ValueError("Missing/nonfinite returns or return <= -100%; resolve upstream.")


def make_schedule(returns, optimizer, lookback, rebalance_every, decision_lag_periods=1):
    """Optimizer receives historical raw simple returns only.

    lag=1 excludes the return immediately before execution, giving a full
    monthly implementation lag. lag=0 assumes trading at the preceding close
    with that close already known; requires explicit research justification.
    """
    validate_returns(returns)
    for value in (lookback, rebalance_every, decision_lag_periods):
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError("Window, interval and lag must be integers.")
    if lookback < 2 or rebalance_every < 1 or decision_lag_periods < 0:
        raise ValueError("Invalid window, interval or lag.")
    start = lookback + decision_lag_periods
    if start >= len(returns):
        raise ValueError("Not enough history and out-of-sample data.")
    records = []
    for pos in range(start, len(returns), rebalance_every):
        stop = pos - decision_lag_periods
        history = returns.iloc[stop-lookback:stop].copy()
        # Copies keep optimizer mutations from changing source returns.
        weights = validate_weights(optimizer(history), returns.columns)
        records.append(dict(position=pos, train_start=history.index[0],
                            train_end=history.index[-1], weights=weights))
    return records


@dataclass
class BacktestResult:
    periods: pd.DataFrame
    trades: pd.DataFrame
    weights: pd.DataFrame


def simulate(returns, schedule, transaction_cost_rate, initial_wealth=1.):
    validate_returns(returns)
    if not np.isfinite(initial_wealth) or initial_wealth <= 0:
        raise ValueError("Initial wealth must be positive.")
    if not np.isfinite(transaction_cost_rate) or not 0 <= transaction_cost_rate < 1:
        raise ValueError("Invalid transaction_cost_rate.")
    if not schedule:
        raise ValueError("Schedule is empty.")
    orders = {}
    for item in schedule:
        pos = item['position']
        if isinstance(pos, bool) or not isinstance(pos, int) or pos < 1 or pos >= len(returns) or pos in orders:
            raise ValueError("Invalid/duplicate execution position.")
        if pd.isna(item['train_start']) or pd.isna(item['train_end']) or item['train_start'] > item['train_end']:
            raise ValueError("Invalid training dates.")
        if item['train_end'] > returns.index[pos-1]:
            raise ValueError("Training overlaps execution period.")
        orders[pos] = item
    start = min(orders)
    holdings = np.zeros(returns.shape[1])
    cash = float(initial_wealth)
    period_rows, trade_rows, weight_rows = [], [], []
    for pos in range(start, len(returns)):
        date = returns.index[pos]
        before = float(holdings.sum() + cash)
        old_holdings = holdings.copy()
        fee = turnover = 0.
        rebalanced = pos in orders
        if rebalanced:
            item = orders[pos]
            holdings, trades, fee, turnover = rebalance(
                holdings, cash, item['weights'], transaction_cost_rate)
            cash = 0.
            for k, asset in enumerate(returns.columns):
                trade_rows.append(dict(date=date, asset=asset,
                    train_start=item['train_start'], train_end=item['train_end'],
                    pretrade_weight=old_holdings[k]/before,
                    target_weight=float(item['weights'][k]),
                    trade_value=trades[k], fee=abs(trades[k])*transaction_cost_rate))
        after = float(holdings.sum())
        for k, asset in enumerate(returns.columns):
            weight_rows.append(dict(date=date, asset=asset, start_weight=holdings[k]/after))
        holdings *= 1 + returns.iloc[pos].to_numpy(dtype=float)
        end = float(holdings.sum())
        period_rows.append(dict(date=date, start_value=before, fee=fee,
            turnover_two_way=turnover, rebalanced=rebalanced,
            market_return=end/after-1, net_return=end/before-1, end_value=end))
    return BacktestResult(pd.DataFrame(period_rows).set_index('date'),
                          pd.DataFrame(trade_rows), pd.DataFrame(weight_rows))


def run_walk_forward(returns, optimizer, *, lookback, rebalance_every,
                     transaction_cost_rate, decision_lag_periods=1, initial_wealth=1.):
    schedule = make_schedule(returns, optimizer, lookback, rebalance_every, decision_lag_periods)
    return simulate(returns, schedule, transaction_cost_rate, initial_wealth)


def run_cost_scenarios(returns, optimizer, *, lookback, rebalance_every,
                       rates=(0., .0015, .0025, .0035), decision_lag_periods=1):
    rates = tuple(float(rate) for rate in rates)
    if not rates or len(set(rates)) != len(rates):
        raise ValueError("Provide distinct fee scenarios.")
    # Shared targets ensure fee scenarios do not retune the strategy on outcomes.
    schedule = make_schedule(returns, optimizer, lookback, rebalance_every, decision_lag_periods)
    return {rate: simulate(returns, schedule, rate) for rate in rates}
