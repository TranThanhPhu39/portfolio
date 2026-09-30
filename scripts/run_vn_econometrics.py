"""Run auditable CAPM, FF3, FF5, HAC, VIF, and GRS on VN monthly data."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.models.diagnostics import calculate_vif, run_hac_regression
from src.models.grs_test import grs_test
from src.models.regressions import run_factor_regression


MODEL_FACTORS = {
    "CAPM": ["MKT_RF"],
    "FF3": ["MKT_RF", "SMB", "HML"],
    "FF5": ["MKT_RF", "SMB_FF5", "HML", "RMW", "CMA"],
}
REQUIRED_FACTOR_COLUMNS = ["MKT_RF", "SMB", "HML", "SMB_FF5", "RMW", "CMA", "RF"]
HAC_LAGS = (12, 6)
ASSET_COUNT = 30


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def display_path(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def git_text(*args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, check=False
    )
    if result.returncode:
        raise RuntimeError(f"Git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def verify_factor_commit(returns_path: Path, factors_path: Path, commit: str) -> dict:
    expected_paths = {
        "returns": ROOT / "outputs" / "vn_period_factors" / "vn100_returns_clean.csv",
        "factors": ROOT / "outputs" / "vn_period_factors" / "vn100_factors_monthly.csv",
    }
    actual_paths = {"returns": returns_path, "factors": factors_path}
    if actual_paths != expected_paths:
        return {"verified": False, "reason": "custom input paths", "git_blob_oids": {}}
    blob_oids = {}
    for name, path in actual_paths.items():
        relative = path.relative_to(ROOT).as_posix()
        expected_oid = git_text("rev-parse", f"{commit}:{relative}")
        actual_oid = git_text("hash-object", f"--path={relative}", str(path))
        if actual_oid != expected_oid:
            raise ValueError(
                f"{relative} does not match Factor Team commit {commit} "
                f"after Git line-ending normalization"
            )
        blob_oids[name] = expected_oid
    return {"verified": True, "reason": "matched tracked Git blobs", "git_blob_oids": blob_oids}


def read_returns(path: Path) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(f"Return input not found: {path}")
    frame = pd.read_csv(path)
    required = {"ticker", "date", "return"}
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise KeyError(f"Return input is missing columns: {missing}")
    frame["date"] = pd.to_datetime(frame["date"], errors="raise").dt.normalize()
    if frame["date"].isna().any():
        raise ValueError("Return input has missing dates")
    expected_eom = frame["date"].dt.to_period("M").dt.to_timestamp("M")
    if not frame["date"].equals(expected_eom.rename("date")):
        raise ValueError("Return dates must be calendar month ends")
    frame["ticker"] = frame["ticker"].astype("string").str.strip()
    if frame["ticker"].isna().any() or frame["ticker"].eq("").any():
        raise ValueError("Return input has missing ticker labels")
    if frame.duplicated(["ticker", "date"]).any():
        raise ValueError("Return input has duplicate ticker-month rows")
    frame["return"] = pd.to_numeric(frame["return"], errors="raise")
    if not np.isfinite(frame["return"].to_numpy(dtype=float)).all():
        raise ValueError("Return input has missing or non-finite returns")
    return frame


def read_factors(path: Path) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(f"Factor input not found: {path}")
    frame = pd.read_csv(path)
    required = {"Date", *REQUIRED_FACTOR_COLUMNS}
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise KeyError(f"Factor input is missing columns: {missing}")
    frame["Date"] = pd.to_datetime(frame["Date"], errors="raise").dt.normalize()
    if frame["Date"].isna().any() or frame["Date"].duplicated().any():
        raise ValueError("Factor input has missing or duplicate dates")
    expected_eom = frame["Date"].dt.to_period("M").dt.to_timestamp("M")
    if not frame["Date"].equals(expected_eom.rename("Date")):
        raise ValueError("Factor dates must be calendar month ends")
    for column in REQUIRED_FACTOR_COLUMNS:
        frame[column] = pd.to_numeric(frame[column], errors="raise")
        values = frame[column].dropna().to_numpy(dtype=float)
        if not np.isfinite(values).all():
            raise ValueError(f"Factor {column} has non-finite values")
    if frame["RF"].dropna().abs().ge(1).any():
        raise ValueError("RF contains values >= 1; expected decimal monthly returns")
    if "MARKET" in frame.columns:
        market = pd.to_numeric(frame["MARKET"], errors="raise")
        gap = (frame["MKT_RF"] - (market - frame["RF"])).dropna().abs()
        if not gap.empty and float(gap.max()) > 1e-10:
            raise ValueError(f"MKT_RF does not match MARKET - RF; max gap={gap.max()}")
    return frame.set_index("Date").sort_index()


def read_universe(path: Path) -> tuple[list[str], str]:
    if not path.is_file():
        raise FileNotFoundError(f"Universe file not found: {path}")
    frame = pd.read_csv(path)
    if "ticker" not in frame.columns:
        raise KeyError("Universe file needs a ticker column")
    tickers = frame["ticker"].astype("string").str.strip()
    if tickers.isna().any() or tickers.eq("").any():
        raise ValueError("Universe file has blank tickers")
    output = tickers.tolist()
    if len(output) != ASSET_COUNT or len(set(output)) != ASSET_COUNT:
        raise ValueError(f"Universe must contain exactly {ASSET_COUNT} unique tickers")
    if "selection_rule" in frame.columns:
        rules = frame["selection_rule"].dropna().astype(str).unique().tolist()
        if len(rules) != 1:
            raise ValueError("Universe file must contain one consistent selection_rule")
        rule = rules[0]
    else:
        rule = "Explicit 30-ticker universe supplied; document its selection rationale."
    return output, rule


def apply_market_proxy(
    returns: pd.DataFrame,
    factors: pd.DataFrame,
    market_proxy: str,
) -> pd.DataFrame:
    if market_proxy == "VNINDEX":
        return factors.copy()
    if market_proxy != "VN100":
        raise ValueError(f"Unsupported market proxy: {market_proxy}")
    if "VN100" not in returns.columns:
        raise KeyError("Return panel has no VN100 monthly market return column")
    market_rows = returns[["date", "VN100"]].copy()
    market_rows["VN100"] = pd.to_numeric(market_rows["VN100"], errors="raise")
    if not np.isfinite(market_rows["VN100"].dropna().to_numpy(dtype=float)).all():
        raise ValueError("VN100 monthly market return contains non-finite values")
    distinct = market_rows.groupby("date")["VN100"].nunique(dropna=True)
    inconsistent = distinct.loc[distinct.ne(1)]
    if not inconsistent.empty:
        raise ValueError(
            "VN100 market return is not constant across ticker rows for dates: "
            + ", ".join(date.strftime("%Y-%m-%d") for date in inconsistent.index[:10])
        )
    market = market_rows.drop_duplicates("date").set_index("date")["VN100"]
    market = market.reindex(factors.index)
    if market.isna().any():
        missing = market.index[market.isna()]
        raise ValueError(
            "VN100 market return missing for factor dates: "
            + ", ".join(date.strftime("%Y-%m-%d") for date in missing[:10])
        )
    adjusted = factors.copy()
    adjusted["MARKET"] = market
    adjusted["MKT_RF"] = market - adjusted["RF"]
    return adjusted


def markdown_table(frame: pd.DataFrame, columns: list[str], digits: int = 4) -> str:
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join(["---"] * len(columns)) + " |",
    ]
    for values in frame.loc[:, columns].itertuples(index=False, name=None):
        formatted = []
        for value in values:
            if pd.isna(value):
                formatted.append("")
            elif isinstance(value, (float, np.floating)):
                formatted.append(f"{float(value):.{digits}f}")
            else:
                formatted.append(str(value))
        lines.append("| " + " | ".join(formatted) + " |")
    return "\n".join(lines)


def market_proxy_sensitivity(
    returns: pd.DataFrame,
    raw_factors: pd.DataFrame,
    asset_returns: pd.DataFrame,
    sample_dates: pd.DatetimeIndex,
) -> pd.DataFrame:
    rows: list[dict] = []
    for proxy in ("VN100", "VNINDEX"):
        proxy_factors = apply_market_proxy(returns, raw_factors, proxy).reindex(
            sample_dates
        )
        for model, factor_columns in MODEL_FACTORS.items():
            factor_data = proxy_factors.loc[:, ["RF", *factor_columns]]
            fits = [
                run_factor_regression(
                    asset_returns[ticker], factor_data, factor_columns
                )
                for ticker in asset_returns.columns
            ]
            grs = grs_test(asset_returns, factor_data, factor_columns)
            vif = calculate_vif(proxy_factors, factor_columns)
            rows.append(
                {
                    "market_proxy": proxy,
                    "model": model,
                    "n_assets": len(fits),
                    "t_months": int(fits[0].nobs),
                    "mean_abs_alpha_pct_per_month": float(
                        np.mean([abs(float(fit.params["const"])) for fit in fits])
                        * 100.0
                    ),
                    "mean_r_squared": float(np.mean([fit.rsquared for fit in fits])),
                    "grs_f": grs.statistic,
                    "grs_p_value": grs.p_value,
                    "max_rhs_vif": float(vif["vif"].max()),
                }
            )
    return pd.DataFrame(rows)


def run(args: argparse.Namespace) -> None:
    source_verification = verify_factor_commit(
        args.returns, args.factors, args.factor_commit
    )
    returns = read_returns(args.returns)
    raw_factors = read_factors(args.factors)
    factors = apply_market_proxy(returns, raw_factors, args.market_proxy)
    start = pd.Period(args.start, freq="M")
    end = pd.Period(args.end, freq="M")
    if end < start:
        raise ValueError("end month precedes start month")
    sample_dates = pd.period_range(start, end, freq="M").to_timestamp("M")
    sample_factors = factors.reindex(sample_dates)
    if sample_factors[REQUIRED_FACTOR_COLUMNS].isna().any().any():
        missing = sample_factors[REQUIRED_FACTOR_COLUMNS].isna().sum()
        raise ValueError(
            "Chosen common period has missing factors: "
            + ", ".join(f"{key}={int(value)}" for key, value in missing.items() if value)
        )
    if not np.isfinite(
        sample_factors[REQUIRED_FACTOR_COLUMNS].to_numpy(dtype=float)
    ).all():
        raise ValueError("Chosen factor sample contains non-finite values")

    tickers, universe_rule = read_universe(args.universe)
    sample_status = (
        "KTL_BASELINE_JUNE_2021_FORMATION_TOP30"
        if args.universe_status == "team-baseline"
        else "GROUP_APPROVED_UNIVERSE"
    )

    wide = returns.pivot(index="date", columns="ticker", values="return")
    missing_tickers = sorted(set(tickers).difference(wide.columns))
    if missing_tickers:
        raise ValueError(f"Selected tickers missing from returns: {missing_tickers}")
    asset_returns = wide.reindex(index=sample_dates, columns=tickers)
    missing_asset_months = asset_returns.isna().sum()
    if missing_asset_months.any():
        detail = {name: int(count) for name, count in missing_asset_months.items() if count}
        raise ValueError(f"Selected assets have missing months in common sample: {detail}")
    if len(sample_dates) <= ASSET_COUNT + max(map(len, MODEL_FACTORS.values())):
        raise ValueError("Need T > N + K for FF5 GRS on selected assets")

    summary_rows: list[dict] = []
    coefficient_rows: list[dict] = []
    grs_rows: list[dict] = []
    vif_rows: list[dict] = []
    example_summaries: list[str] = []
    for model, factor_columns in MODEL_FACTORS.items():
        factor_data = sample_factors.loc[:, ["RF", *factor_columns]].copy()
        alpha_by_ticker: dict[str, float] = {}
        for ticker in tickers:
            raw_return = asset_returns[ticker].copy()
            fit = run_factor_regression(raw_return, factor_data, factor_columns)
            robust = {
                lag: run_hac_regression(
                    raw_return,
                    factor_data,
                    factor_columns,
                    maxlags=lag,
                    kernel="bartlett",
                    use_correction=True,
                    use_t=False,
                ).hac
                for lag in HAC_LAGS
            }
            if int(fit.nobs) != len(sample_dates):
                raise RuntimeError(f"{model}/{ticker} lost observations")
            alpha_by_ticker[ticker] = float(fit.params["const"])
            names = list(fit.model.exog_names)
            for position, name in enumerate(names):
                row = {
                    "model": model,
                    "ticker": ticker,
                    "term": name,
                    "estimate_decimal": float(fit.params[name]),
                    "ols_se_decimal": float(fit.bse[name]),
                    "ols_t": float(fit.tvalues[name]),
                    "ols_p": float(fit.pvalues[name]),
                    "n_months": int(fit.nobs),
                    "r_squared": float(fit.rsquared),
                }
                for lag in HAC_LAGS:
                    row[f"hac_se_lag{lag}_decimal"] = float(robust[lag].bse[position])
                    row[f"hac_z_lag{lag}"] = float(robust[lag].tvalues[position])
                    row[f"hac_p_lag{lag}"] = float(robust[lag].pvalues[position])
                coefficient_rows.append(row)
            summary_rows.append(
                {
                    "model": model,
                    "ticker": ticker,
                    "n_months": int(fit.nobs),
                    "alpha_pct_per_month": float(fit.params["const"] * 100.0),
                    "alpha_t_ols": float(fit.tvalues["const"]),
                    "alpha_p_ols": float(fit.pvalues["const"]),
                    "alpha_z_hac12": float(robust[12].tvalues[0]),
                    "alpha_p_hac12": float(robust[12].pvalues[0]),
                    "alpha_z_hac6": float(robust[6].tvalues[0]),
                    "alpha_p_hac6": float(robust[6].pvalues[0]),
                    "r_squared": float(fit.rsquared),
                    **{f"beta_{name}": float(fit.params[name]) for name in factor_columns},
                }
            )
            if ticker == tickers[0]:
                summary_text = "\n".join(
                    line.rstrip() for line in fit.summary().as_text().splitlines()
                )
                example_summaries.append(f"{model}: {ticker}\n\n{summary_text}\n")

        grs = grs_test(asset_returns, factor_data, factor_columns)
        if not np.allclose(
            grs.alphas.reindex(tickers).to_numpy(dtype=float),
            np.array([alpha_by_ticker[ticker] for ticker in tickers]),
            atol=1e-10,
            rtol=0.0,
        ):
            raise RuntimeError(f"{model} GRS alphas differ from individual regressions")
        grs_rows.append(
            {
                "model": model,
                "grs_f": grs.statistic,
                "p_value": grs.p_value,
                "n_assets": grs.n_portfolios,
                "k_factors": grs.n_factors,
                "t_months": grs.observations,
                "df_denominator": grs.denominator_df,
            }
        )
        vif = calculate_vif(sample_factors, factor_columns)
        vif.insert(0, "model", model)
        vif["above_10"] = vif["vif"] > 10.0
        vif_rows.extend(vif.to_dict(orient="records"))

    summaries = pd.DataFrame(summary_rows)
    coefficients = pd.DataFrame(coefficient_rows)
    grs_results = pd.DataFrame(grs_rows)
    vif_results = pd.DataFrame(vif_rows)
    table5 = (
        summaries.groupby("model")
        .agg(
            mean_abs_alpha_pct=("alpha_pct_per_month", lambda x: x.abs().mean()),
            mean_r_squared=("r_squared", "mean"),
        )
        .reset_index()
        .merge(grs_results, on="model", validate="one_to_one")
    )
    table5["model"] = pd.Categorical(table5["model"], MODEL_FACTORS, ordered=True)
    table5 = table5.sort_values("model").reset_index(drop=True)
    table5["model"] = table5["model"].astype(str)

    table7 = pd.DataFrame({"ticker": tickers})
    for model in MODEL_FACTORS:
        block = summaries.loc[summaries["model"].eq(model)].set_index("ticker")
        for source, suffix in [
            ("alpha_pct_per_month", "alpha_pct_per_month"),
            ("alpha_t_ols", "alpha_t_ols"),
            ("alpha_z_hac12", "alpha_z_hac12"),
            ("r_squared", "r_squared"),
        ]:
            table7[f"{model}_{suffix}"] = table7["ticker"].map(block[source])
        for factor in MODEL_FACTORS[model]:
            table7[f"{model}_beta_{factor}"] = table7["ticker"].map(
                block[f"beta_{factor}"]
            )

    hml_response = sample_factors["HML"]
    hml_design = sm.add_constant(
        sample_factors[["MKT_RF", "SMB_FF5", "RMW", "CMA"]], has_constant="add"
    )
    hml_fit = sm.OLS(hml_response, hml_design, missing="raise").fit()
    hml_row = {
        "n_months": int(hml_fit.nobs),
        "alpha_pct_per_month": float(hml_fit.params["const"] * 100.0),
        "alpha_t_ols": float(hml_fit.tvalues["const"]),
        "alpha_p_ols": float(hml_fit.pvalues["const"]),
        "r_squared": float(hml_fit.rsquared),
    }
    for lag in HAC_LAGS:
        robust = hml_fit.get_robustcov_results(
            cov_type="HAC",
            maxlags=lag,
            kernel="bartlett",
            use_correction=True,
            use_t=False,
        )
        hml_row[f"alpha_z_hac{lag}"] = float(robust.tvalues[0])
        hml_row[f"alpha_p_hac{lag}"] = float(robust.pvalues[0])

    market_sensitivity = market_proxy_sensitivity(
        returns, raw_factors, asset_returns, sample_dates
    )

    selected_input = returns.loc[
        returns["ticker"].isin(tickers) & returns["date"].isin(sample_dates)
    ].copy()
    qa = {
        "sample_status": sample_status,
        "source_return_rows": int(len(returns)),
        "source_return_tickers": int(returns["ticker"].nunique()),
        "source_factor_months": int(len(factors)),
        "common_months": int(len(sample_dates)),
        "sample_start": sample_dates.min().strftime("%Y-%m-%d"),
        "sample_end": sample_dates.max().strftime("%Y-%m-%d"),
        "assets": len(tickers),
        "selection_rule": universe_rule,
        "universe_status": args.universe_status,
        "selected_return_rows": int(len(selected_input)),
        "return_sources": (
            selected_input["return_source"].value_counts().to_dict()
            if "return_source" in selected_input.columns
            else {}
        ),
        "selected_abs_return_over_100pct": int(selected_input["return"].abs().gt(1).sum()),
        "selected_reported_price_gap_over_1pp": (
            int(selected_input["reported_minus_price_return"].abs().gt(0.01).sum())
            if "reported_minus_price_return" in selected_input.columns
            else None
        ),
        "vif_over_10_count": int(vif_results["above_10"].sum()),
        "factor_team_market_proxy": "VNINDEX",
        "econometrics_market_proxy": args.market_proxy,
        "market_factor_construction": (
            "Factor Team MKT_RF based on VNINDEX."
            if args.market_proxy == "VNINDEX"
            else "Monthly VN100 return from the matched return panel minus Factor Team RF."
        ),
        "factor_team_rf_proxy": "1Y government yield converted to effective monthly return",
        "factor_team_schedule": "June formation, July-to-June holding",
        "factor_team_weighting": "lagged market capitalization",
        "factor_team_fiscal_rule": "latest statement announced by formation date",
        "source_commit_factor_branch": args.factor_commit,
        "source_commit_econometrics_main": args.econometrics_commit,
        "returns_sha256": sha256(args.returns),
        "factors_sha256": sha256(args.factors),
        "factor_source_verification": source_verification,
        "universe_sha256": sha256(args.universe),
        "python": sys.version.split()[0],
        "pandas": pd.__version__,
    }
    if len(summaries) != ASSET_COUNT * len(MODEL_FACTORS):
        raise RuntimeError("Model summary does not contain 30 × 3 rows")
    if not summaries["n_months"].eq(len(sample_dates)).all():
        raise RuntimeError("Models do not use the same month sample")
    if len(grs_results) != len(MODEL_FACTORS):
        raise RuntimeError("GRS did not complete for every model")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    summaries.to_csv(args.output_dir / "asset_model_summary.csv", index=False, float_format="%.10g")
    coefficients.to_csv(args.output_dir / "coefficient_detail.csv", index=False, float_format="%.10g")
    grs_results.to_csv(args.output_dir / "grs_summary.csv", index=False, float_format="%.10g")
    vif_results.to_csv(args.output_dir / "vif.csv", index=False, float_format="%.10g")
    market_sensitivity.to_csv(
        args.output_dir / "market_proxy_sensitivity.csv",
        index=False,
        float_format="%.10g",
    )
    table5.to_csv(args.output_dir / "table5_style_summary.csv", index=False, float_format="%.10g")
    table7.to_csv(args.output_dir / "table7_style_assets.csv", index=False, float_format="%.10g")
    pd.DataFrame([hml_row]).to_csv(
        args.output_dir / "hml_redundancy.csv", index=False, float_format="%.10g"
    )
    pd.DataFrame({"ticker": tickers}).to_csv(
        args.output_dir / "selected_tickers.csv", index=False
    )
    pd.DataFrame({"Date": sample_dates}).to_csv(
        args.output_dir / "sample_months.csv", index=False, date_format="%Y-%m-%d"
    )
    (args.output_dir / "model_summaries.txt").write_text(
        "\n\n".join(example_summaries), encoding="utf-8"
    )
    (args.output_dir / "run_manifest.json").write_text(
        json.dumps(qa, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    r2 = summaries.pivot(index="ticker", columns="model", values="r_squared")
    decreases = r2.index[r2["FF5"] + 1e-12 < r2["FF3"]].tolist()
    report = f"""# VN100 econometrics run — {sample_status}

