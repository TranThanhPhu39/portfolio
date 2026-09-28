"""Download reproducible US test data for the factor and econometrics teams.

This is test data only. Final Vietnam results must use the processed,
point-in-time VN100 panel.
"""

from __future__ import annotations

from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pandas_datareader.data as web
import yfinance as yf

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.factors import compute_smb_hml, portfolio_sort  # noqa: E402

OUT_DIR = ROOT / "test_data"
OUT_DIR.mkdir(parents=True, exist_ok=True)

TICKERS = [
    "AAPL", "MSFT", "JNJ", "XOM", "GE", "KO", "PFE", "WMT", "CAT",
    "IBM", "DIS", "MCD", "CVX", "HD", "MMM", "BA", "AXP", "NKE",
    "PG", "TRV", "UNH", "VZ", "V", "JPM", "CSCO", "INTC", "MRK",
    "GS", "HON", "CRM",
]


def get_ff_factors() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Download monthly FF3, FF5, and 25 Size--B/M portfolios."""
    datasets = {
        "ff3_factors_monthly.csv": "F-F_Research_Data_Factors",
        "ff5_factors_monthly.csv": "F-F_Research_Data_5_Factors_2x3",
        "25_portfolios_size_bm.csv": "25_Portfolios_5x5",
    }
    frames = []
    for filename, dataset in datasets.items():
        print(f"Downloading {dataset} ...")
        frame = web.DataReader(dataset, "famafrench")[0].copy()
        frame.index = frame.index.to_timestamp()
        frame = frame / 100.0
        frame.to_csv(OUT_DIR / filename)
        print(f"  saved {filename}: {len(frame)} rows")
        frames.append(frame)
    return tuple(frames)


def get_stock_level_test_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Download adjusted prices and create deterministic test characteristics."""
    print(f"Downloading adjusted prices for {len(TICKERS)} US tickers ...")
    raw = yf.download(
        TICKERS,
        start="2018-01-01",
        end="2023-01-01",
        auto_adjust=True,
        progress=False,
    )
    prices = raw["Close"].reindex(columns=TICKERS).dropna(how="all")
    if prices.empty:
        raise RuntimeError("Yahoo Finance returned no stock-price data")
    prices.to_csv(OUT_DIR / "us_test_prices.csv")

    rng = np.random.default_rng(42)
    characteristics = pd.DataFrame(
        {
            "size": prices.ffill().iloc[-1]
            * pd.Series(rng.uniform(1e8, 5e9, len(TICKERS)), index=TICKERS),
            "book_to_market": pd.Series(
                rng.uniform(0.1, 3.0, len(TICKERS)), index=TICKERS
            ),
        }
    )
    characteristics.to_csv(OUT_DIR / "us_test_characteristics.csv")
    print(f"  saved prices {prices.shape} and characteristics {characteristics.shape}")
    return prices, characteristics


def smoke_test(prices: pd.DataFrame, characteristics: pd.DataFrame) -> None:
    """Verify that monthly factor construction runs and loses no ticker."""
    monthly_returns = prices.resample("ME").last().pct_change(fill_method=None).dropna(how="all")
    characteristics = characteristics.reindex(monthly_returns.columns)
    groups = portfolio_sort(
        characteristics["size"], characteristics["book_to_market"]
    )
    assert len(groups) == len(characteristics)
    assert groups.notna().all()
    factors = compute_smb_hml(
        monthly_returns, groups, weights=characteristics["size"]
    )
    if factors.empty or factors.isna().all().any():
        raise AssertionError("SMB/HML smoke test did not produce valid series")
    print("SMB/HML monthly smoke test: OK")


def main() -> None:
    get_ff_factors()
    prices, characteristics = get_stock_level_test_data()
    smoke_test(prices, characteristics)
    expected = {
        "ff3_factors_monthly.csv",
        "ff5_factors_monthly.csv",
        "25_portfolios_size_bm.csv",
        "us_test_prices.csv",
        "us_test_characteristics.csv",
    }
    missing = sorted(name for name in expected if not (OUT_DIR / name).is_file())
    if missing:
        raise AssertionError(f"missing expected outputs: {missing}")
    print(f"Complete: five test CSV files are in {OUT_DIR}")


if __name__ == "__main__":
    main()
