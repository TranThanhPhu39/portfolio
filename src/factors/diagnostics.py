"""Summary statistics and comparison helpers for factor returns."""

from __future__ import annotations

import numpy as np
import pandas as pd


def factor_summary(factors: pd.DataFrame) -> pd.DataFrame:
    """Return monthly mean, standard deviation, t-statistic, and observations."""
    count = factors.count()
    mean = factors.mean()
    std = factors.std(ddof=1)
    t_stat = mean.div(std.div(np.sqrt(count)))
    return pd.DataFrame({"mean": mean, "std": std, "t_stat": t_stat, "n": count})


def compare_factors(own: pd.DataFrame, reference: pd.DataFrame) -> pd.DataFrame:
    """Compare matching factors after converting both indexes to month periods."""
    left = own.copy()
    right = reference.copy()
    left.index = pd.to_datetime(left.index).to_period("M")
    right.index = pd.to_datetime(right.index).to_period("M")
    common_columns = left.columns.intersection(right.columns)
    joined = left[common_columns].join(
        right[common_columns], how="inner", lsuffix="_own", rsuffix="_reference"
    )
    rows = []
    for name in common_columns:
        pair = joined[[f"{name}_own", f"{name}_reference"]].dropna()
        rows.append({
            "factor": name,
            "correlation": pair.iloc[:, 0].corr(pair.iloc[:, 1]),
            "own_mean": pair.iloc[:, 0].mean(),
            "reference_mean": pair.iloc[:, 1].mean(),
            "n_overlap": len(pair),
        })
    return pd.DataFrame(rows).set_index("factor")
