"""Portfolio sorts used to construct Fama--French factors."""

from __future__ import annotations

import numpy as np
import pandas as pd


def portfolio_sort(
    size: pd.Series,
    characteristic: pd.Series,
    *,
    size_bp: float = 0.5,
    characteristic_bp: tuple[float, float] = (0.3, 0.7),
    labels: tuple[str, str, str, str, str, str] =
    ("SL", "SN", "SH", "BL", "BN", "BH"),
) -> pd.Series:
    """Independently sort securities into 2 Size x 3 characteristic groups.

    The function is intentionally strict: mismatched indexes, duplicates, or
    missing/non-finite inputs raise an error instead of silently dropping a
    security. Breakpoint observations are assigned to the lower bucket.
    """
    if not size.index.equals(characteristic.index):
        raise ValueError("size and characteristic must have identical indexes")
    if not size.index.is_unique:
        raise ValueError("ticker index must be unique")
    if not 0 < size_bp < 1:
        raise ValueError("size_bp must be between 0 and 1")
    low_bp, high_bp = characteristic_bp
    if not 0 < low_bp < high_bp < 1:
        raise ValueError("characteristic breakpoints must satisfy 0 < low < high < 1")

    frame = pd.concat(
        [size.rename("size"), characteristic.rename("characteristic")], axis=1
    ).astype(float)
    if frame.isna().any().any() or not np.isfinite(frame.to_numpy()).all():
        raise ValueError("sort inputs contain missing or non-finite values")

    size_cut = frame["size"].quantile(size_bp)
    low_cut, high_cut = frame["characteristic"].quantile([low_bp, high_bp])
    small = frame["size"] <= size_cut
    low = frame["characteristic"] <= low_cut
    high = frame["characteristic"] > high_cut
    neutral = ~(low | high)

    sl, sn, sh, bl, bn, bh = labels
    values = np.select(
        [small & low, small & neutral, small & high,
         ~small & low, ~small & neutral, ~small & high],
        [sl, sn, sh, bl, bn, bh],
        default=None,
    )
    result = pd.Series(values, index=frame.index, name="portfolio", dtype="object")
    if result.isna().any() or len(result) != len(size):
        raise AssertionError("portfolio sort lost one or more securities")
    return result
