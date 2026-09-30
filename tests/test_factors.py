import numpy as np
import pandas as pd
import pytest

from src.factors import (
    annual_yield_percent_to_monthly,
    build_annual_july_panel,
    build_point_in_time_formations,
    compute_cma,
    compute_rmw,
    compute_smb_hml,
    portfolio_sort,
    reconcile_period_returns,
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


def test_annual_yield_is_converted_to_monthly_decimal():
    monthly = annual_yield_percent_to_monthly(12.0)
    assert (1.0 + monthly) ** 12 == pytest.approx(1.12)


def test_point_in_time_formation_uses_only_announced_information():
    membership = pd.DataFrame({
        "period": [1],
        "ticker": ["AAA.HM"],
        "formation_market_cap": [100.0],
        "formation_date": pd.to_datetime(["2024-06-30"]),
        "holding_start": pd.to_datetime(["2024-08-31"]),
        "holding_end": pd.to_datetime(["2025-01-31"]),
        "complete": [True],
    })
    events = pd.DataFrame({
        "ticker": ["AAA.HM", "AAA.HM"],
        "information_date": pd.to_datetime(["2024-04-30", "2024-07-31"]),
        "source_date": pd.to_datetime(["2024-03-31", "2024-06-30"]),
        "book_equity": [80.0, 120.0],
        "operating_profitability": [0.10, 0.20],
        "investment": [0.05, 0.07],
    })
    result = build_point_in_time_formations(membership, events)
    row = result.iloc[0]
    assert row["information_date"] == pd.Timestamp("2024-04-30")
    assert row["book_to_market"] == pytest.approx(0.8)
    assert row["operating_profitability"] == pytest.approx(0.10)
    assert not row["look_ahead"]


def test_conflicting_fundamental_event_is_not_eligible():
    membership = pd.DataFrame({
        "period": [1],
        "ticker": ["AAA.HM"],
        "formation_market_cap": [100.0],
        "formation_date": pd.to_datetime(["2024-06-30"]),
        "holding_start": pd.to_datetime(["2024-08-31"]),
        "holding_end": pd.to_datetime(["2025-01-31"]),
        "complete": [True],
    })
    events = pd.DataFrame({
        "ticker": ["AAA.HM"],
        "information_date": pd.to_datetime(["2024-04-30"]),
        "source_date": pd.to_datetime(["2024-03-31"]),
        "book_equity": [80.0],
        "operating_profitability": [0.10],
        "investment": [0.05],
        "event_conflict": [True],
    })
    row = build_point_in_time_formations(membership, events).iloc[0]
    assert not row["eligible_bm"]
    assert not row["eligible_op"]
    assert not row["eligible_inv"]
    assert row["reason_bm"] == "conflicting_fundamental_event"


def test_return_reconciliation_prefers_consecutive_month_price_return():
    period_returns = pd.DataFrame({
        "period": [1, 1],
        "ticker": ["AAA.HM", "BBB.HM"],
        "date": pd.to_datetime(["2024-02-29", "2024-02-29"]),
        "return": [1.50, 0.07],
    })
    monthly_prices = pd.DataFrame({
        "ticker": ["AAA.HM", "BBB.HM"],
        "date": pd.to_datetime(["2024-02-29", "2024-02-29"]),
        "close": [110.0, 20.0],
        "previous_close": [100.0, np.nan],
        "price_return": [0.10, np.nan],
    })
    result = reconcile_period_returns(period_returns, monthly_prices)
    aaa = result.loc[result["ticker"].eq("AAA.HM")].iloc[0]
    bbb = result.loc[result["ticker"].eq("BBB.HM")].iloc[0]
    assert aaa["return"] == pytest.approx(0.10)
    assert aaa["reported_return"] == pytest.approx(1.50)
    assert aaa["return_source"] == "close_eom"
    assert bbb["return"] == pytest.approx(0.07)
    assert bbb["return_source"] == "reported_fallback"


def test_annual_july_panel_uses_june_formation_and_twelve_month_holding():
    supplied_periods = pd.DataFrame({
        "Ky": [2, 3, 4],
        "formation_date": pd.to_datetime(["2018-06-30", "2018-12-31", "2019-06-30"]),
    })
    supplied_membership = pd.DataFrame({
        "period": [2, 2, 3, 4, 4],
        "ticker": ["AAA.HM", "BBB.HM", "AAA.HM", "AAA.HM", "BBB.HM"],
        "formation_market_cap": [100.0, 200.0, 110.0, 120.0, 220.0],
        "formation_date": pd.to_datetime([
            "2018-06-30", "2018-06-30", "2018-12-31", "2019-06-30", "2019-06-30"
        ]),
    })
    months = pd.period_range("2018-07", "2019-09", freq="M")
    market_monthly = pd.DataFrame({
        "month": months,
        "VN100": 0.01,
        "VNINDEX": 0.01,
        "VN30": 0.01,
    })
    price_rows = []
    for ticker in ["AAA.HM", "BBB.HM"]:
        for month in months:
            price_rows.append({
                "ticker": ticker,
                "month": month,
                "reported_return": 0.02,
            })
    monthly_prices = pd.DataFrame(price_rows)

    periods, membership, returns = build_annual_july_panel(
        supplied_periods,
        supplied_membership,
        monthly_prices,
        market_monthly,
    )
    assert periods["period"].tolist() == [2018, 2019]
    assert periods["complete"].tolist() == [True, False]
    assert set(membership["period"]) == {2018}
    assert returns["date"].min() == pd.Timestamp("2018-07-31")
    assert returns["date"].max() == pd.Timestamp("2019-06-30")
    assert len(returns) == 24
