"""Return aggregation and construction of SMB/HML."""

from __future__ import annotations

import pandas as pd

SIX_PORTFOLIOS = ("SL", "SN", "SH", "BL", "BN", "BH")


def portfolio_returns(
    returns: pd.DataFrame,
    groups: pd.Series,
    weights: pd.Series | pd.DataFrame | None = None,
    *,
    required_groups: tuple[str, ...] = SIX_PORTFOLIOS,
) -> pd.DataFrame:
    """Aggregate stock returns by group, equal- or value-weighted.

    A weight DataFrame may contain time-varying lagged market capitalizations;
    a Series represents fixed formation-date weights.
    """
    groups = groups.reindex(returns.columns)
    if groups.isna().any():
        missing = groups.index[groups.isna()].tolist()
        raise ValueError(f"missing group for return columns: {missing}")
    absent = [label for label in required_groups if label not in set(groups)]
    if absent:
        raise ValueError(f"empty required portfolios: {absent}")

    result: dict[str, pd.Series] = {}
    for label in required_groups:
        members = groups.index[groups.eq(label)]
        group_returns = returns.loc[:, members]
        if weights is None:
            result[label] = group_returns.mean(axis=1)
            continue
        if isinstance(weights, pd.Series):
            group_weights = weights.reindex(members)
            if group_weights.isna().any():
                raise ValueError(f"missing fixed weights in portfolio {label}")
            numerator = group_returns.mul(group_weights, axis=1).sum(axis=1)
            denominator = group_returns.notna().mul(group_weights, axis=1).sum(axis=1)
        else:
            group_weights = weights.reindex(index=returns.index, columns=members)
            valid_weights = group_weights.where(group_returns.notna())
            numerator = group_returns.mul(valid_weights).sum(axis=1)
            denominator = valid_weights.sum(axis=1)
        result[label] = numerator.div(denominator).where(denominator.ne(0))
    return pd.DataFrame(result, index=returns.index)


def compute_smb_hml(
    returns: pd.DataFrame,
    groups: pd.Series,
    weights: pd.Series | pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Construct SMB and HML from six Size--B/M portfolios."""
    portfolios = portfolio_returns(returns, groups, weights)
    smb = portfolios[["SL", "SN", "SH"]].mean(axis=1) - portfolios[
        ["BL", "BN", "BH"]
    ].mean(axis=1)
    hml = portfolios[["SH", "BH"]].mean(axis=1) - portfolios[
        ["SL", "BL"]
    ].mean(axis=1)
    return pd.DataFrame({"SMB": smb, "HML": hml})
