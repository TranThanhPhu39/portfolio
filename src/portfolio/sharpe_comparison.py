"""Like-for-like in-sample Sharpe comparison without forcing an ordering."""

import json

import numpy as np
import pandas as pd

from src.backtest.benchmark import align_series
from src.backtest.transaction_costs import validate_weights
from src.backtest.walk_forward import validate_returns


def compare_sharpes(history, risk_free, max_sharpe_weights):
    validate_returns(history)
    if len(history) < 2:
        raise ValueError("At least two common monthly observations required")
    rf = align_series(risk_free, history.index, "risk_free")
    weights = validate_weights(max_sharpe_weights, history.columns)
    shared = {
        "start_date": history.index[0].date().isoformat(),
        "end_date": history.index[-1].date().isoformat(),
        "months": len(history),
        "rf_mean_monthly": float(rf.mean()),
        "sample": "in_sample",
        "fee_rate": 0.0,
    }

    def make_row(name, kind, returns):
        excess = returns - rf
        standard_deviation = float(excess.std(ddof=1))
        return {
            "name": name,
            "kind": kind,
            **shared,
            "mean_return_monthly": float(returns.mean()),
            "mean_excess_monthly": float(excess.mean()),
            "excess_sd_monthly": standard_deviation,
            "sharpe_annualized": (
                float(np.sqrt(12) * excess.mean() / standard_deviation)
                if standard_deviation > 1e-14
                else np.nan
            ),
        }

    rows = [make_row("MaxSharpe", "portfolio", history.astype(float) @ weights)]
    for asset in history.columns:
        rows.append(make_row(str(asset), "asset", history[asset].astype(float)))
    individual = np.array([row["sharpe_annualized"] for row in rows[1:]])
    valid = bool(np.isfinite(individual).all())
    average = float(individual.mean()) if valid else np.nan
    rows.append(
        {
            "name": "MeanAssetSharpe",
            "kind": "arithmetic_mean_of_asset_sharpes",
            **shared,
            "mean_return_monthly": np.nan,
            "mean_excess_monthly": np.nan,
            "excess_sd_monthly": np.nan,
            "sharpe_annualized": average,
        }
    )
    score = rows[0]["sharpe_annualized"]

    def difference(value):
        return float(score - value) if np.isfinite(score) and np.isfinite(value) else None

    best = float(individual.max()) if valid else np.nan
    metadata = {
        **shared,
        "assets": len(individual),
        "valid_asset_sharpes": int(np.isfinite(individual).sum()),
        "max_sharpe_minus_mean_asset": difference(average),
        "max_sharpe_minus_best_asset": difference(best),
        "formula": "sqrt(12) * mean(r_t - RF_t) / sample_std(r_t - RF_t), ddof=1",
        "mean_definition": "Arithmetic mean of all individual asset Sharpes",
    }
    return pd.DataFrame(rows), metadata


def export_sharpe_comparison(out, history, risk_free, weights):
    table, metadata = compare_sharpes(history, risk_free, weights)
    table.to_csv(out / "05_sharpe_assets_comparison.csv", index=False)
    (out / "05_sharpe_comparison_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8",
    )
    history.to_csv(out / "05_sharpe_input_returns.csv", index_label="date")
    align_series(risk_free, history.index, "risk_free").to_csv(
        out / "05_sharpe_input_rf.csv", index_label="date", header=["rf_return"]
    )
    weights.reindex(history.columns).to_csv(
        out / "05_sharpe_input_weights.csv", index_label="ticker", header=["weight"]
    )
    return table
