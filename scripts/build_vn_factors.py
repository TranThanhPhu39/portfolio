"""CLI entry point for task 7 once the processed VN100 panel is available."""

from pathlib import Path
import argparse
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.factors.diagnostics import factor_summary  # noqa: E402
from src.factors.vn_pipeline import construct_vn_factors  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_csv", type=Path)
    parser.add_argument("--output-dir", type=Path,
                        default=ROOT / "outputs" / "vn_factors")
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    panel = pd.read_csv(args.input_csv)
    factors, audit = construct_vn_factors(panel)
    factors.to_csv(args.output_dir / "vn100_factors_monthly.csv")
    factor_summary(factors).to_csv(args.output_dir / "vn100_factor_summary.csv")
    factors.corr().to_csv(args.output_dir / "vn100_factor_correlations.csv")
    audit.to_csv(args.output_dir / "vn100_eligibility_audit.csv", index=False)
    print(f"Saved VN100 factor outputs to {args.output_dir}")


if __name__ == "__main__":
    main()
