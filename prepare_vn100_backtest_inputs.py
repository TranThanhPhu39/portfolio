"""Build generic dynamic-backtest inputs from the versioned VN period outputs."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(source_dir, output_dir):
    source_dir = Path(source_dir).resolve()
    output_dir = Path(output_dir).resolve()
    if output_dir.exists():
        raise FileExistsError("Choose a new output directory.")

    returns_path = source_dir / "vn100_returns_clean.csv"
    factors_path = source_dir / "vn100_factors_monthly.csv"
    if not returns_path.exists() or not factors_path.exists():
        raise FileNotFoundError("Required VN period outputs are missing.")

    raw = pd.read_csv(returns_path, parse_dates=["date"])
    required = {"date", "ticker", "return", "return_source", "VNINDEX", "VN30"}
    if not required.issubset(raw.columns):
        raise ValueError(f"Missing columns: {sorted(required - set(raw.columns))}")
    if raw.duplicated(["date", "ticker"]).any():
        raise ValueError("Duplicate date/ticker observations.")
    values = pd.to_numeric(raw["return"], errors="raise")
    if not np.isfinite(values).all() or (values <= -1).any():
        raise ValueError("Invalid stock returns.")

    dates = pd.Index(sorted(raw["date"].unique()), name="date")
    if not np.all(np.diff(dates.to_period("M").asi8) == 1):
        raise ValueError("The stock panel has a missing calendar month.")
    tickers = pd.Index(sorted(raw["ticker"].unique()), name="ticker")

    present = raw.assign(member=True).set_index(["date", "ticker"])["member"]
    full_index = pd.MultiIndex.from_product([dates, tickers], names=["date", "ticker"])
    membership = present.reindex(full_index, fill_value=False).rename("member").reset_index()

    def unique_market(column):
        counts = raw.groupby("date")[column].nunique(dropna=False)
        if counts.ne(1).any():
            raise ValueError(f"Conflicting {column} observations by month.")
        series = raw.groupby("date")[column].first().reindex(dates)
        if not np.isfinite(series.to_numpy(float)).all() or (series <= -1).any():
            raise ValueError(f"Invalid {column} returns.")
        return series

    vnindex = unique_market("VNINDEX")
    vn30 = unique_market("VN30")
    factors = pd.read_csv(factors_path, parse_dates=["Date"]).set_index("Date")
    rf = factors["RF"].reindex(dates)
    if not np.isfinite(rf.to_numpy(float)).all() or (rf <= -1).any():
        raise ValueError("RF does not cover the stock-return dates.")

    output_dir.mkdir(parents=True)
    raw[["date", "ticker", "return"]].sort_values(["date", "ticker"]).to_csv(
        output_dir / "returns.csv", index=False
    )
    membership.to_csv(output_dir / "membership.csv", index=False)
    vnindex.rename("return").to_csv(output_dir / "benchmark_vnindex.csv")
    vn30.rename("return").to_csv(output_dir / "benchmark_vn30.csv")
    rf.rename("rf_return").to_csv(output_dir / "risk_free.csv")

    member_counts = raw.groupby("date")["ticker"].nunique()
    metadata = {
        "status": "EXPLORATORY_SOURCE_ARCHIVE_NOT_PRESENT",
        "source_files": {
            str(returns_path): sha256(returns_path),
            str(factors_path): sha256(factors_path),
        },
        "date_start": str(dates.min().date()),
        "date_end": str(dates.max().date()),
        "months": len(dates),
        "assets_union": len(tickers),
        "members_per_month_min": int(member_counts.min()),
        "members_per_month_max": int(member_counts.max()),
        "return_basis": "close_eom; reported_return fallback where price return unavailable",
        "reported_return_fallbacks": int(raw["return_source"].eq("reported_fallback").sum()),
        "rf_basis": "effective monthly return converted from supplied annual 1Y government yield",
        "benchmarks": ["VNINDEX", "VN30"],
    }
    (output_dir / "preparation_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(metadata, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        default="outputs/vn_period_factors",
        help="Directory containing versioned VN period outputs.",
    )
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    prepare(args.source, args.output)
