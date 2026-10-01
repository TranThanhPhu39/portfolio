"""Strict benchmark/RF alignment; no silent row dropping or filling."""

import numpy as np
import pandas as pd


def align_series(series, dates, name):
    if not isinstance(series, pd.Series) or not isinstance(series.index, pd.DatetimeIndex):
        raise ValueError(f"{name} must be a dated Series.")
    if (
        series.index.has_duplicates
        or series.index.hasnans
        or not series.index.is_monotonic_increasing
    ):
        raise ValueError(f"{name}: invalid index.")
    aligned = series.reindex(dates).astype(float)
    if not np.isfinite(aligned.to_numpy()).all() or (aligned <= -1).any():
        raise ValueError(f"{name}: missing dates/values or invalid returns; resolve upstream.")
    return aligned


def daily_to_monthly(simple_returns):
    """Compound daily simple returns, not sums."""
    if not isinstance(simple_returns.index, pd.DatetimeIndex):
        raise ValueError("Use a DatetimeIndex.")
    if (
        simple_returns.index.has_duplicates
        or simple_returns.index.hasnans
        or not simple_returns.index.is_monotonic_increasing
    ):
        raise ValueError("Dates must be unique, valid and sorted.")
    values = np.asarray(simple_returns, dtype=float)
    if not np.isfinite(values).all() or (values <= -1).any():
        raise ValueError("Resolve missing/invalid daily returns before compounding.")
    counts = simple_returns.resample("ME").size()
    if (counts == 0).any():
        raise ValueError("Entire month absent.")
    return (1 + simple_returns).resample("ME").prod() - 1
