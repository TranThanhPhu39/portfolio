"""Strict monthly adjusted-price input; never forward-fill missing prices."""

import numpy as np
import pandas as pd

from src.backtest.walk_forward import validate_returns


def prices_to_returns(prices):
    if not isinstance(prices, pd.DataFrame) or prices.empty:
        raise ValueError("Nonempty price panel required")
    validate_returns(prices)
    if not prices.index.is_month_end.all() or (prices.to_numpy(float) <= 0).any():
        raise ValueError("Require month-end labels and strictly positive adjusted prices")
    if len(prices) < 3:
        raise ValueError("Need at least three monthly prices")
    result = prices.pct_change(fill_method=None).iloc[1:]
    validate_returns(result)
    return result


def load_prices(path):
    df = pd.read_csv(path, dtype={"ticker": str})
    if not {"date", "ticker", "adjusted_price"}.issubset(df):
        raise ValueError("Required columns: date,ticker,adjusted_price")
    df["date"] = pd.to_datetime(df.date, errors="raise")
    if (
        df.ticker.isna().any()
        or df.ticker.str.strip().eq("").any()
        or df.duplicated(["date", "ticker"]).any()
    ):
        raise ValueError("Empty ticker or duplicate price observations")
    df["adjusted_price"] = pd.to_numeric(df.adjusted_price, errors="raise")
    panel = df.pivot(index="date", columns="ticker", values="adjusted_price").sort_index()
    returns = prices_to_returns(panel)
    return panel, returns