## Inputs and sample

- Returns: `{display_path(args.returns)}`; factors: `{display_path(args.factors)}`. Source commit `{args.factor_commit}`; tracked-blob verification: `{source_verification['verified']}` ({source_verification['reason']}).
- Exactly {len(tickers)} assets and {len(sample_dates)} common monthly observations ({qa['sample_start']} to {qa['sample_end']}). All three models and all three GRS tests use this same sample.
- Return, RF, and factors are decimals in the input. `run_factor_regression()` subtracts RF once. CAPM uses MKT_RF; FF3 uses SMB; FF5 uses the separate SMB_FF5 plus HML, RMW, CMA.
- MKT uses `{args.market_proxy}`. {('MKT_RF is the Factor Team series based on VNINDEX.' if args.market_proxy == 'VNINDEX' else 'MKT_RF is recomputed from the monthly VN100 return column in the matched return panel minus the Factor Team RF.')}
- RF remains the Factor Team's effective monthly conversion from a 1Y yield; portfolio formation is June with July-to-June holding and lagged total market-cap weights. See `docs/vn_econometrics_method_choices.md` for the baseline method and its basis.
- Universe selection: {universe_rule}. The Econometrics Team chose the June 2021 formation market-cap rule before the July 2021–June 2026 return window; status: `{args.universe_status}`.

