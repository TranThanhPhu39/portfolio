"""Run joint GRS tests for the Kenneth French 25 Size-B/M portfolios."""

from __future__ import annotations

import hashlib
import sys
import zipfile
from io import BytesIO
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.models.grs_test import GRSResult, grs_test


DATA_DIR = PROJECT_ROOT / "test_data"
OUTPUT_DIR = PROJECT_ROOT / "outputs"
RESULTS_PATH = OUTPUT_DIR / "step5_grs_results.csv"
REPORT_PATH = OUTPUT_DIR / "step5_grs_audit.md"
SAMPLE_START = "1963-07-01"
SAMPLE_END = "2013-12-01"
PORTFOLIO_PATH = DATA_DIR / "25_portfolios_size_bm.csv"
FF3_PATH = DATA_DIR / "ff3_factors_monthly.csv"
FF5_PATH = DATA_DIR / "ff5_factors_monthly.csv"
ARCHIVES = (
    (
        "FF3",
        "July 2014 archive sensitivity",
        DATA_DIR / "_historical_2014" / "ff3_july2014.zip",
        ["Mkt-RF", "SMB", "HML"],
        3.62,
    ),
    (
        "FF3",
        "July 2015 archive sensitivity",
        DATA_DIR / "_historical_2015" / "ff3_july2015.zip",
        ["Mkt-RF", "SMB", "HML"],
        3.62,
    ),
    (
        "FF5",
        "July 2015 archive sensitivity",
        DATA_DIR / "_historical_2015" / "ff5_july2015.zip",
        ["Mkt-RF", "SMB", "HML", "RMW", "CMA"],
        2.84,
    ),
)
CURRENT_MODELS = (
    (
        "CAPM",
        "current CSV",
        FF3_PATH,
        ["Mkt-RF"],
        None,
    ),
    (
        "FF3",
        "current CSV",
        FF3_PATH,
        ["Mkt-RF", "SMB", "HML"],
        3.62,
    ),
    (
        "FF5",
        "current CSV",
        FF5_PATH,
        ["Mkt-RF", "SMB", "HML", "RMW", "CMA"],
        2.84,
    ),
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_monthly_csv(path: Path) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(f"Required input file is missing: {path}")
    return pd.read_csv(path, index_col=0, parse_dates=True)


def read_french_archive(path: Path) -> pd.DataFrame:
    with zipfile.ZipFile(path) as archive:
        members = [
            name for name in archive.namelist()
            if name.lower().endswith((".csv", ".txt"))
        ]
        if len(members) != 1:
            raise ValueError(
                f"Expected one factor data file in {path.name}; found {members}"
            )
        member = members[0]
        separator = r"\s+" if member.lower().endswith(".txt") else ","
        frame = pd.read_csv(
            BytesIO(archive.read(member)),
            skiprows=3,
            sep=separator,
            index_col=0,
        )
    labels = frame.index.astype(str).str.strip()
    frame = frame.loc[labels.str.fullmatch(r"\d{6}")].copy()
    labels = frame.index.astype(str).str.strip()
    frame.index = pd.to_datetime(labels + "01", format="%Y%m%d")
    return frame.apply(pd.to_numeric, errors="raise") / 100.0


def validate_sample(
    label: str,
    frame: pd.DataFrame,
    expected_dates: pd.DatetimeIndex,
    required_columns: list[str],
) -> pd.DataFrame:
    missing_columns = [column for column in required_columns if column not in frame]
    if missing_columns:
        raise KeyError(f"{label} is missing columns: {missing_columns}")
    if frame.index.has_duplicates:
        raise ValueError(f"{label} contains duplicate dates")
    if not frame.index.is_monotonic_increasing:
        raise ValueError(f"{label} dates are not chronological")
    sample = frame.reindex(expected_dates).loc[:, required_columns]
    if sample.isna().any().any():
        raise ValueError(f"{label} has missing data in the required 606-month sample")
    if not np.isfinite(sample.to_numpy(dtype=np.float64)).all():
        raise ValueError(f"{label} has non-finite data in the required sample")
    return sample


def independent_mle_grs(
    returns: pd.DataFrame,
    factor_data: pd.DataFrame,
    factor_cols: list[str],
) -> tuple[float, np.ndarray]:
    """Recompute GRS via matrix OLS and the equivalent MLE-covariance form."""
    observations, n_portfolios = returns.shape
    n_factors = len(factor_cols)
    factor_matrix = factor_data.loc[:, factor_cols].to_numpy(dtype=np.float64)
    excess_returns = returns.sub(factor_data["RF"], axis=0).to_numpy(dtype=np.float64)
    design = np.column_stack([np.ones(observations), factor_matrix])
    if np.linalg.matrix_rank(design) != n_factors + 1:
        raise ValueError("Independent GRS check found a rank-deficient factor design")

    coefficients = np.linalg.lstsq(design, excess_returns, rcond=None)[0]
    residuals = excess_returns - design @ coefficients
    alpha = coefficients[0, :]
    residual_covariance_mle = residuals.T @ residuals / observations
    factor_mean = factor_matrix.mean(axis=0)
    centered_factors = factor_matrix - factor_mean
    factor_covariance = centered_factors.T @ centered_factors / (observations - 1)
    try:
        alpha_quadratic = float(
            alpha @ np.linalg.solve(residual_covariance_mle, alpha)
        )
        factor_sharpe_squared = float(
            factor_mean @ np.linalg.solve(factor_covariance, factor_mean)
        )
    except np.linalg.LinAlgError as exc:
        raise ValueError("Independent GRS check found a singular covariance") from exc

    denominator_df = observations - n_portfolios - n_factors
    statistic = (
        denominator_df
        / n_portfolios
        * alpha_quadratic
        / (1.0 + factor_sharpe_squared)
    )
    if not np.isfinite(statistic) or statistic < 0.0:
        raise ArithmeticError("Independent GRS statistic is invalid")
    return float(statistic), alpha


def run_one(
    *,
    model: str,
    variant: str,
    factor_source: str,
    returns: pd.DataFrame,
    factor_data: pd.DataFrame,
    factor_cols: list[str],
    paper_grs: float | None,
    note: str,
) -> tuple[dict[str, object], GRSResult]:
    result = grs_test(returns, factor_data, factor_cols)
    independent_statistic, independent_alphas = independent_mle_grs(
        returns,
        factor_data,
        factor_cols,
    )
    independent_statistic_gap = abs(result.statistic - independent_statistic)
    independent_alpha_gap = float(
        np.max(np.abs(result.alphas.to_numpy(dtype=np.float64) - independent_alphas))
    )
    if independent_statistic_gap > 1e-10 or independent_alpha_gap > 1e-10:
        raise RuntimeError(
            f"Independent GRS verification failed for {model}/{variant}: "
            f"statistic gap={independent_statistic_gap:.3g}, "
            f"alpha gap={independent_alpha_gap:.3g}"
        )
    expected_df_den = result.observations - result.n_portfolios - result.n_factors
    if result.numerator_df != 25 or result.denominator_df != expected_df_den:
        raise RuntimeError(f"Unexpected GRS degrees of freedom for {model}/{variant}")
    if result.observations != len(returns):
        raise RuntimeError(f"{model}/{variant} did not use every aligned input date")
    return (
        {
            "model": model,
            "variant": variant,
            "factor_source": factor_source,
            "factor_columns": ", ".join(factor_cols),
            "observations": result.observations,
            "n_portfolios": result.n_portfolios,
            "n_factors": result.n_factors,
            "df_numerator": result.numerator_df,
            "df_denominator": result.denominator_df,
            "grs_statistic": result.statistic,
            "p_value": result.p_value,
            "independent_grs_statistic": independent_statistic,
            "independent_grs_abs_gap": independent_statistic_gap,
            "independent_alpha_max_abs_gap": independent_alpha_gap,
            "paper_grs_reference": paper_grs if paper_grs is not None else np.nan,
            "grs_gap": result.statistic - paper_grs if paper_grs is not None else np.nan,
            "factor_sharpe_squared": result.factor_sharpe_squared,
            "note": note,
        },
        result,
    )


def format_number(
    value: object,
    *,
    column: str,
    digits: int = 4,
) -> str:
    if pd.isna(value):
        return "—"
    if isinstance(value, (int, np.integer)):
        return str(int(value))
    if isinstance(value, (float, np.floating)):
        if column in {"p_value", "independent_grs_abs_gap", "independent_alpha_max_abs_gap"}:
            return f"{float(value):.6g}"
        return f"{float(value):.{digits}f}"
    return str(value)


def markdown_table(
    frame: pd.DataFrame,
    columns: list[tuple[str, str]],
) -> str:
    headings = [label for label, _ in columns]
    lines = [
        "| " + " | ".join(headings) + " |",
        "|" + "|".join(["---"] * len(headings)) + "|",
    ]
    for _, row in frame.iterrows():
        lines.append(
            "| "
            + " | ".join(
                format_number(row[column], column=column) for _, column in columns
            )
            + " |"
        )
    return "\n".join(lines)


def build_outputs() -> tuple[pd.DataFrame, str]:
    expected_dates = pd.date_range(SAMPLE_START, SAMPLE_END, freq="MS")
    portfolios = read_monthly_csv(PORTFOLIO_PATH)
    ff3 = read_monthly_csv(FF3_PATH)
    ff5 = read_monthly_csv(FF5_PATH)
    if portfolios.shape[1] != 25:
        raise ValueError(f"Expected 25 portfolio columns; found {portfolios.shape[1]}")
    if not portfolios.columns.is_unique:
        raise ValueError("The 25-portfolio file has duplicate column names")
    if not ff3.columns.is_unique or not ff5.columns.is_unique:
        raise ValueError("Factor files must have unique column names")

    p25_sample = validate_sample(
        "25 Size-B/M portfolios",
        portfolios,
        expected_dates,
        portfolios.columns.tolist(),
    )
    ff3_sample = validate_sample(
        "FF3 factors", ff3, expected_dates, ["Mkt-RF", "SMB", "HML", "RF"]
    )
    ff5_sample = validate_sample(
        "FF5 factors",
        ff5,
        expected_dates,
        ["Mkt-RF", "SMB", "HML", "RMW", "CMA", "RF"],
    )

    rows: list[dict[str, object]] = []
    for model, variant, path, factor_cols, paper_grs in CURRENT_MODELS:
        factor_sample = ff3_sample if path == FF3_PATH else ff5_sample
        row, _ = run_one(
            model=model,
            variant=variant,
            factor_source=path.name,
            returns=p25_sample,
            factor_data=factor_sample,
            factor_cols=factor_cols,
            paper_grs=paper_grs,
            note=(
                "Table 5 Panel A reference applies to the published FF3/FF5 row."
                if paper_grs is not None
                else "CAPM has no corresponding Table 5 GRS reference."
            ),
        )
        rows.append(row)

    archive_hashes: dict[str, str] = {}
    sensitivity_notes: list[str] = []
    for model, variant, archive_path, factor_cols, paper_grs in ARCHIVES:
        if not archive_path.is_file():
            sensitivity_notes.append(
                f"Skipped {variant}: local archive is absent at {archive_path}."
            )
            continue
        archived = read_french_archive(archive_path)
        required = ["Mkt-RF", "SMB", "HML", "RF"]
        if model == "FF5":
            required = [*required[:-1], "RMW", "CMA", "RF"]
        archived_sample = validate_sample(
            variant,
            archived,
            expected_dates,
            required,
        )
        row, _ = run_one(
            model=model,
            variant=variant,
            factor_source=f"official archive ZIP: {archive_path.name}",
            returns=p25_sample,
            factor_data=archived_sample,
            factor_cols=factor_cols,
            paper_grs=paper_grs,
            note="Factor-vintage sensitivity only; LHS remains the current local 25-portfolio file.",
        )
        rows.append(row)
        archive_hashes[archive_path.name] = sha256_file(archive_path)

    results = pd.DataFrame(rows)
    if not (results["observations"] == len(expected_dates)).all():
        raise RuntimeError("At least one GRS run did not use all 606 months")
    if not (results["n_portfolios"] == 25).all():
        raise RuntimeError("At least one GRS run did not include all 25 portfolios")
    if (results["p_value"].isna() | (results["p_value"] < 0) | (results["p_value"] > 1)).any():
        raise RuntimeError("At least one GRS p-value is outside [0, 1]")

    current_hashes = {
        path.name: sha256_file(path) for path in (PORTFOLIO_PATH, FF3_PATH, FF5_PATH)
    }
    current_ff3 = results.loc[
        (results["model"] == "FF3") & (results["variant"] == "current CSV")
    ].iloc[0]
    current_ff5 = results.loc[
        (results["model"] == "FF5") & (results["variant"] == "current CSV")
    ].iloc[0]
    archived_ff5_rows = results.loc[
        (results["model"] == "FF5")
        & (results["variant"] == "July 2015 archive sensitivity")
    ]
    if archived_ff5_rows.empty:
        archived_ff5_note = "No local July 2015 FF5 archive was available for sensitivity analysis."
    else:
        archived_ff5 = archived_ff5_rows.iloc[0]
        archived_ff5_note = (
            f"The July 2015 FF5 factor sensitivity yields GRS "
            f"{archived_ff5['grs_statistic']:.4f}, a gap of "
            f"{archived_ff5['grs_gap']:+.4f} from Table 5; its LHS is still the current local file."
        )
    max_independent_grs_gap = float(results["independent_grs_abs_gap"].max())
    max_independent_alpha_gap = float(results["independent_alpha_max_abs_gap"].max())
    results_md = markdown_table(
        results,
        [
            ("Model", "model"),
            ("Variant", "variant"),
            ("T", "observations"),
            ("N", "n_portfolios"),
            ("K", "n_factors"),
            ("F numerator df", "df_numerator"),
            ("F denominator df", "df_denominator"),
            ("GRS", "grs_statistic"),
            ("p-value", "p_value"),
            ("Independent GRS gap", "independent_grs_abs_gap"),
            ("Table 5 GRS", "paper_grs_reference"),
            ("Gap", "grs_gap"),
        ],
    )
    sensitivity_text = "\n".join(f"- {line}" for line in sensitivity_notes) or "- All locally available archive sensitivities were run."
    archive_hash_text = (
        "\n".join(f"- `{name}`: `{digest}`" for name, digest in archive_hashes.items())
        or "- No archive ZIPs were used."
    )
    report = f"""# Step 5: GRS joint-alpha test

## Inputs and alignment

The test uses all 25 value-weighted Size-B/M portfolio returns and the same FF3/FF5 factor sources as Step 4. The current input files contain 606 complete month-start observations from July 1963 through December 2013. RF is subtracted from every raw portfolio return; the published Mkt-RF series is already an excess-return factor and is not adjusted a second time.

## Method

The null is that all 25 intercepts are jointly zero. For each factor specification, the runner fits 25 OLS equations on the same dates, obtains the intercept vector and residual matrix, and evaluates:

`GRS = (T/N) * ((T-N-K)/(T-K-1)) * (alpha' Sigma_e^-1 alpha) / (1 + mean_f' Omega_f^-1 mean_f)`

Here `Sigma_e = E'E/(T-K-1)` is the unbiased residual covariance and `Omega_f` uses divisor `T-1`. The reference F distribution is `F(N, T-N-K)`. The p-value is computed with SciPy's upper-tail survival function. Positive-definite covariance matrices are checked with Cholesky factorization and solved without explicitly forming matrix inverses.

The finite-sample GRS reference assumes the standard joint normality and time-independence conditions for regression disturbances. It is the classical test; HAC/Newey-West adjustments are not part of this statistic and remain in Step 6.

An independent matrix-OLS path recomputes the equivalent statistic using the MLE residual covariance `E'E/T`. Every run must agree with the covariance-unbiased implementation before output is written. Across the saved runs, the maximum statistic gap is {max_independent_grs_gap:.3e} and the maximum alpha gap is {max_independent_alpha_gap:.3e}.

## Results

Table 5 Panel A's 2x3-factor GRS references are **3.62** for FF3 (`HML`) and **2.84** for FF5 (`HML RMW CMA`). The paper does not report row-level p-values; all p-values below are computed from the stated F distribution.

{results_md}

Current-source FF3 differs from its Table 5 reference by {current_ff3['grs_gap']:+.4f}; current-source FF5 differs by {current_ff5['grs_gap']:+.4f}. {archived_ff5_note} CAPM is included as a joint test but has no matching Table 5 GRS reference. Archive rows are factor-vintage sensitivities using the current local portfolio file, not full 2015-vintage replications.

## Input fingerprints

Current CSV SHA-256 values:

{chr(10).join(f'- `{name}`: `{digest}`' for name, digest in current_hashes.items())}

Archive ZIP SHA-256 values:

{archive_hash_text}

{sensitivity_text}
"""
    return results, report


def main() -> None:
    results, report = build_outputs()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    results.to_csv(RESULTS_PATH, index=False, float_format="%.10g")
    REPORT_PATH.write_text(report, encoding="utf-8", newline="\n")
    print(
        results[
            [
                "model",
                "variant",
                "observations",
                "n_portfolios",
                "n_factors",
                "df_denominator",
                "grs_statistic",
                "p_value",
                "independent_grs_abs_gap",
                "paper_grs_reference",
            ]
        ].to_string(index=False, float_format=lambda value: f"{value:.6g}")
    )
    print(f"\nSaved GRS results: {RESULTS_PATH}")
    print(f"Saved GRS audit report: {REPORT_PATH}")


if __name__ == "__main__":
    main()
