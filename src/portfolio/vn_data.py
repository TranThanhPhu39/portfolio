"""Explicit conversion of group period files without modifying originals."""

from pathlib import Path

import numpy as np
import pandas as pd


def load_periods(
    folder,
    return_basis="provided",
    rf_basis="annual_effective_percent",
    end="2026-08",
):
    paths = sorted(Path(folder).glob("Top100_Ky*.csv"))
    if not paths:
        raise ValueError("No period CSV files")
    frames = []
    for path in paths:
        try:
            frame = pd.read_csv(path, encoding="utf-8-sig")
        except UnicodeDecodeError:
            frame = pd.read_csv(path, encoding="cp1252")
        frame["source_file"] = path.name
        frames.append(frame)
    raw = pd.concat(frames, ignore_index=True)
    required = {"Ticker", "Date", "Close (EOM)", "Monthly Return (%)", "rRF", "VN30"}
    missing = sorted(required.difference(raw.columns))
    if missing:
        raise ValueError(f"Period files are missing columns: {missing}")
    raw["observed_date"] = pd.to_datetime(raw.Date, format="%d/%m/%Y", errors="raise")
    raw["date"] = raw.observed_date.dt.to_period("M").dt.to_timestamp("M")
    if raw.duplicated(["date", "Ticker"]).any():
        raise ValueError("Duplicate ticker month")
    partial = raw.loc[raw.observed_date != raw.date, "date"].unique()
    last = pd.Period(end, freq="M").to_timestamp("M")
    if any(pd.Timestamp(date) <= last for date in partial):
        raise ValueError("Selected range includes non-month-end observations; choose earlier end")
    data = raw.loc[raw.date <= last].copy()

    def numeric(series):
        cleaned = series.astype(str).str.replace(",", "", regex=False).where(
            series.notna(), np.nan
        )
        return pd.to_numeric(cleaned, errors="raise")

    for column in ["Monthly Return (%)", "Close (EOM)", "rRF", "VN30"]:
        data[column] = numeric(data[column])
    for column in ["rRF", "VN30"]:
        if data.groupby("date")[column].nunique(dropna=False).gt(1).any():
            raise ValueError(f"Conflicting {column} by date")
    data["present"] = True
    membership = (
        data.pivot(index="date", columns="Ticker", values="present")
        .eq(True)
        .sort_index()
    )
    prices = data.pivot(index="date", columns="Ticker", values="Close (EOM)").reindex_like(
        membership
    )
    if return_basis == "provided":
        returns = (
            data.pivot(index="date", columns="Ticker", values="Monthly Return (%)")
            .reindex_like(membership)
            / 100
        )
    elif return_basis == "prices":
        returns = prices.pct_change(fill_method=None)
        if returns.iloc[0].isna().all():
            returns = returns.iloc[1:]
            membership = membership.loc[returns.index]
    else:
        raise ValueError("Unknown return basis")
    monthly = data.groupby("date")[["rRF", "VN30"]].first().reindex(returns.index)
    if rf_basis == "annual_effective_percent":
        risk_free = (1 + monthly.rRF / 100) ** (1 / 12) - 1
    elif rf_basis == "monthly_percent":
        risk_free = monthly.rRF / 100
    else:
        raise ValueError("Unknown RF basis")
    if not np.isfinite(risk_free).all():
        raise ValueError("Missing RF")
    return returns, membership, risk_free, monthly.VN30 / 100, prices