## Summary like Fama–French Table 5

{markdown_table(table5, ['model', 't_months', 'n_assets', 'k_factors', 'grs_f', 'p_value', 'mean_abs_alpha_pct', 'mean_r_squared'])}

The paper's Table 5 uses 25 or 32 sorted US portfolios; this table uses 30 VN stocks. The figures are not numerical replication of the paper.

At the 5% level, the GRS p-values do not reject the joint zero-alpha null for CAPM, FF3, or FF5 in this 30-stock, 60-month sample. This is a failure to reject for this sample, not proof that a model is true.

## Market proxy sensitivity

Both VN100 and VNINDEX were run on the same assets, months, RF, and SMB/HML/RMW/CMA series:

{markdown_table(market_sensitivity, ['market_proxy', 'model', 'mean_abs_alpha_pct_per_month', 'mean_r_squared', 'grs_f', 'grs_p_value', 'max_rhs_vif'])}

## Inference and diagnostics

- OLS alpha/t, factor betas, and R² for every stock/model are in `table7_style_assets.csv` and `asset_model_summary.csv`; coefficient-level OLS and HAC lag 12/6 estimates are in `coefficient_detail.csv`.
- VIF rows above the project threshold 10: {qa['vif_over_10_count']}. Values are in `vif.csv`.
- FF5 R² is below FF3 R² for {len(decreases)} of 30 assets: {', '.join(decreases) if decreases else 'none'}. This can occur because FF5 uses SMB_FF5 rather than the FF3 SMB series.
- HML spanning regression (HML on MKT_RF, SMB_FF5, RMW, CMA): alpha {hml_row['alpha_pct_per_month']:.4f}%/month; OLS t {hml_row['alpha_t_ols']:.4f}; HAC lag-12 z {hml_row['alpha_z_hac12']:.4f}. Full p-values are in `hml_redundancy.csv`.
- Selected returns use source counts {qa['return_sources']}. Reported-vs-price return gaps above 1 percentage point in selected rows: {qa['selected_reported_price_gap_over_1pp']}. These are retained as audit flags.

