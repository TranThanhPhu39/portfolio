import numpy as np
import pandas as pd
import pytest

from src.factors import (
    compute_cma,
    compute_rmw,
    compute_smb_hml,
    portfolio_sort,
    validate_vn_panel,
)


def sample_data():
    tickers = pd.Index([f"T{i}" for i in range(12)])
    size = pd.Series(np.arange(1, 13), index=tickers, dtype=float)
    characteristic = pd.Series(np.tile([1.0, 2.0, 3.0], 4), index=tickers)
    returns = pd.DataFrame(
        np.arange(36, dtype=float).reshape(3, 12) / 100,
        index=pd.date_range("2024-01-31", periods=3, freq="ME"),
        columns=tickers,
    )
    return size, characteristic, returns


def test_portfolio_sort_keeps_every_security():
    size, characteristic, _ = sample_data()
    groups = portfolio_sort(size, characteristic)
    assert len(groups) == len(size)
    assert groups.notna().all()
    assert set(groups) == {"SL", "SN", "SH", "BL", "BN", "BH"}


def test_portfolio_sort_rejects_missing_values():
    size, characteristic, _ = sample_data()
    characteristic.iloc[0] = np.nan
    with pytest.raises(ValueError, match="missing"):
        portfolio_sort(size, characteristic)


def test_smb_hml_and_ff5_extensions_have_expected_shape():
    size, characteristic, returns = sample_data()
    groups = portfolio_sort(size, characteristic)
    ff3 = compute_smb_hml(returns, groups, weights=size)
    rmw = compute_rmw(returns, size, characteristic, weights=size)
    cma = compute_cma(returns, size, characteristic, weights=size)
    assert list(ff3.columns) == ["SMB", "HML"]
    assert len(ff3) == len(returns)
    assert len(rmw) == len(returns)
    assert len(cma) == len(returns)
    assert ff3.notna().all().all()


def test_vn_panel_requires_point_in_time_schema():
    with pytest.raises(ValueError, match="information_date"):
        validate_vn_panel(pd.DataFrame({"date": ["2024-01-01"]}))


def test_vn_panel_rejects_look_ahead_rows():
    panel = pd.DataFrame({
        "date": ["2024-01-31"], "ticker": ["AAA"], "adjusted_price": [10.0],
        "market_cap": [100.0], "book_to_market": [1.0],
        "operating_profitability": [0.2], "investment": [0.1],
        "information_date": ["2024-02-01"],
    })
    with pytest.raises(ValueError, match="information_date"):
        validate_vn_panel(panel)
