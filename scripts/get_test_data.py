"""
get_test_data.py
=================
Script lay du lieu de FACTOR TEAM va KINH TE LUONG TEAM test logic code
truoc khi co du lieu VN30 thuc te.

Nguon du lieu:
1. Kenneth French Data Library (qua pandas_datareader) - factor thanh pham
   (MKT, SMB, HML, RMW, CMA) + 25 danh muc Size-B/M de test GRS.
2. Du lieu gia co phieu Mytest (qua yfinance) - du lieu cap co phieu de
   factor team test ham portfolio_sort() tu xay SMB/HML.

Cach chay:
    Chay tu thu muc goc repo sau khi cai requirements.lock.txt.
    .venv\\Scripts\\python.exe scripts\\get_test_data.py

Ket qua: du lieu Kenneth French vao data/test/kenneth_french/;
          du lieu mau Factor Team vao data/test/us_factor_logic/.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from src.models.regressions import run_factor_regression

FRENCH_OUT_DIR = PROJECT_ROOT / "data" / "test" / "kenneth_french"
US_TEST_OUT_DIR = PROJECT_ROOT / "data" / "test" / "us_factor_logic"
FACTOR_TEST_START = "1963-07-01"
FACTOR_TEST_END = "2013-12-31"
FRENCH_OUT_DIR.mkdir(parents=True, exist_ok=True)
US_TEST_OUT_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# PHAN 1: Lay factor thanh pham tu Kenneth French Data Library
# Dung cho: Kinh te luong team (test hoi quy CAPM/FF3/FF5)
#           Factor team (doi chieu ket qua tu xay SMB/HML voi ban goc)
# ---------------------------------------------------------------------------

def get_ff_factors():
    import pandas_datareader.data as web

    print("Dang tai FF 3-factor (MKT, SMB, HML)...")
    ff3_raw = web.DataReader(
        "F-F_Research_Data_Factors",
        "famafrench",
        start=FACTOR_TEST_START,
        end=FACTOR_TEST_END,
    )
    ff3 = ff3_raw[0].copy()
    ff3.index = ff3.index.to_timestamp()
    ff3 = ff3 / 100.0  # doi tu % ve decimal
    ff3.to_csv(FRENCH_OUT_DIR / "ff3_factors_monthly.csv")
    print(f"  -> Da luu {FRENCH_OUT_DIR / 'ff3_factors_monthly.csv'}  ({len(ff3)} dong)")

    print("Dang tai FF 5-factor (MKT, SMB, HML, RMW, CMA)...")
    ff5_raw = web.DataReader(
        "F-F_Research_Data_5_Factors_2x3",
        "famafrench",
        start=FACTOR_TEST_START,
        end=FACTOR_TEST_END,
    )
    ff5 = ff5_raw[0].copy()
    ff5.index = ff5.index.to_timestamp()
    ff5 = ff5 / 100.0
    ff5.to_csv(FRENCH_OUT_DIR / "ff5_factors_monthly.csv")
    print(f"  -> Da luu {FRENCH_OUT_DIR / 'ff5_factors_monthly.csv'}  ({len(ff5)} dong)")

    print("Dang tai 25 danh muc Size-B/M (LHS portfolios, dung cho GRS test)...")
    p25_raw = web.DataReader(
        "25_Portfolios_5x5",
        "famafrench",
        start=FACTOR_TEST_START,
        end=FACTOR_TEST_END,
    )
    p25 = p25_raw[0].copy()  # bang 0 = value-weighted returns
    p25.index = p25.index.to_timestamp()
    p25 = p25 / 100.0
    p25.to_csv(FRENCH_OUT_DIR / "25_portfolios_size_bm.csv")
    print(f"  -> Da luu {FRENCH_OUT_DIR / '25_portfolios_size_bm.csv'}  ({len(p25)} dong)")

    return ff3, ff5, p25


# ---------------------------------------------------------------------------
# PHAN 2: Lay du lieu cap co phieu (US) de test ham portfolio_sort()
# Dung cho: Factor team - test logic sort 2x3 truoc khi ap dung len VN
# LUU Y: day CHI la du lieu de test CODE, khong phai du lieu dung de nop bai.
# ---------------------------------------------------------------------------

def get_stock_level_test_data():
    import yfinance as yf

    tickers = [
        "AAPL", "MSFT", "JNJ", "XOM", "GE", "KO", "PFE", "WMT",
        "CAT", "IBM", "DIS", "MCD", "CVX", "HD", "MMM", "BA",
        "AXP", "NKE", "PG", "TRV", "UNH", "VZ", "V", "JPM",
        "CSCO", "INTC", "MRK", "GS", "HON", "CRM",
    ]
    print(f"Dang tai gia {len(tickers)} ma US de test portfolio sort...")
    data = yf.download(tickers, start="2018-01-01", end="2023-01-01",
                        auto_adjust=True, progress=False)["Close"]
    data.to_csv(US_TEST_OUT_DIR / "us_test_prices.csv")
    print(f"  -> Da luu {US_TEST_OUT_DIR / 'us_test_prices.csv'}  ({data.shape})")

    # Gia lap "size" (von hoa) va "book-to-market" de test thuat toan sort.
    # Khi chuyen sang VN, hai cot nay se duoc thay bang du lieu that
    # (von hoa tu gia*so luong CP luu hanh, book value tu BCTC).
    rng = np.random.default_rng(42)
    last_price = data.iloc[-1]
    fake_shares_outstanding = pd.Series(
        rng.uniform(1e8, 5e9, size=len(tickers)), index=tickers
    )
    size_proxy = last_price * fake_shares_outstanding
    bm_proxy = pd.Series(rng.uniform(0.1, 3.0, size=len(tickers)), index=tickers)

    characteristics = pd.DataFrame({
        "size": size_proxy,
        "book_to_market": bm_proxy,
    })
    characteristics.to_csv(US_TEST_OUT_DIR / "us_test_characteristics.csv")
    print(f"  -> Da luu {US_TEST_OUT_DIR / 'us_test_characteristics.csv'} (size + B/M gia lap)")

    return data, characteristics


# ---------------------------------------------------------------------------
# PHAN 3: Ham portfolio_sort() de factor team test logic tu xay SMB/HML
# ---------------------------------------------------------------------------

def portfolio_sort(size: pd.Series, bm: pd.Series,
                    size_bp: float = 0.5,
                    bm_bp=(0.3, 0.7)) -> pd.Series:
    """
    Sort 2x3 theo dung phuong phap Fama-French: 2 nhom Size x 3 nhom B/M.
    Tra ve nhan nhom cho tung ma: SL, SN, SH, BL, BN, BH.
    """
    size_median = size.quantile(size_bp)
    bm_low, bm_high = bm.quantile(bm_bp[0]), bm.quantile(bm_bp[1])

    group = pd.Series(index=size.index, dtype="object")
    small = size <= size_median
    big = ~small

    group[small & (bm <= bm_low)] = "SL"
    group[small & (bm > bm_low) & (bm <= bm_high)] = "SN"
    group[small & (bm > bm_high)] = "SH"
    group[big & (bm <= bm_low)] = "BL"
    group[big & (bm > bm_low) & (bm <= bm_high)] = "BN"
    group[big & (bm > bm_high)] = "BH"
    return group


def compute_smb_hml(returns: pd.DataFrame, group: pd.Series) -> pd.DataFrame:
    """
    Tinh SMB, HML tu loi suat tung ma va nhan nhom da sort.
    returns: DataFrame loi suat (cot = ma co phieu, hang = thoi gian)
    group:   Series nhan nhom ung voi tung ma (index = ma co phieu)
    """
    portfolios = {}
    for label in ["SL", "SN", "SH", "BL", "BN", "BH"]:
        members = group[group == label].index
        members = [m for m in members if m in returns.columns]
        if members:
            portfolios[label] = returns[members].mean(axis=1)

    smb = (portfolios["SL"] + portfolios["SN"] + portfolios["SH"]) / 3 - \
          (portfolios["BL"] + portfolios["BN"] + portfolios["BH"]) / 3
    hml = (portfolios["SH"] + portfolios["BH"]) / 2 - \
          (portfolios["SL"] + portfolios["BL"]) / 2

    return pd.DataFrame({"SMB": smb, "HML": hml})


# ---------------------------------------------------------------------------
# PHAN 4: Regression logic dung chung code trong src/models
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# MAIN: chay thu toan bo pipeline test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    ff3, ff5, p25 = get_ff_factors()
    prices, chars = get_stock_level_test_data()

    print("\n--- TEST 1: Factor team - tu xay SMB/HML tren du lieu US test ---")
    rets = prices.pct_change().dropna()
    grp = portfolio_sort(chars["size"], chars["book_to_market"])
    own_factors = compute_smb_hml(rets, grp)
    print(own_factors.head())
    print("(Doi chieu voi ff3['SMB'], ff3['HML'] de kiem tra logic - luu y du "
          "lieu size/B/M o day la gia lap nen khong ky vong giong het.)")

    print("\n--- TEST 2: Kinh te luong team - hoi quy CAPM/FF3/FF5 ---")
    y_test = p25.iloc[:, 0]  # lay 1 trong 25 danh muc de test
    capm = run_factor_regression(y_test, ff5, ["Mkt-RF"])
    ff3_m = run_factor_regression(y_test, ff5, ["Mkt-RF", "SMB", "HML"])
    ff5_m = run_factor_regression(y_test, ff5, ["Mkt-RF", "SMB", "HML", "RMW", "CMA"])
    for name, m in [("CAPM", capm), ("FF3", ff3_m), ("FF5", ff5_m)]:
        print(f"{name}: alpha={m.params['const']:.4f}  "
              f"t={m.tvalues['const']:.2f}  R2={m.rsquared:.3f}")

    print(
        "\nHoan tat. Du lieu test da san sang trong "
        f"{FRENCH_OUT_DIR} va {US_TEST_OUT_DIR}."
    )
