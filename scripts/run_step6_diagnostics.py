"""Run HAC and VIF diagnostics for the Step 3 factor models."""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.models.diagnostics import calculate_vif, run_hac_regression


DATA_DIR = PROJECT_ROOT / "test_data"
OUTPUT_DIR = PROJECT_ROOT / "outputs"
HAC_RESULTS_PATH = OUTPUT_DIR / "step6_hac_results.csv"
VIF_RESULTS_PATH = OUTPUT_DIR / "step6_vif.csv"
REPORT_PATH = OUTPUT_DIR / "step6_audit.md"
SAMPLE_START = "1963-07-01"
SAMPLE_END = "2013-12-01"
PORTFOLIO = "SMALL LoBM"
HAC_MAXLAGS = (12, 6)
PROJECT_VIF_LIMIT = 10.0
VIF_REFERENCE_LIMIT = 5.0
MODEL_SPECS = (
    ("CAPM", "ff3_factors_monthly.csv", ["Mkt-RF"]),
    ("FF3", "ff3_factors_monthly.csv", ["Mkt-RF", "SMB", "HML"]),
    ("FF5", "ff5_factors_monthly.csv", ["Mkt-RF", "SMB", "HML", "RMW", "CMA"]),
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_input(path: Path) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(f"Required Step 6 input is missing: {path}")
    return pd.read_csv(path, index_col=0, parse_dates=True)


def validate_sample(
    label: str,
    frame: pd.DataFrame,
    expected_dates: pd.DatetimeIndex,
    required_columns: list[str],
) -> pd.DataFrame:
    if not frame.columns.is_unique:
        raise ValueError(f"{label} has duplicate column names")
    missing = [column for column in required_columns if column not in frame.columns]
    if missing:
        raise KeyError(f"{label} is missing columns: {missing}")
    if frame.index.has_duplicates:
        raise ValueError(f"{label} contains duplicate dates")
    if not frame.index.is_monotonic_increasing:
        raise ValueError(f"{label} dates are not chronological")
    sample = frame.reindex(expected_dates).loc[:, required_columns]
    if sample.isna().any().any():
        raise ValueError(f"{label} has missing values in the 606-month sample")
    if not np.isfinite(sample.to_numpy(dtype=np.float64)).all():
        raise ValueError(f"{label} has non-finite values in the sample")
    return sample


def format_number(value: object, *, column: str, digits: int = 4) -> str:
    if pd.isna(value):
        return "—"
    if isinstance(value, (bool, np.bool_)):
        return "Yes" if value else "No"
    if isinstance(value, (int, np.integer)):
        return str(int(value))
    if isinstance(value, (float, np.floating)):
        if column.startswith("p_"):
            return f"{float(value):.6g}"
        return f"{float(value):.{digits}f}"
    return str(value)


def independent_hac_covariance(
    ols_result: object,
    *,
    maxlags: int,
    use_correction: bool,
) -> np.ndarray:
    """Rebuild Bartlett Newey-West covariance without statsmodels' HAC helper."""
    design = np.asarray(ols_result.model.exog, dtype=np.float64)
    residuals = np.asarray(ols_result.resid, dtype=np.float64)
    observations, n_parameters = design.shape
    score = design * residuals[:, None]
    meat = score.T @ score
    for lag in range(1, maxlags + 1):
        weight = 1.0 - lag / (maxlags + 1.0)
        autocovariance = score[lag:].T @ score[:-lag]
        meat += weight * (autocovariance + autocovariance.T)
    bread = np.linalg.solve(design.T @ design, np.eye(n_parameters))
    covariance = bread @ meat @ bread
    if use_correction:
        covariance *= observations / (observations - n_parameters)
    return covariance


def independent_vif_values(
    factors: pd.DataFrame,
    factor_cols: list[str],
) -> dict[str, float]:
    """Recompute VIF from auxiliary-regression R-squared values."""
    values = factors.loc[:, factor_cols].to_numpy(dtype=np.float64)
    design = np.column_stack([np.ones(len(values)), values])
    output = {}
    for position, factor in enumerate(factor_cols, start=1):
        target = design[:, position]
        auxiliary = np.delete(design, position, axis=1)
        coefficients = np.linalg.lstsq(auxiliary, target, rcond=None)[0]
        residual = target - auxiliary @ coefficients
        total = float(np.sum((target - target.mean()) ** 2))
        if total <= 0.0:
            raise ValueError(f"Factor {factor!r} has no variation for VIF")
        r_squared = 1.0 - float(residual @ residual) / total
        denominator = 1.0 - r_squared
        output[factor] = float("inf") if denominator <= 0.0 else 1.0 / denominator
    return output


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


def build_outputs() -> tuple[pd.DataFrame, pd.DataFrame, str]:
    expected_dates = pd.date_range(SAMPLE_START, SAMPLE_END, freq="MS")
    portfolio_path = DATA_DIR / "25_portfolios_size_bm.csv"
    ff3_path = DATA_DIR / "ff3_factors_monthly.csv"
    ff5_path = DATA_DIR / "ff5_factors_monthly.csv"
    portfolios = read_input(portfolio_path)
    ff3 = read_input(ff3_path)
    ff5 = read_input(ff5_path)

    if portfolios.shape[1] != 25 or not portfolios.columns.is_unique:
        raise ValueError("Expected exactly 25 uniquely named portfolio columns")
    if PORTFOLIO not in portfolios.columns:
        raise KeyError(f"Step 3 portfolio {PORTFOLIO!r} is absent from the LHS file")
    returns = validate_sample(
        "25 Size-B/M portfolios", portfolios, expected_dates, portfolios.columns.tolist()
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

    hac_rows: list[dict[str, object]] = []
    vif_rows: list[dict[str, object]] = []
    for model, factor_filename, factor_cols in MODEL_SPECS:
        factor_data = ff3_sample if factor_filename == ff3_path.name else ff5_sample
        fit = None
        for maxlags in HAC_MAXLAGS:
            diagnostics = run_hac_regression(
                returns[PORTFOLIO],
                factor_data,
                factor_cols,
                maxlags=maxlags,
                rf_col="RF",
                kernel="bartlett",
                use_correction=True,
                use_t=False,
            )
            fit = diagnostics.ols
            names = list(fit.model.exog_names)
            ols_params = np.asarray(fit.params, dtype=np.float64)
            hac_params = np.asarray(diagnostics.hac.params, dtype=np.float64)
            ols_se = np.asarray(fit.bse, dtype=np.float64)
            ols_t = np.asarray(fit.tvalues, dtype=np.float64)
            ols_p = np.asarray(fit.pvalues, dtype=np.float64)
            ols_log_p = np.log(2.0) + stats.t.logsf(
                np.abs(ols_t), df=float(fit.df_resid)
            )
            hac_se = np.asarray(diagnostics.hac.bse, dtype=np.float64)
            hac_z = np.asarray(diagnostics.hac.tvalues, dtype=np.float64)
            hac_p = np.asarray(diagnostics.hac.pvalues, dtype=np.float64)
            hac_log_p = np.log(2.0) + stats.norm.logsf(np.abs(hac_z))
            manual_covariance = independent_hac_covariance(
                fit,
                maxlags=maxlags,
                use_correction=True,
            )
            covariance_gap = float(
                np.max(np.abs(manual_covariance - np.asarray(diagnostics.hac.cov_params())))
            )
            if covariance_gap > 1e-10:
                raise RuntimeError(
                    f"Manual HAC covariance check failed for {model}, maxlags={maxlags}: "
                    f"gap={covariance_gap:.3g}"
                )
            if int(fit.nobs) != len(expected_dates):
                raise RuntimeError(f"{model} HAC fit did not use all 606 months")
            if not np.allclose(ols_params, hac_params, rtol=0.0, atol=1e-12):
                raise RuntimeError(f"{model} HAC run changed OLS coefficients")
            for index, term in enumerate(names):
                hac_rows.append(
                    {
                        "model": model,
                        "portfolio": PORTFOLIO,
                        "factor_source": factor_filename,
                        "maxlags": maxlags,
                        "kernel": diagnostics.kernel,
                        "use_correction": diagnostics.use_correction,
                        "inference_reference": "standard normal (z)",
                        "term": term,
                        "coefficient_unit": (
                            "decimal return per month"
                            if term == "const"
                            else "slope per decimal factor return"
                        ),
                        "observations": int(fit.nobs),
                        "coefficient_ols": ols_params[index],
                        "coefficient_hac": hac_params[index],
                        "se_ols": ols_se[index],
                        "t_ols": ols_t[index],
                        "p_ols": ols_p[index],
                        "log_p_ols": ols_log_p[index],
                        "se_hac": hac_se[index],
                        "z_hac": hac_z[index],
                        "p_hac": hac_p[index],
                        "log_p_hac": hac_log_p[index],
                        "hac_covariance_manual_max_abs_gap": covariance_gap,
                    }
                )

        vif_table = calculate_vif(factor_data, factor_cols)
        manual_vifs = independent_vif_values(factor_data, factor_cols)
        for row in vif_table.itertuples(index=False):
            single_factor = len(factor_cols) == 1
            manual_vif = manual_vifs[row.factor]
            vif_gap = (
                0.0
                if np.isinf(manual_vif) and np.isinf(row.vif)
                else abs(float(row.vif) - manual_vif)
            )
            if vif_gap > 1e-8:
                raise RuntimeError(
                    f"Independent VIF check failed for {model}/{row.factor}: "
                    f"gap={vif_gap:.3g}"
                )
            vif_rows.append(
                {
                    "model": model,
                    "factor_source": factor_filename,
                    "factor": row.factor,
                    "vif": row.vif,
                    "vif_independent": manual_vif,
                    "vif_independent_abs_gap": vif_gap,
                    "observations": row.observations,
                    "single_factor_model": single_factor,
                    "above_statsmodels_5_reference": bool(row.vif > VIF_REFERENCE_LIMIT),
                    "above_project_10_threshold": bool(row.vif > PROJECT_VIF_LIMIT),
                    "note": (
                        "Single RHS factor; VIF=1 is not informative about between-factor collinearity."
                        if single_factor
                        else "VIF is calculated with an intercept and excludes RF from the RHS."
                    ),
                }
            )

    hac_results = pd.DataFrame(hac_rows)
    vif_results = pd.DataFrame(vif_rows)
    expected_hac_rows = sum(1 + len(columns) for _, _, columns in MODEL_SPECS) * len(HAC_MAXLAGS)
    expected_vif_rows = sum(len(columns) for _, _, columns in MODEL_SPECS)
    if len(hac_results) != expected_hac_rows:
        raise RuntimeError(f"Expected {expected_hac_rows} HAC rows; found {len(hac_results)}")
    if len(vif_results) != expected_vif_rows:
        raise RuntimeError(f"Expected {expected_vif_rows} VIF rows; found {len(vif_results)}")
    if not (hac_results["observations"] == len(expected_dates)).all():
        raise RuntimeError("At least one HAC result did not use the same 606-month sample")
    if not (vif_results["observations"] == len(expected_dates)).all():
        raise RuntimeError("At least one VIF result did not use the same 606-month sample")

    step3_path = OUTPUT_DIR / "step3_model_comparison.csv"
    if not step3_path.is_file():
        raise FileNotFoundError(f"Step 3 comparison is required for audit: {step3_path}")
    step3 = pd.read_csv(step3_path)
    step3_alpha_gaps = []
    step3_t_gaps = []
    for model, factor_filename, _ in MODEL_SPECS:
        step3_row = step3.loc[step3["model"] == model]
        hac_alpha = hac_results.loc[
            (hac_results["model"] == model)
            & (hac_results["term"] == "const")
            & (hac_results["maxlags"] == 12)
        ]
        if len(step3_row) != 1 or len(hac_alpha) != 1:
            raise ValueError(f"Missing unique Step 3/HAC alpha row for {model}")
        step3_row = step3_row.iloc[0]
        hac_alpha = hac_alpha.iloc[0]
        if step3_row["factor_file"] != factor_filename:
            raise RuntimeError(f"Factor source changed between Step 3 and Step 6 for {model}")
        if int(step3_row["observations"]) != int(hac_alpha["observations"]):
            raise RuntimeError(f"Observation count changed between Step 3 and Step 6 for {model}")
        alpha_gap = abs(float(step3_row["alpha_pct_per_month"]) / 100.0 - hac_alpha["coefficient_ols"])
        t_gap = abs(float(step3_row["t_alpha"]) - hac_alpha["t_ols"])
        if alpha_gap > 1e-9 or t_gap > 1e-8:
            raise RuntimeError(
                f"Step 6 OLS baseline differs from Step 3 for {model}: "
                f"alpha gap={alpha_gap:.3g}, t gap={t_gap:.3g}"
            )
        step3_alpha_gaps.append(alpha_gap)
        step3_t_gaps.append(t_gap)
    max_step3_alpha_gap = max(step3_alpha_gaps)
    max_step3_t_gap = max(step3_t_gaps)

    max_vif = float(vif_results["vif"].max())
    max_hac_covariance_gap = float(hac_results["hac_covariance_manual_max_abs_gap"].max())
    max_vif_independent_gap = float(vif_results["vif_independent_abs_gap"].max())
    above_10 = vif_results.loc[vif_results["above_project_10_threshold"]]
    if above_10.empty:
        vif_verdict = "No factor VIF exceeds the project threshold of 10."
    else:
        values = ", ".join(f"{row.model}/{row.factor}={row.vif:.4f}" for row in above_10.itertuples())
        vif_verdict = f"VIF above 10 was found and recorded as an empirical result: {values}."
    above_5 = vif_results.loc[vif_results["above_statsmodels_5_reference"]]
    above_5_text = (
        ", ".join(f"{row.model}/{row.factor}={row.vif:.4f}" for row in above_5.itertuples())
        if not above_5.empty
        else "none"
    )

    current_hashes = {
        path.name: sha256_file(path)
        for path in (portfolio_path, ff3_path, ff5_path)
    }
    hac_alpha_summary = hac_results[
        (hac_results["term"] == "const") & (hac_results["maxlags"] == 12)
    ].copy()
    hac_alpha_summary["alpha_ols_pct_per_month"] = hac_alpha_summary[
        "coefficient_ols"
    ] * 100.0
    hac_alpha_summary["se_hac_pct_per_month"] = hac_alpha_summary["se_hac"] * 100.0
    hac_md = markdown_table(
        hac_alpha_summary,
        [
            ("Model", "model"),
            ("Factor source", "factor_source"),
            ("T", "observations"),
            ("Alpha OLS (%/month)", "alpha_ols_pct_per_month"),
            ("OLS t", "t_ols"),
            ("HAC SE (%/month), lag 12", "se_hac_pct_per_month"),
            ("z HAC", "z_hac"),
            ("HAC p-value", "p_hac"),
        ],
    )
    hac_alpha = hac_results[hac_results["term"] == "const"]
    lag_rows = []
    for model in (spec[0] for spec in MODEL_SPECS):
        at_12 = hac_alpha[(hac_alpha["model"] == model) & (hac_alpha["maxlags"] == 12)].iloc[0]
        at_6 = hac_alpha[(hac_alpha["model"] == model) & (hac_alpha["maxlags"] == 6)].iloc[0]
        decision_12 = bool(at_12["p_hac"] < 0.05)
        decision_6 = bool(at_6["p_hac"] < 0.05)
        lag_rows.append(
            {
                "model": model,
                "z_hac_lag12": at_12["z_hac"],
                "p_hac_lag12": at_12["p_hac"],
                "z_hac_lag6": at_6["z_hac"],
                "p_hac_lag6": at_6["p_hac"],
                "reject_5pct_lag12": decision_12,
                "reject_5pct_lag6": decision_6,
                "decision_changes": decision_12 != decision_6,
            }
        )
    lag_sensitivity = pd.DataFrame(lag_rows)
    lag_md = markdown_table(
        lag_sensitivity,
        [
            ("Model", "model"),
            ("z lag 12", "z_hac_lag12"),
            ("p lag 12", "p_hac_lag12"),
            ("z lag 6", "z_hac_lag6"),
            ("p lag 6", "p_hac_lag6"),
            ("Reject 5% at 12", "reject_5pct_lag12"),
            ("Reject 5% at 6", "reject_5pct_lag6"),
            ("Decision changes", "decision_changes"),
        ],
    )
    vif_md = markdown_table(
        vif_results,
        [
            ("Model", "model"),
            ("Factor", "factor"),
            ("VIF", "vif"),
            (">5 reference", "above_statsmodels_5_reference"),
            (">10 project flag", "above_project_10_threshold"),
            ("T", "observations"),
        ],
    )
    report = f"""# Step 6: HAC and VIF diagnostics

## Inputs and specification

HAC inference is calculated for `SMALL LoBM`, the same LHS used in Steps 2-4, on the complete July 1963–December 2013 sample (606 months). CAPM and FF3 use `ff3_factors_monthly.csv`; FF5 uses `ff5_factors_monthly.csv`. RF is subtracted from the raw portfolio return and is not an RHS factor. VIF is computed from each model's RHS factors on the same source/sample, with an intercept in its auxiliary design matrix; RF and the intercept are not reported as VIF targets.

HAC uses the Bartlett kernel, small-sample correction, and asymptotic-normal inference (`use_t=False`). Lag 12 is the primary monthly bandwidth; lag 6 is included as a sensitivity run. The HAC covariance changes standard errors and inference, not OLS coefficients. Extreme-tail p-values that underflow in standard floating-point output retain their finite log p-value in the full CSV.

## Newey-West results

The table reports the intercept and its standard error in percent per month at the primary 12-lag setting. The complete coefficient-level CSV retains regression-scale coefficients and records their units; it includes both lags.

The OLS alpha and t-statistic at lag 12 are cross-checked against the Step 3 comparison before output is written. Maximum Step 3 alpha gap is {max_step3_alpha_gap:.3e} in decimal returns; maximum OLS t-statistic gap is {max_step3_t_gap:.3e}.

The HAC covariance is separately recomputed from the Bartlett weighted score products. Its maximum difference from statsmodels is {max_hac_covariance_gap:.3e}. VIFs are also checked against the auxiliary-regression definition; the maximum difference is {max_vif_independent_gap:.3e}.

{hac_md}

The intercept's significance sensitivity to the two bandwidths is:

{lag_md}

## VIF results

Project threshold: VIF > 10. The installed statsmodels 0.14.0 documentation also flags >5 as a common caution reference. Values are reported without altering factors.

{vif_md}

Maximum VIF: {max_vif:.4f}. {vif_verdict} Values above the statsmodels >5 reference: {above_5_text}.

## Audit conclusion

The runner validates the three input files, fits all three Step 3 models on T=606 observations, generates 24 HAC coefficient rows (three models, intercept plus RHS factors, two lag settings), and generates {len(vif_results)} VIF rows. Coefficients from the HAC results are checked against their OLS values before output is written. Bandwidth sensitivity changes the CAPM alpha decision at 5%; report both lags. {vif_verdict}

Current CSV SHA-256 values:

{chr(10).join(f'- `{name}`: `{digest}`' for name, digest in current_hashes.items())}
"""
    return hac_results, vif_results, report


def main() -> None:
    hac_results, vif_results, report = build_outputs()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    hac_results.to_csv(HAC_RESULTS_PATH, index=False, float_format="%.15g")
    vif_results.to_csv(VIF_RESULTS_PATH, index=False, float_format="%.15g")
    REPORT_PATH.write_text(report, encoding="utf-8", newline="\n")
    print("HAC alpha summary at maxlags=12:")
    print(
        hac_results[(hac_results["term"] == "const") & (hac_results["maxlags"] == 12)][
            ["model", "observations", "coefficient_ols", "t_ols", "se_hac", "z_hac", "p_hac"]
        ].to_string(index=False, float_format=lambda value: f"{value:.6g}")
    )
    print("\nVIF:")
    print(vif_results[["model", "factor", "vif", "above_project_10_threshold"]].to_string(index=False, float_format=lambda value: f"{value:.6g}"))
    print(f"\nSaved HAC results: {HAC_RESULTS_PATH}")
    print(f"Saved VIF results: {VIF_RESULTS_PATH}")
    print(f"Saved diagnostics report: {REPORT_PATH}")


if __name__ == "__main__":
    main()
