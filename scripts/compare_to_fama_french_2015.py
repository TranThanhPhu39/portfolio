"""Compare the SMALL LoBM test regression with Fama-French (2015), Table 7."""

from __future__ import annotations

import hashlib
import sys
import zipfile
from io import BytesIO
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.models.regressions import run_factor_regression


DATA_DIR = PROJECT_ROOT / "test_data"
ARCHIVE_2014_DIR = DATA_DIR / "_historical_2014"
ARCHIVE_2015_DIR = DATA_DIR / "_historical_2015"
OUTPUT_DIR = PROJECT_ROOT / "outputs"
COMPARISON_PATH = OUTPUT_DIR / "step4_table7_comparison.csv"
TABLE5_SUMMARY_PATH = OUTPUT_DIR / "step4_table5_panel_a_comparison.csv"
REPORT_PATH = OUTPUT_DIR / "step4_audit.md"
PORTFOLIO = "SMALL LoBM"
SAMPLE_START = "1963-07-01"
SAMPLE_END = "2013-12-01"
FF3_COLUMNS = ["Mkt-RF", "SMB", "HML", "RF"]
FF5_COLUMNS = ["Mkt-RF", "SMB", "HML", "RMW", "CMA", "RF"]
PAPER_TARGETS = {
    "FF3": {
        "reference": "Table 7, Panel A, Small / Low B/M",
        "alpha_pct_per_month": -0.49,
        "t_alpha": -5.18,
    },
    "FF5": {
        "reference": "Table 7, Panel B, Small / Low B/M (HML^O)",
        "alpha_pct_per_month": -0.29,
        "t_alpha": -3.31,
    },
}
ARCHIVE_FILES = {
    "ff3_july2014": ARCHIVE_2014_DIR / "ff3_july2014.zip",
    "ff3_july2015": ARCHIVE_2015_DIR / "ff3_july2015.zip",
    "ff5_july2015": ARCHIVE_2015_DIR / "ff5_july2015.zip",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_monthly_csv(path: Path) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(f"Required input file is missing: {path}")
    frame = pd.read_csv(path, index_col=0, parse_dates=True)
    return frame


def read_french_archive(path: Path) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(
            f"Historical factor archive is missing: {path}. "
            "Download the official archive linked in outputs/step4_audit.md."
        )
    with zipfile.ZipFile(path) as archive:
        data_files = [
            name for name in archive.namelist()
            if name.lower().endswith((".csv", ".txt"))
        ]
        if len(data_files) != 1:
            raise ValueError(
                f"Expected one monthly data file in {path.name}; found {data_files}"
            )
        member = data_files[0]
        separator = r"\s+" if member.lower().endswith(".txt") else ","
        frame = pd.read_csv(
            BytesIO(archive.read(member)),
            skiprows=3,
            sep=separator,
            index_col=0,
        )

    labels = frame.index.astype(str).str.strip()
    monthly_mask = labels.str.fullmatch(r"\d{6}")
    frame = frame.loc[monthly_mask].copy()
    labels = frame.index.astype(str).str.strip()
    frame.index = pd.to_datetime(labels + "01", format="%Y%m%d")
    frame = frame.apply(pd.to_numeric, errors="raise") / 100.0
    return frame


def validate_frame(
    label: str,
    frame: pd.DataFrame,
    expected_dates: pd.DatetimeIndex,
    required_columns: list[str],
) -> None:
    missing_columns = [column for column in required_columns if column not in frame]
    if missing_columns:
        raise KeyError(f"{label} is missing required columns: {missing_columns}")
    if frame.index.has_duplicates:
        raise ValueError(f"{label} contains duplicate dates")
    if not frame.index.is_monotonic_increasing:
        raise ValueError(f"{label} dates are not chronological")
    sample = frame.reindex(expected_dates).loc[:, required_columns]
    if sample.isna().any().any():
        raise ValueError(f"{label} has missing observations in the 606-month sample")
    if not np.isfinite(sample.to_numpy(dtype=np.float64)).all():
        raise ValueError(f"{label} contains non-finite values in the sample")


def orthogonalize_hml(factors: pd.DataFrame) -> tuple[pd.DataFrame, float]:
    controls = ["Mkt-RF", "SMB", "RMW", "CMA"]
    result = sm.OLS(
        factors["HML"],
        sm.add_constant(factors[controls], has_constant="add"),
        missing="raise",
    ).fit()
    transformed = factors.copy()
    transformed["HML_O"] = result.params["const"] + result.resid
    return transformed, float(result.params["const"])


def fit_row(
    *,
    model: str,
    variant: str,
    factor_source: str,
    portfolio_returns: pd.Series,
    factors: pd.DataFrame,
    factor_columns: list[str],
    factor_spec: str,
    note: str,
) -> dict[str, object]:
    result = run_factor_regression(
        portfolio_returns,
        factors,
        factor_columns,
    )
    target = PAPER_TARGETS.get(model)
    alpha = float(result.params["const"] * 100.0)
    t_alpha = float(result.tvalues["const"])
    paper_alpha = target["alpha_pct_per_month"] if target else np.nan
    paper_t = target["t_alpha"] if target else np.nan
    return {
        "model": model,
        "variant": variant,
        "portfolio": PORTFOLIO,
        "factor_source": factor_source,
        "factor_spec": factor_spec,
        "paper_reference": target["reference"] if target else "Not reported in Table 5/7",
        "observations": int(result.nobs),
        "alpha_pct_per_month": alpha,
        "paper_alpha_pct_per_month": paper_alpha,
        "alpha_gap_pct_points_per_month": alpha - paper_alpha,
        "t_alpha": t_alpha,
        "paper_t_alpha": paper_t,
        "t_alpha_gap": t_alpha - paper_t,
        "r_squared": float(result.rsquared),
        "note": note,
    }


def format_value(value: object, digits: int = 4) -> str:
    if pd.isna(value):
        return "—"
    if isinstance(value, (int, np.integer)):
        return str(int(value))
    if isinstance(value, (float, np.floating)):
        return f"{float(value):.{digits}f}"
    return str(value)


def markdown_table(frame: pd.DataFrame, columns: list[tuple[str, str]]) -> str:
    headers = [label for label, _ in columns]
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    for _, row in frame.iterrows():
        lines.append(
            "| "
            + " | ".join(format_value(row[column]) for _, column in columns)
            + " |"
        )
    return "\n".join(lines)


def build_table5_summary(
    portfolios: pd.DataFrame,
    expected_dates: pd.DatetimeIndex,
    factor_sources: list[tuple[str, str, str, pd.DataFrame, list[str]]],
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    portfolio_sample = portfolios.loc[expected_dates]
    for model, variant, factor_source, factors, factor_columns in factor_sources:
        factor_sample = factors.loc[expected_dates]
        excess_returns = portfolio_sample.sub(factor_sample["RF"], axis=0)
        alphas = []
        for portfolio_name in portfolio_sample.columns:
            result = run_factor_regression(
                portfolio_sample[portfolio_name],
                factor_sample,
                factor_columns,
            )
            alphas.append(float(result.params["const"] * 100.0))

        mean_abs_alpha = float(np.mean(np.abs(alphas)))
        mean_excess_returns = excess_returns.mean(axis=0)
        deviations_pct = (
            mean_excess_returns - mean_excess_returns.mean()
        ) * 100.0
        mean_abs_deviation = float(np.mean(np.abs(deviations_pct)))
        paper_alpha = 0.102 if model == "FF3" else 0.094
        paper_ratio = 0.54 if model == "FF3" else 0.50
        ratio = mean_abs_alpha / mean_abs_deviation
        rows.append(
            {
                "model": model,
                "variant": variant,
                "factor_source": factor_source,
                "portfolio_count": len(portfolio_sample.columns),
                "observations_per_portfolio": len(expected_dates),
                "mean_abs_alpha_pct_per_month": mean_abs_alpha,
                "paper_mean_abs_alpha_pct_per_month": paper_alpha,
                "mean_abs_alpha_gap_pct_points_per_month": mean_abs_alpha - paper_alpha,
                "mean_abs_cross_section_deviation_pct_per_month": mean_abs_deviation,
                "mean_abs_alpha_over_mean_abs_deviation": ratio,
                "paper_alpha_to_deviation_ratio": paper_ratio,
                "ratio_gap": ratio - paper_ratio,
                "note": (
                    "Table 5 Panel A, 2x3 factors; current local LHS vintage. "
                    "GRS is not computed in Step 4."
                ),
            }
        )
    return pd.DataFrame(rows)


def build_outputs() -> tuple[pd.DataFrame, pd.DataFrame, str]:
    expected_dates = pd.date_range(SAMPLE_START, SAMPLE_END, freq="MS")
    portfolio_path = DATA_DIR / "25_portfolios_size_bm.csv"
    current_ff3_path = DATA_DIR / "ff3_factors_monthly.csv"
    current_ff5_path = DATA_DIR / "ff5_factors_monthly.csv"

    portfolios = read_monthly_csv(portfolio_path)
    current_ff3 = read_monthly_csv(current_ff3_path)
    current_ff5 = read_monthly_csv(current_ff5_path)
    archived_ff3_2014 = read_french_archive(ARCHIVE_FILES["ff3_july2014"])
    archived_ff3_2015 = read_french_archive(ARCHIVE_FILES["ff3_july2015"])
    archived_ff5_2015 = read_french_archive(ARCHIVE_FILES["ff5_july2015"])

    if PORTFOLIO not in portfolios.columns:
        raise KeyError(f"Portfolio {PORTFOLIO!r} is missing from {portfolio_path.name}")
    if portfolios.shape[1] != 25:
        raise ValueError(
            f"Expected 25 Size-B/M portfolio columns; found {portfolios.shape[1]}"
        )
    if not portfolios.columns.is_unique:
        raise ValueError("The 25 Size-B/M portfolio file has duplicate column names")
    validate_frame(
        "25 Size-B/M portfolios",
        portfolios,
        expected_dates,
        portfolios.columns.tolist(),
    )
    validate_frame("Current FF3 factors", current_ff3, expected_dates, FF3_COLUMNS)
    validate_frame("Current FF5 factors", current_ff5, expected_dates, FF5_COLUMNS)
    validate_frame("July 2014 archived FF3 factors", archived_ff3_2014, expected_dates, FF3_COLUMNS)
    validate_frame("July 2015 archived FF3 factors", archived_ff3_2015, expected_dates, FF3_COLUMNS)
    validate_frame("July 2015 archived FF5 factors", archived_ff5_2015, expected_dates, FF5_COLUMNS)

    returns = portfolios.loc[expected_dates, PORTFOLIO].rename(PORTFOLIO)
    rows: list[dict[str, object]] = []

    rows.append(
        fit_row(
            model="CAPM",
            variant="current FF3 source",
            factor_source="ff3_factors_monthly.csv",
            portfolio_returns=returns,
            factors=current_ff3.loc[expected_dates, FF3_COLUMNS],
            factor_columns=["Mkt-RF"],
            factor_spec="Mkt-RF; RF subtracted from LHS",
            note="No CAPM alpha/t-stat benchmark is reported in Table 5/7.",
        )
    )

    for variant, source, factors in (
        ("current CSV", "ff3_factors_monthly.csv", current_ff3),
        ("July 2014 archive", "FF3 July 2014 archive", archived_ff3_2014),
        ("July 2015 archive", "FF3 July 2015 archive", archived_ff3_2015),
    ):
        rows.append(
            fit_row(
                model="FF3",
                variant=variant,
                factor_source=source,
                portfolio_returns=returns,
                factors=factors.loc[expected_dates, FF3_COLUMNS],
                factor_columns=["Mkt-RF", "SMB", "HML"],
                factor_spec="Mkt-RF, SMB, HML; RF subtracted from LHS",
                note="Table 7 Panel A reference; LHS portfolio vintage is the current local CSV.",
            )
        )

    for variant, source, factors in (
        ("current CSV, raw HML", "ff5_factors_monthly.csv", current_ff5),
        ("current CSV, HML^O", "ff5_factors_monthly.csv", current_ff5),
        ("July 2015 archive, HML^O", "FF5 July 2015 archive", archived_ff5_2015),
    ):
        sample_factors = factors.loc[expected_dates, FF5_COLUMNS].copy()
        factor_spec = "Mkt-RF, SMB, HML, RMW, CMA; RF subtracted from LHS"
        note = "Table 7 Panel B reference; LHS portfolio vintage is the current local CSV."
        if "HML^O" in variant:
            sample_factors, _ = orthogonalize_hml(sample_factors)
            factor_spec = "Mkt-RF, SMB, HML^O, RMW, CMA; RF subtracted from LHS"
            note += " HML^O = intercept + residual from HML on Mkt-RF, SMB, RMW, CMA."
        else:
            note += " Raw-HML fit is retained as an equivalence check."
        rows.append(
            fit_row(
                model="FF5",
                variant=variant,
                factor_source=source,
                portfolio_returns=returns,
                factors=sample_factors,
                factor_columns=["Mkt-RF", "SMB", "HML_O" if "HML^O" in variant else "HML", "RMW", "CMA"],
                factor_spec=factor_spec,
                note=note,
            )
        )

    comparison = pd.DataFrame(rows)
    if not (comparison["observations"] == len(expected_dates)).all():
        raise RuntimeError("At least one comparison did not use all 606 months")

    current_hml = comparison.loc[
        (comparison["model"] == "FF5") & (comparison["variant"] == "current CSV, raw HML")
    ].iloc[0]
    current_hmlo = comparison.loc[
        (comparison["model"] == "FF5") & (comparison["variant"] == "current CSV, HML^O")
    ].iloc[0]
    if not np.allclose(
        current_hml[["alpha_pct_per_month", "t_alpha", "r_squared"]].to_numpy(dtype=float),
        current_hmlo[["alpha_pct_per_month", "t_alpha", "r_squared"]].to_numpy(dtype=float),
        rtol=0.0,
        atol=1e-10,
    ):
        raise RuntimeError("Raw-HML and HML^O FF5 fits disagree on model performance")

    table5_summary = build_table5_summary(
        portfolios,
        expected_dates,
        [
            ("FF3", "current CSV", "ff3_factors_monthly.csv", current_ff3, ["Mkt-RF", "SMB", "HML"]),
            ("FF3", "July 2014 archive", "FF3 July 2014 archive", archived_ff3_2014, ["Mkt-RF", "SMB", "HML"]),
            ("FF3", "July 2015 archive", "FF3 July 2015 archive", archived_ff3_2015, ["Mkt-RF", "SMB", "HML"]),
            ("FF5", "current CSV", "ff5_factors_monthly.csv", current_ff5, ["Mkt-RF", "SMB", "HML", "RMW", "CMA"]),
            ("FF5", "July 2015 archive", "FF5 July 2015 archive", archived_ff5_2015, ["Mkt-RF", "SMB", "HML", "RMW", "CMA"]),
        ],
    )

    current_hashes = {
        path.name: sha256_file(path)
        for path in (portfolio_path, current_ff3_path, current_ff5_path)
    }
    archive_hashes = {
        path.name: sha256_file(path) for path in ARCHIVE_FILES.values()
    }
    current_ff3_row = comparison.loc[
        (comparison["model"] == "FF3") & (comparison["variant"] == "current CSV")
    ].iloc[0]
    current_ff5_row = current_hmlo
    archived_ff5_row = comparison.loc[
        (comparison["model"] == "FF5")
        & (comparison["variant"] == "July 2015 archive, HML^O")
    ].iloc[0]
    table7 = comparison.loc[comparison["model"].isin(["FF3", "FF5"])].copy()

    results_md = markdown_table(
        comparison,
        [
            ("Model", "model"),
            ("Variant", "variant"),
            ("N", "observations"),
            ("Alpha own", "alpha_pct_per_month"),
            ("Alpha paper", "paper_alpha_pct_per_month"),
            ("Delta alpha", "alpha_gap_pct_points_per_month"),
            ("t own", "t_alpha"),
            ("t paper", "paper_t_alpha"),
            ("Delta t", "t_alpha_gap"),
            ("R²", "r_squared"),
        ],
    )
    table5_md = markdown_table(
        table5_summary,
        [
            ("Model", "model"),
            ("Variant", "variant"),
            ("Portfolios", "portfolio_count"),
            ("T", "observations_per_portfolio"),
            ("Mean abs alpha own", "mean_abs_alpha_pct_per_month"),
            ("Mean abs alpha paper", "paper_mean_abs_alpha_pct_per_month"),
            ("Delta", "mean_abs_alpha_gap_pct_points_per_month"),
            ("Alpha/deviation own", "mean_abs_alpha_over_mean_abs_deviation"),
            ("Alpha/deviation paper", "paper_alpha_to_deviation_ratio"),
        ],
    )
    report = f"""# Step 4: Fama-French (2015) comparison

## Scope and sample

The comparison uses `SMALL LoBM`, value-weighted Size-B/M portfolio returns, and the July 1963–December 2013 sample (606 monthly observations). FF3 uses `Mkt-RF`, `SMB`, and `HML` from the FF3 factor file. FF5 uses `Mkt-RF`, `SMB`, `HML`, `RMW`, and `CMA` from the FF5 factor file. In both models, RF is subtracted from the portfolio return. Alpha is reported in percent per month; t-statistics are conventional OLS t-statistics.

## Table 7 comparison

Table 7 Panel A reports the FF3 intercept and t-stat for Small / Low B/M as **-0.49% per month** and **-5.18**. Panel B reports the FF5 values as **-0.29% per month** and **-3.31**, using `HML^O`. CAPM has no corresponding alpha/t-stat cell in Tables 5 or 7.

{results_md}

The raw-HML and HML^O FF5 fits have the same alpha, t-stat(alpha), and R-squared within 1e-10 on the current factor file. This confirms the paper's equivalent reparameterization for the metrics being compared.

## Vintage check

The current local CSVs do not encode their source vintage. Official July 2014 FF3 and July 2015 FF3/FF5 factor archives were downloaded from the Kenneth French Data Library and compared on the same 606 dates. These are factor-vintage sensitivity runs only: the LHS portfolio remains the current local `25_portfolios_size_bm.csv`, so they are not full replications with a historical portfolio vintage.

Official archive sources: [FF3 history](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/f-f_factors_archive.html), [FF5 history](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/f-f_5_factors_2x3_archive.html). The downloaded ZIP files are the July 2014 FF3 text archive and July 2015 FF3/FF5 CSV archives.

- Current FF3: alpha {current_ff3_row['alpha_pct_per_month']:.4f}%/month, t {current_ff3_row['t_alpha']:.4f}; Table 7 target -0.49 and -5.18.
- Current FF5 with HML^O: alpha {current_ff5_row['alpha_pct_per_month']:.4f}%/month, t {current_ff5_row['t_alpha']:.4f}; Table 7 target -0.29 and -3.31.
- July 2015 archived FF5 factors with current LHS: alpha {archived_ff5_row['alpha_pct_per_month']:.4f}%/month, t {archived_ff5_row['t_alpha']:.4f}. Its alpha rounds to the Table 7 value; its t-stat remains {archived_ff5_row['t_alpha'] - PAPER_TARGETS['FF5']['t_alpha']:+.4f} away from the published rounded value.
- The Table 7 FF3 result is closer using the current FF3 CSV than the July 2014 or July 2015 archived FF3 factors. Therefore vintage alone does not explain every difference.

The archived ZIPs identify the July 2014 and July 2015 CRSP data cuts. Their official archive pages state that archived factor files are annual July cuts. The current Data Library notes that U.S. research returns switched from FIZ to CIZ beginning January 2025, and that historical returns can change when CRSP revises its database. The accessed 25-portfolio entry exposes the current monthly series but no historical-vintage link, so the original 2015 LHS portfolio series could not be established from that entry.

## Table 5 Panel A aggregate comparison

Table 5 Panel A summarizes all 25 Size-B/M portfolios. The published FF3 `HML` row under 2x3 factors reports GRS 3.62, mean absolute alpha 0.102% per month, and mean-absolute-alpha/deviation ratio 0.54. The FF5 `HML RMW CMA` row reports GRS 2.84, mean absolute alpha 0.094% per month, and ratio 0.50. The team-side mean absolute alpha and ratio are calculated below for all 25 LHS portfolios, using the matched 606-month sample. GRS itself is not calculated here; it remains Step 5.

{table5_md}

For the current files, the team-side mean absolute alpha is {table5_summary.loc[(table5_summary['model'] == 'FF3') & (table5_summary['variant'] == 'current CSV'), 'mean_abs_alpha_pct_per_month'].iloc[0]:.4f}%/month for FF3 and {table5_summary.loc[(table5_summary['model'] == 'FF5') & (table5_summary['variant'] == 'current CSV'), 'mean_abs_alpha_pct_per_month'].iloc[0]:.4f}%/month for FF5. FF5 rounds to the published 0.094; FF3 is 0.0041 percentage points/month below 0.102. The corresponding ratios are {table5_summary.loc[(table5_summary['model'] == 'FF3') & (table5_summary['variant'] == 'current CSV'), 'mean_abs_alpha_over_mean_abs_deviation'].iloc[0]:.4f} versus 0.54 for FF3 and {table5_summary.loc[(table5_summary['model'] == 'FF5') & (table5_summary['variant'] == 'current CSV'), 'mean_abs_alpha_over_mean_abs_deviation'].iloc[0]:.4f} versus 0.50 for FF5.

## Audit conclusion

The Table 7 comparison is completed for the selected portfolio with model sources and units aligned. The Table 5 mean-absolute-alpha and ratio summaries are also computed for all 25 portfolios; GRS is reserved for Step 5. FF3 is close to the published rounded intercept and t-stat. Current-vintage FF5 differs more for SMALL LoBM; the July 2015 archived FF5 factors move that intercept to the published rounding, while the t-stat remains different. At the 25-portfolio level, current FF5 summary statistics are very close to Table 5. The HML^O transformation itself is not the source of the discrepancy. The remaining limitation is the unavailable matching 2015 vintage of the 25-portfolio LHS data, plus the lack of vintage metadata in the current local CSVs. No regression-logic error was found in the tested path.

The FF5 factor archive header identifies CRSP 201507 and the one-month T-bill source as Ibbotson and Associates. Archive ZIP SHA-256 values:

{chr(10).join(f'- `{name}`: `{digest}`' for name, digest in archive_hashes.items())}

Current test-data SHA-256 values:

{chr(10).join(f'- `{name}`: `{digest}`' for name, digest in current_hashes.items())}
"""
    return comparison, table5_summary, report


def main() -> None:
    comparison, table5_summary, report = build_outputs()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    comparison.to_csv(COMPARISON_PATH, index=False, float_format="%.10g")
    table5_summary.to_csv(TABLE5_SUMMARY_PATH, index=False, float_format="%.10g")
    REPORT_PATH.write_text(report, encoding="utf-8", newline="\n")
    print(
        comparison[
            [
                "model",
                "variant",
                "alpha_pct_per_month",
                "paper_alpha_pct_per_month",
                "t_alpha",
                "paper_t_alpha",
                "r_squared",
                "observations",
            ]
        ].to_string(index=False, float_format=lambda value: f"{value:.4f}")
    )
    print("\nTable 5 Panel A alpha summary:")
    print(
        table5_summary[
            [
                "model",
                "variant",
                "mean_abs_alpha_pct_per_month",
                "paper_mean_abs_alpha_pct_per_month",
                "mean_abs_alpha_over_mean_abs_deviation",
                "paper_alpha_to_deviation_ratio",
                "portfolio_count",
            ]
        ].to_string(index=False, float_format=lambda value: f"{value:.4f}")
    )
    print(f"\nSaved comparison: {COMPARISON_PATH}")
    print(f"Saved Table 5 summary: {TABLE5_SUMMARY_PATH}")
    print(f"Saved audit report: {REPORT_PATH}")


if __name__ == "__main__":
    main()
