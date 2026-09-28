"""Run tasks 2--6 on the downloaded US test data.

Profitability and investment below are deterministic test fixtures only.
"""

from pathlib import Path
import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.factors import (  # noqa: E402
    compare_factors,
    compute_cma,
    compute_rmw,
    compute_smb_hml,
    factor_summary,
    portfolio_sort,
)


def main() -> None:
    data_dir = ROOT / "test_data"
    output_dir = ROOT / "outputs" / "factor_demo"
    output_dir.mkdir(parents=True, exist_ok=True)

    prices = pd.read_csv(data_dir / "us_test_prices.csv", index_col=0, parse_dates=True)
    characteristics = pd.read_csv(data_dir / "us_test_characteristics.csv", index_col=0)
    ff3 = pd.read_csv(data_dir / "ff3_factors_monthly.csv", index_col=0, parse_dates=True)
    ff5 = pd.read_csv(data_dir / "ff5_factors_monthly.csv", index_col=0, parse_dates=True)

    monthly_returns = prices.resample("ME").last().pct_change(fill_method=None).dropna(how="all")
    characteristics = characteristics.reindex(monthly_returns.columns)
    groups = portfolio_sort(characteristics["size"], characteristics["book_to_market"])
    assert len(groups) == len(characteristics) and groups.notna().all()
    groups.rename("group").to_csv(output_dir / "us_test_2x3_groups.csv")

    own_ff3 = compute_smb_hml(monthly_returns, groups, weights=characteristics["size"])

    rng = np.random.default_rng(20260928)
    op = pd.Series(rng.uniform(-0.1, 0.5, len(groups)), index=groups.index)
    investment = pd.Series(rng.uniform(-0.2, 0.6, len(groups)), index=groups.index)
    own_ff5 = own_ff3.assign(
        RMW=compute_rmw(monthly_returns, characteristics["size"], op,
                        characteristics["size"]),
        CMA=compute_cma(monthly_returns, characteristics["size"], investment,
                        characteristics["size"]),
    )
    own_ff5.to_csv(output_dir / "us_test_factors_monthly.csv")
    factor_summary(own_ff5).to_csv(output_dir / "us_test_factor_summary.csv")
    comparison = compare_factors(own_ff3, ff3)
    comparison.to_csv(output_dir / "ff3_comparison.csv")
    compare_factors(own_ff5[["RMW", "CMA"]], ff5).to_csv(
        output_dir / "ff5_extension_comparison.csv"
    )

    own_plot = own_ff3.copy()
    own_plot.index = own_plot.index.to_period("M")
    ref_plot = ff3[["SMB", "HML"]].copy()
    ref_plot.index = ref_plot.index.to_period("M")
    aligned = own_plot.join(ref_plot, how="inner", lsuffix=" (own)", rsuffix=" (KF)")
    aligned.index = aligned.index.to_timestamp()
    axes = aligned.plot(subplots=True, figsize=(10, 8), grid=True, title="Own vs Kenneth French")
    axes[-1].set_xlabel("Month")
    plt.tight_layout()
    plt.savefig(output_dir / "own_vs_kenneth_french.png", dpi=180)
    plt.close()

    print(f"Saved task 2--6 outputs to {output_dir}")
    print("\n2x3 group counts:")
    print(groups.value_counts().sort_index().to_string())
    print("\nFF3 comparison (test data only):")
    print(comparison.to_string(float_format=lambda x: f"{x:.4f}"))


if __name__ == "__main__":
    main()
