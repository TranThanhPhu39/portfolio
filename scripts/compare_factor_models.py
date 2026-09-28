"""Compare CAPM, FF3, and FF5 using each model's Kenneth French factor file."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.models.regressions import run_factor_regression


DATA_DIR = PROJECT_ROOT / "data" / "test" / "kenneth_french"
OUTPUT_PATH = PROJECT_ROOT / "outputs" / "step3_model_comparison.csv"
PORTFOLIO = "SMALL LoBM"
FF3_COLUMNS = ["Mkt-RF", "SMB", "HML", "RF"]
FF5_COLUMNS = ["Mkt-RF", "SMB", "HML", "RMW", "CMA", "RF"]
MODEL_SPECS = (
    ("CAPM", "ff3", "ff3_factors_monthly.csv", ["Mkt-RF"]),
    ("FF3", "ff3", "ff3_factors_monthly.csv", ["Mkt-RF", "SMB", "HML"]),
    ("FF5", "ff5", "ff5_factors_monthly.csv", ["Mkt-RF", "SMB", "HML", "RMW", "CMA"]),
)


def build_comparison_table() -> pd.DataFrame:
    portfolio_path = DATA_DIR / "25_portfolios_size_bm.csv"
    ff3_path = DATA_DIR / "ff3_factors_monthly.csv"
    ff5_path = DATA_DIR / "ff5_factors_monthly.csv"
    missing_files = [
        path for path in (portfolio_path, ff3_path, ff5_path) if not path.is_file()
    ]
    if missing_files:
        missing = ", ".join(str(path) for path in missing_files)
        raise FileNotFoundError(f"Required test data files are missing: {missing}")

    portfolios = pd.read_csv(portfolio_path, index_col=0, parse_dates=True)
    ff3 = pd.read_csv(ff3_path, index_col=0, parse_dates=True)
    ff5 = pd.read_csv(ff5_path, index_col=0, parse_dates=True)
    if PORTFOLIO not in portfolios.columns:
        raise KeyError(f"Portfolio {PORTFOLIO!r} is not in {portfolio_path.name}")

    for label, frame in (
        ("portfolios", portfolios),
        ("FF3 factors", ff3),
        ("FF5 factors", ff5),
    ):
        if frame.index.has_duplicates:
            raise ValueError(f"{label} input contains duplicate dates")
    for label, frame, required in (
        ("FF3", ff3, FF3_COLUMNS),
        ("FF5", ff5, FF5_COLUMNS),
    ):
        missing = [column for column in required if column not in frame.columns]
        if missing:
            raise KeyError(f"Required {label} factor columns are missing: {missing}")

    common = pd.concat(
        [
            portfolios[[PORTFOLIO]],
            ff3.reindex(columns=FF3_COLUMNS).add_prefix("ff3__"),
            ff5.reindex(columns=FF5_COLUMNS).add_prefix("ff5__"),
        ],
        axis=1,
        join="inner",
    ).sort_index().dropna()
    expected_dates = pd.date_range("1963-07-01", "2013-12-01", freq="MS")
    if not common.index.equals(expected_dates):
        raise ValueError(
            "Expected 606 consecutive month-start observations from 1963-07 through "
            f"2013-12; found {len(common)} observations from {common.index.min()} "
            f"through {common.index.max()}"
        )
    if common.index.has_duplicates:
        raise ValueError("The aligned monthly sample contains duplicate dates")
    if not common.index.is_monotonic_increasing:
        raise ValueError("The aligned monthly sample is not chronological")
    if not np.isfinite(common.to_numpy(dtype=np.float64)).all():
        raise ValueError("The aligned monthly sample contains non-finite values")

    portfolio_returns = common[PORTFOLIO]
    rows = []
    for model_name, source, factor_file, factor_cols in MODEL_SPECS:
        factor_names = [*factor_cols, "RF"]
        factor_data = common[[f"{source}__{name}" for name in factor_names]].copy()
        factor_data.columns = factor_names
        result = run_factor_regression(portfolio_returns, factor_data, factor_cols)
        rows.append(
            {
                "model": model_name,
                "portfolio": PORTFOLIO,
                "factor_file": factor_file,
                "alpha_pct_per_month": float(result.params["const"] * 100.0),
                "t_alpha": float(result.tvalues["const"]),
                "r_squared": float(result.rsquared),
                "observations": int(result.nobs),
            }
        )

    table = pd.DataFrame(rows)
    r_squared = table["r_squared"].to_numpy(dtype=np.float64)
    if np.any(np.diff(r_squared) <= 0.0):
        raise RuntimeError(
            "In-sample R-squared did not strictly increase CAPM -> FF3 -> FF5"
        )
    if not (table["observations"] == len(common)).all():
        raise RuntimeError("Model runs did not use the same aligned sample")
    return table


def main() -> None:
    table = build_comparison_table()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(OUTPUT_PATH, index=False, float_format="%.10g")

    display = table.rename(
        columns={
            "model": "Model",
            "portfolio": "LHS portfolio",
            "factor_file": "Factor source",
            "alpha_pct_per_month": "Alpha (%/month)",
            "t_alpha": "t-stat(alpha)",
            "r_squared": "R-squared",
            "observations": "N",
        }
    )
    print(display.to_string(index=False, float_format=lambda value: f"{value:.4f}"))
    print(f"\nSaved comparison table: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
