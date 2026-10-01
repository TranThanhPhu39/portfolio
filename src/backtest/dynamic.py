"""Backtest support for a monthly changing eligible universe."""

import numpy as np
import pandas as pd

from .transaction_costs import rebalance, validate_weights
from .walk_forward import BacktestResult


def make_dynamic_schedule(returns, membership, optimizer, lookback=24, lag=1):
    if lookback < 2 or lag < 1:
        raise ValueError("Require lookback>=2 and lag>=1")
    if not returns.index.equals(membership.index) or not returns.columns.equals(
        membership.columns
    ):
        raise ValueError("Membership must align exactly with return panel")
    if (
        returns.index.has_duplicates
        or not returns.index.is_monotonic_increasing
        or returns.columns.has_duplicates
    ):
        raise ValueError("Duplicate/unsorted dates or assets")
    if not np.all(np.diff(returns.index.to_period("M").asi8) == 1):
        raise ValueError("Missing calendar month")
    finite = returns.notna()
    if np.isinf(returns.to_numpy()).any() or (returns[finite] <= -1).any().any():
        raise ValueError("Invalid returns")
    schedule = []
    audit = []
    for position in range(lookback + lag, len(returns)):
        history = returns.iloc[position - lag - lookback : position - lag]
        members = membership.iloc[position].astype(bool)
        eligible = members & history.notna().all()
        names = returns.columns[eligible]
        if len(names) < 2:
            raise ValueError(f"Insufficient eligible assets at {returns.index[position]}")
        sample = history.loc[:, names].copy()
        weights = validate_weights(optimizer(sample), names)
        target = pd.Series(0.0, index=returns.columns)
        target.loc[names] = weights
        schedule.append(
            {
                "position": position,
                "train_start": sample.index[0],
                "train_end": sample.index[-1],
                "weights": target.to_numpy(),
            }
        )
        for name in returns.columns[members]:
            audit.append(
                {
                    "date": returns.index[position],
                    "ticker": name,
                    "eligible": bool(eligible[name]),
                    "training_months": int(history[name].notna().sum()),
                }
            )
    if not schedule:
        raise ValueError("Not enough data for training and evaluation")
    return schedule, pd.DataFrame(audit)


def simulate_dynamic(returns, schedule, rate):
    if not 0 <= rate < 1:
        raise ValueError("Invalid fee rate")
    orders = {item["position"]: item for item in schedule}
    if len(orders) != len(schedule):
        raise ValueError("Duplicate orders")
    holdings = np.zeros(returns.shape[1])
    cash = 1.0
    periods = []
    trades = []
    weights = []
    for position in range(min(orders), len(returns)):
        date = returns.index[position]
        before = float(holdings.sum() + cash)
        old_holdings = holdings.copy()
        fee = turnover = 0.0
        if position in orders:
            item = orders[position]
            if item["train_end"] >= date:
                raise ValueError("Look-ahead in schedule")
            target = pd.Series(item["weights"], index=returns.columns)
            validated = validate_weights(target, returns.columns)
            holdings, delta, fee, turnover = rebalance(
                holdings, cash, validated, rate
            )
            cash = 0.0
            for index, name in enumerate(returns.columns):
                trades.append(
                    {
                        "date": date,
                        "asset": name,
                        "train_start": item["train_start"],
                        "train_end": item["train_end"],
                        "pretrade_weight": old_holdings[index] / before,
                        "target_weight": validated[index],
                        "trade_value": delta[index],
                        "fee": abs(delta[index]) * rate,
                    }
                )
        after = float(holdings.sum())
        period_returns = returns.iloc[position].to_numpy(float)
        held = holdings > 0
        if not np.isfinite(period_returns[held]).all() or (
            period_returns[held] <= -1
        ).any():
            raise ValueError(f"Missing/invalid return for held asset at {date}")
        for index, name in enumerate(returns.columns):
            weights.append(
                {
                    "date": date,
                    "asset": name,
                    "start_weight": holdings[index] / after,
                }
            )
        holdings[held] *= 1 + period_returns[held]
        end = float(holdings.sum())
        periods.append(
            {
                "date": date,
                "start_value": before,
                "fee": fee,
                "turnover_two_way": turnover,
                "rebalanced": position in orders,
                "market_return": end / after - 1,
                "net_return": end / before - 1,
                "end_value": end,
            }
        )
    return BacktestResult(
        pd.DataFrame(periods).set_index("date"),
        pd.DataFrame(trades),
        pd.DataFrame(weights),
    )
