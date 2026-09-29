"""Build point-in-time factors from the supplied VN100 and master-data ZIP files."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.factors.diagnostics import factor_summary  # noqa: E402
from src.factors.vn_period_pipeline import build_vn_period_factors  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Construct VN100 factors with point-in-time fundamentals."
    )
    parser.add_argument("period_archive", type=Path,
                        help="ZIP containing Top100 period CSV files")
    parser.add_argument("master_archive", type=Path,
                        help="ZIP containing the cleaned master data and RF workbooks")
    parser.add_argument("--rf-tenor", choices=["1Y", "3Y", "10Y"], default="1Y")
    parser.add_argument("--market-proxy", choices=["VNINDEX", "VN100", "VN30"],
                        default="VNINDEX")
    parser.add_argument("--weighting", choices=["formation", "lagged_market_cap"],
                        default="lagged_market_cap")
    parser.add_argument(
        "--schedule",
        choices=["annual_july", "supplied_semiannual"],
        default="annual_july",
        help="June formation/July-June or supplied six-month robustness schedule",
    )
    parser.add_argument("--include-incomplete", action="store_true",
                        help="Include incomplete holding periods such as period 18")
    parser.add_argument("--exclude-financials", action="store_true")
    parser.add_argument("--output-dir", type=Path,
                        default=ROOT / "outputs" / "vn_period_factors")
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    result, periods, event_conflicts = build_vn_period_factors(
        args.period_archive,
        args.master_archive,
        rf_tenor=args.rf_tenor,
        market_proxy=args.market_proxy,
        weighting=args.weighting,
        schedule=args.schedule,
        include_incomplete=args.include_incomplete,
        exclude_financials=args.exclude_financials,
    )

    result.factors.to_csv(args.output_dir / "vn100_factors_monthly.csv")
    factor_summary(result.factors.drop(columns=["period"], errors="ignore")).to_csv(
        args.output_dir / "vn100_factor_summary.csv"
    )
    result.factors.drop(columns=["period"], errors="ignore").corr().to_csv(
        args.output_dir / "vn100_factor_correlations.csv"
    )
    result.formation_audit.to_csv(
        args.output_dir / "vn100_formation_audit.csv", index=False
    )
    result.group_assignments.to_csv(
        args.output_dir / "vn100_group_assignments.csv", index=False
    )
    result.group_counts.to_csv(
        args.output_dir / "vn100_group_counts.csv", index=False
    )
    result.returns_panel.to_csv(
        args.output_dir / "vn100_returns_clean.csv", index=False
    )
    return_reconciliation = result.returns_panel.loc[
        result.returns_panel["reported_minus_price_return"].abs().gt(0.01)
        | result.returns_panel["price_return"].isna()
        | result.returns_panel["reported_return"].abs().gt(1.0)
        | result.returns_panel["return"].abs().gt(1.0)
    ].copy()
    return_reconciliation.to_csv(
        args.output_dir / "vn100_return_reconciliation.csv", index=False
    )
    result.data_quality.to_csv(
        args.output_dir / "vn100_data_quality.csv", index=False
    )
    periods.to_csv(args.output_dir / "vn100_periods_audit.csv", index=False)
    event_conflicts.to_csv(
        args.output_dir / "vn100_fundamental_event_conflicts.csv", index=False
    )

    print(f"Saved VN100 factor outputs to {args.output_dir}")
    print(f"Factor months: {len(result.factors)}")
    print(f"Formation rows: {len(result.formation_audit)}")
    print(f"Schedule: {args.schedule}")
    print(f"Weighting: {args.weighting}")
    print(f"Incomplete periods included: {args.include_incomplete}")


if __name__ == "__main__":
    main()