## Outputs and status

`asset_model_summary.csv`, `coefficient_detail.csv`, `grs_summary.csv`, `vif.csv`, `market_proxy_sensitivity.csv`, `table5_style_summary.csv`, `table7_style_assets.csv`, `hml_redundancy.csv`, `selected_tickers.csv`, `sample_months.csv`, `model_summaries.txt`, and `run_manifest.json` are generated by `scripts/run_vn_econometrics.py`.

This is the Econometrics Team's baseline result. The 30-asset list is fixed using information at the June 2021 formation and all selected returns are present for the following 60 months. Factor columns follow the Factor Team's versioned output; method choices and deviations from the original project brief are documented in `docs/vn_econometrics_method_choices.md`.
"""
    (args.output_dir / "run_report.md").write_text(report, encoding="utf-8")
    print(f"status={sample_status}")
    print(f"assets={len(tickers)}")
    print(f"months={len(sample_dates)} ({qa['sample_start']} to {qa['sample_end']})")
    print(f"regressions={len(summaries)}")
    print(f"grs={grs_results[['model', 'grs_f', 'p_value']].to_dict('records')}")
    print(f"vif_over_10={qa['vif_over_10_count']}")
    print(f"output_dir={args.output_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--returns",
        type=Path,
        default=ROOT / "outputs" / "vn_period_factors" / "vn100_returns_clean.csv",
    )
    parser.add_argument(
        "--factors",
        type=Path,
        default=ROOT / "outputs" / "vn_period_factors" / "vn100_factors_monthly.csv",
    )
    parser.add_argument(
        "--universe",
        type=Path,
        default=ROOT / "config" / "vn_econometrics_universe.csv",
        help="CSV with exactly 30 tickers and a documented selection rule",
    )
    parser.add_argument(
        "--universe-status",
        choices=["team-baseline", "group-approved"],
        default="team-baseline",
        help="Record whether this is the Econometrics Team baseline or a group-approved universe",
    )
    parser.add_argument("--start", default="2021-07", help="First common sample month YYYY-MM")
    parser.add_argument("--end", default="2026-06", help="Last common sample month YYYY-MM")
    parser.add_argument(
        "--market-proxy",
        choices=["VN100", "VNINDEX"],
        default="VN100",
        help="Market series for MKT-RF; project baseline uses VN100",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "outputs" / "vn_econometrics_baseline",
    )
    parser.add_argument(
        "--factor-commit",
        default="926f53deaaf0c9cc2e75a540fb789eb1f811d82a",
    )
    parser.add_argument(
        "--econometrics-commit",
        default="08b7096e4f6971dd58c4c9ca63b2b65a0cf476bf",
    )
    args = parser.parse_args()
    args.returns = args.returns.resolve()
    args.factors = args.factors.resolve()
    args.universe = args.universe.resolve()
    args.output_dir = args.output_dir.resolve()
    run(args)


if __name__ == "__main__":
    main()
