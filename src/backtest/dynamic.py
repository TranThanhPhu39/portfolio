"""Monthly changing eligibility; missing returns are allowed only for unheld assets."""
import numpy as np
import pandas as pd

from .transaction_costs import rebalance, validate_weights
from .walk_forward import BacktestResult


def validate_dynamic_returns(returns):
    if not isinstance(returns, pd.DataFrame) or returns.empty or returns.shape[1] == 0:
        raise ValueError("Returns must be a nonempty DataFrame.")
    if not isinstance(returns.index, pd.DatetimeIndex) or returns.index.hasnans:
        raise ValueError("Returns require a valid DatetimeIndex.")
    months = returns.index.to_period("M")
    if not returns.index.is_monotonic_increasing or months.has_duplicates:
        raise ValueError("Supply sorted observations with one row per month.")
    if len(months) > 1 and not np.all(np.diff(months.asi8) == 1):
        raise ValueError("Missing calendar month.")
    if returns.columns.has_duplicates:
        raise ValueError("Duplicate asset names.")
    values = returns.to_numpy(dtype=float)
    observed = ~np.isnan(values)
    if np.isinf(values).any() or (values[observed] <= -1).any():
        raise ValueError("Observed returns must be finite and greater than -100%.")


def validate_membership(membership, returns):
    if not isinstance(membership, pd.DataFrame):
        raise ValueError("Membership must be a DataFrame.")
    if not returns.index.equals(membership.index) or not returns.columns.equals(
        membership.columns
    ):
        raise ValueError("Membership must align exactly with the return panel.")
    if membership.isna().to_numpy().any():
        raise ValueError("Membership cannot contain missing values.")
    values = membership.to_numpy(dtype=object).ravel()
    if not all(isinstance(value, (bool, np.bool_)) for value in values):
        raise ValueError("Membership values must be explicit booleans.")


def make_dynamic_schedule(
    returns, membership, optimizer, lookback=24, lag=1, rebalance_every=1
):
    validate_dynamic_returns(returns)
    validate_membership(membership, returns)
    for value in (lookback, lag, rebalance_every):
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError("Window, lag and interval must be integers.")
    if lookback < 2 or lag < 1 or rebalance_every < 1:
        raise ValueError("Require lookback>=2, lag>=1 and rebalance_every>=1.")

    schedule = []
    audit = []
    start = lookback + lag
    regular_positions = set(range(start, len(returns), rebalance_every))
    # Membership changes force a trade so an exited constituent is not held
    # until the next ordinary rebalance date.
    membership_changes = membership.ne(membership.shift()).any(axis=1)
    forced_positions = set(np.flatnonzero(membership_changes.to_numpy()))
    positions = sorted(regular_positions | {pos for pos in forced_positions if pos >= start})
    for pos in positions:
        hist = returns.iloc[pos - lag - lookback : pos - lag]
        members = membership.iloc[pos]
        eligible = members & hist.notna().all()
        names = returns.columns[eligible]
        if len(names) < 2:
            raise ValueError(f"Insufficient eligible assets at {returns.index[pos]}.")
        sub = hist.loc[:, names].copy()
        weights = validate_weights(optimizer(sub), names)
        target = pd.Series(0.0, index=returns.columns)
        target.loc[names] = weights
        schedule.append(
            dict(
                position=pos,
                train_start=sub.index[0],
                train_end=sub.index[-1],
                weights=target.to_numpy(),
            )
        )
        for name in returns.columns[members]:
            audit.append(
                dict(
                    date=returns.index[pos],
                    ticker=name,
                    eligible=bool(eligible[name]),
                    training_months=int(hist[name].notna().sum()),
                )
            )
    if not schedule:
        raise ValueError("Not enough data for training and evaluation.")
    return schedule, pd.DataFrame(audit)


def simulate_dynamic(returns, schedule, rate):
    validate_dynamic_returns(returns)
    if not np.isfinite(rate) or not 0 <= rate < 1:
        raise ValueError("Invalid fee rate.")
    if not isinstance(schedule, (list, tuple)) or not schedule:
        raise ValueError("Schedule must be nonempty.")

    orders = {}
    for item in schedule:
        if not isinstance(item, dict) or "position" not in item:
            raise ValueError("Invalid schedule item.")
        pos = item["position"]
        if (
            isinstance(pos, bool)
            or not isinstance(pos, int)
            or pos < 1
            or pos >= len(returns)
            or pos in orders
        ):
            raise ValueError("Invalid or duplicate execution position.")
        if "train_start" not in item or "train_end" not in item:
            raise ValueError("Schedule item is missing training dates.")
        if (
            pd.isna(item["train_start"])
            or pd.isna(item["train_end"])
            or item["train_start"] > item["train_end"]
            or item["train_end"] >= returns.index[pos]
        ):
            raise ValueError("Invalid or look-ahead training dates.")
        target = pd.Series(item.get("weights"), index=returns.columns)
        item = dict(item)
        item["weights"] = validate_weights(target, returns.columns)
        orders[pos] = item

    holdings = np.zeros(returns.shape[1])
    cash = 1.0
    periods, trades, weights = [], [], []
    for pos in range(min(orders), len(returns)):
        date = returns.index[pos]
        before = float(holdings.sum() + cash)
        old = holdings.copy()
        fee = turnover = 0.0
        if pos in orders:
            item = orders[pos]
            holdings, delta, fee, turnover = rebalance(
                holdings, cash, item["weights"], rate
            )
            cash = 0.0
            for k, name in enumerate(returns.columns):
                trades.append(
                    dict(
                        date=date,
                        asset=name,
                        train_start=item["train_start"],
                        train_end=item["train_end"],
                        pretrade_weight=old[k] / before,
                        target_weight=item["weights"][k],
                        trade_value=delta[k],
                        fee=abs(delta[k]) * rate,
                    )
                )
        after = float(holdings.sum())
        period_returns = returns.iloc[pos].to_numpy(float)
        held = holdings > 0
        if not np.isfinite(period_returns[held]).all() or (
            period_returns[held] <= -1
        ).any():
            raise ValueError(f"Missing/invalid return for held asset at {date}.")
        for k, name in enumerate(returns.columns):
            weights.append(
                dict(
                    date=date,
                    asset=name,
                    start_weight=holdings[k] / after,
                )
            )
        holdings[held] *= 1 + period_returns[held]
        end = float(holdings.sum())
        periods.append(
            dict(
                date=date,
                start_value=before,
                fee=fee,
                turnover_two_way=turnover,
                rebalanced=pos in orders,
                market_return=end / after - 1,
                net_return=end / before - 1,
                end_value=end,
            )
        )
    return BacktestResult(
        pd.DataFrame(periods).set_index("date"),
        pd.DataFrame(trades),
        pd.DataFrame(weights),
    )
