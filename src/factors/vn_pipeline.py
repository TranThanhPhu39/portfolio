"""Annual July factor construction for a point-in-time Vietnam stock panel."""

from __future__ import annotations

import pandas as pd

from .portfolio_sort import portfolio_sort
from .smb_hml import compute_smb_hml, portfolio_returns

REQUIRED_COLUMNS = {
    "date", "ticker", "adjusted_price", "market_cap", "book_to_market",
    "operating_profitability", "investment", "information_date",
}


def validate_vn_panel(panel: pd.DataFrame) -> pd.DataFrame:
    """Validate and normalize the long-format point-in-time input panel."""
    missing = sorted(REQUIRED_COLUMNS.difference(panel.columns))
    if missing:
        raise ValueError(f"VN panel is missing required columns: {missing}")
    data = panel.copy()
    data["date"] = pd.to_datetime(data["date"])
    data["information_date"] = pd.to_datetime(data["information_date"])
    if data[["date", "ticker"]].duplicated().any():
        raise ValueError("VN panel contains duplicate date-ticker rows")
    if (data["information_date"] > data["date"]).any():
        raise ValueError("information_date cannot be later than the row date")
    data["ticker"] = data["ticker"].astype(str)
    return data.sort_values(["date", "ticker"]).reset_index(drop=True)


def _size_spread(portfolios: pd.DataFrame, labels: tuple[str, ...]) -> pd.Series:
    small = portfolios[list(labels[:3])].mean(axis=1)
    big = portfolios[list(labels[3:])].mean(axis=1)
    return small - big


def construct_vn_factors(panel: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Construct annual-membership, monthly value-weighted VN factors.

    Portfolios are formed using information available by 30 June of year t and
    held from July t through June t+1. Monthly returns use lagged market cap.
    Returns a factor table and an eligibility audit table.
    """
    data = validate_vn_panel(panel)
    monthly = data.assign(month=data["date"].dt.to_period("M"))
    monthly = monthly.sort_values("date").groupby(["month", "ticker"], as_index=False).tail(1)
    prices = monthly.pivot(index="month", columns="ticker", values="adjusted_price")
    returns = prices.pct_change(fill_method=None)
    market_caps = monthly.pivot(index="month", columns="ticker", values="market_cap")
    lagged_caps = market_caps.shift(1)

    factor_blocks: list[pd.DataFrame] = []
    audit_rows: list[dict] = []
    for year in range(data["date"].dt.year.min(), data["date"].dt.year.max() + 1):
        cutoff = pd.Timestamp(year=year, month=6, day=30)
        available = data[
            (data["date"] <= cutoff) & (data["information_date"] <= cutoff)
        ].sort_values(["ticker", "date"]).groupby("ticker", as_index=False).tail(1)
        available = available.set_index("ticker")
        numeric = [
            "market_cap", "book_to_market", "operating_profitability", "investment"
        ]
        eligible = available[numeric].notna().all(axis=1)
        eligible &= available["market_cap"].gt(0) & available["book_to_market"].gt(0)
        for ticker in available.index:
            audit_rows.append({
                "formation_year": year,
                "ticker": ticker,
                "eligible": bool(eligible.loc[ticker]),
                "reason": "eligible" if eligible.loc[ticker] else "missing/invalid characteristic",
            })
        chars = available.loc[eligible]
        if chars.empty:
            continue

        holding = returns.index[(returns.index >= pd.Period(f"{year}-07", "M")) &
                                (returns.index <= pd.Period(f"{year + 1}-06", "M"))]
        tickers = chars.index.intersection(returns.columns)
        if holding.empty or tickers.empty:
            continue
        period_returns = returns.loc[holding, tickers]
        period_weights = lagged_caps.loc[holding, tickers]
        size = chars.loc[tickers, "market_cap"]

        bm_labels = ("SL", "SN", "SH", "BL", "BN", "BH")
        bm_groups = portfolio_sort(size, chars.loc[tickers, "book_to_market"], labels=bm_labels)
        bm_portfolios = portfolio_returns(period_returns, bm_groups, period_weights,
                                           required_groups=bm_labels)
        ff3 = compute_smb_hml(period_returns, bm_groups, period_weights)

        op_labels = ("SW", "SN", "SR", "BW", "BN", "BR")
        op_groups = portfolio_sort(size, chars.loc[tickers, "operating_profitability"],
                                   labels=op_labels)
        op_portfolios = portfolio_returns(period_returns, op_groups, period_weights,
                                           required_groups=op_labels)
        rmw = op_portfolios[["SR", "BR"]].mean(axis=1) - op_portfolios[
            ["SW", "BW"]
        ].mean(axis=1)

        inv_labels = ("SC", "SN", "SA", "BC", "BN", "BA")
        inv_groups = portfolio_sort(size, chars.loc[tickers, "investment"], labels=inv_labels)
        inv_portfolios = portfolio_returns(period_returns, inv_groups, period_weights,
                                            required_groups=inv_labels)
        cma = inv_portfolios[["SC", "BC"]].mean(axis=1) - inv_portfolios[
            ["SA", "BA"]
        ].mean(axis=1)

        smb_ff5 = pd.concat([
            _size_spread(bm_portfolios, bm_labels),
            _size_spread(op_portfolios, op_labels),
            _size_spread(inv_portfolios, inv_labels),
        ], axis=1).mean(axis=1)
        factor_blocks.append(ff3.assign(SMB_FF5=smb_ff5, RMW=rmw, CMA=cma))

    if not factor_blocks:
        raise ValueError("no valid July-to-June formation period could be constructed")
    factors = pd.concat(factor_blocks).sort_index()
    factors.index = factors.index.to_timestamp("M")
    factors.index.name = "Date"
    return factors[~factors.index.duplicated()], pd.DataFrame(audit_rows)
