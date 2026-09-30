"""Point-in-time factor construction for VN100 formation and holding periods."""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path, PurePosixPath
import zipfile

import numpy as np
import pandas as pd

from .portfolio_sort import portfolio_sort
from .smb_hml import portfolio_returns


PERIOD_SUMMARY_FILE = "_Tom_tat_cac_ky.csv"
MEMBERSHIP_FILE = "_Thanh_phan_top100_theo_ky.csv"
MARKET_COLUMNS = ("VN100", "VNINDEX", "VN30")


@dataclass(frozen=True)
class PeriodFactorResult:
    """Outputs produced by the period-based factor pipeline."""

    factors: pd.DataFrame
    formation_audit: pd.DataFrame
    group_assignments: pd.DataFrame
    group_counts: pd.DataFrame
    returns_panel: pd.DataFrame
    data_quality: pd.DataFrame


def annual_yield_percent_to_monthly(rate: pd.Series | float) -> pd.Series | float:
    """Convert an effective annual yield in percent to a monthly decimal return."""
    return (1.0 + rate / 100.0) ** (1.0 / 12.0) - 1.0


def _read_csv_from_zip(archive: zipfile.ZipFile, name: str) -> pd.DataFrame:
    exact = name if name in archive.namelist() else None
    if exact is None:
        basename = PurePosixPath(name).name.casefold()
        matches = [
            entry for entry in archive.namelist()
            if PurePosixPath(entry).name.casefold() == basename
        ]
        if len(matches) != 1:
            raise ValueError(f"expected one ZIP entry named {name!r}, found {matches}")
        exact = matches[0]
    raw = archive.read(exact)
    for encoding in ("utf-8-sig", "utf-8", "cp1258", "latin1"):
        try:
            return pd.read_csv(BytesIO(raw), encoding=encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError(f"could not decode {name}")


def _numeric(series: pd.Series) -> pd.Series:
    if pd.api.types.is_numeric_dtype(series):
        return pd.to_numeric(series, errors="coerce")
    return pd.to_numeric(
        series.astype("string").str.replace(",", "", regex=False), errors="coerce"
    )


def load_period_archive(
    path: str | Path,
    *,
    include_incomplete: bool = False,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load the supplied period files without modifying the source archive.

    Returns period metadata, membership at formation, and monthly returns in
    decimal form. Incomplete periods are excluded by default.
    """
    path = Path(path)
    with zipfile.ZipFile(path) as archive:
        periods = _read_csv_from_zip(archive, PERIOD_SUMMARY_FILE)
        membership = _read_csv_from_zip(archive, MEMBERSHIP_FILE)
        required_meta = {
            "Ky", "File", "Thang_xep_hang", "Thang_giu_dau", "Thang_giu_cuoi",
            "So_ma", "So_dong", "So_thang",
        }
        if not required_meta.issubset(periods.columns):
            missing = sorted(required_meta.difference(periods.columns))
            raise ValueError(f"period summary is missing columns: {missing}")
        if membership.duplicated(["Ky", "Ticker"]).any():
            raise ValueError("membership contains duplicate period-ticker rows")

        period_frames: list[pd.DataFrame] = []
        completeness: list[bool] = []
        for row in periods.itertuples(index=False):
            frame = _read_csv_from_zip(archive, row.File)
            required = {"Ticker", "Date", "Monthly Return (%)", *MARKET_COLUMNS}
            if not required.issubset(frame.columns):
                missing = sorted(required.difference(frame.columns))
                raise ValueError(f"{row.File} is missing columns: {missing}")
            frame = frame.copy()
            frame["period"] = int(row.Ky)
            frame["date"] = pd.to_datetime(frame["Date"], dayfirst=True, errors="coerce")
            frame["ticker"] = frame["Ticker"].astype(str)
            frame["return"] = _numeric(frame["Monthly Return (%)"]) / 100.0
            for name in MARKET_COLUMNS:
                frame[name] = _numeric(frame[name]) / 100.0
            if frame[["ticker", "date"]].duplicated().any():
                raise ValueError(f"{row.File} contains duplicate ticker-date rows")
            scheduled_months = len(pd.period_range(
                str(row.Thang_giu_dau), str(row.Thang_giu_cuoi), freq="M"
            ))
            expected_rows = int(row.So_ma) * scheduled_months
            complete = (
                len(frame) == expected_rows
                and frame["ticker"].nunique() == int(row.So_ma)
                and frame["date"].nunique() == scheduled_months
                and int(row.So_thang) == scheduled_months
            )
            completeness.append(bool(complete))
            if complete or include_incomplete:
                period_frames.append(
                    frame[["period", "ticker", "date", "return", *MARKET_COLUMNS]].copy()
                )

    periods = periods.copy()
    periods["complete"] = completeness
    periods["formation_date"] = (
        pd.to_datetime(periods["Thang_xep_hang"].astype(str) + "-01")
        + pd.offsets.MonthEnd(0)
    )
    periods["holding_start"] = pd.to_datetime(
        periods["Thang_giu_dau"].astype(str) + "-01"
    ) + pd.offsets.MonthEnd(0)
    periods["holding_end"] = pd.to_datetime(
        periods["Thang_giu_cuoi"].astype(str) + "-01"
    ) + pd.offsets.MonthEnd(0)
    selected_periods = set(periods.loc[periods["complete"] | include_incomplete, "Ky"])
    membership = membership.loc[membership["Ky"].isin(selected_periods)].copy()
    membership = membership.rename(
        columns={"Ky": "period", "Ticker": "ticker", "Market_Cap": "formation_market_cap"}
    )
    membership["ticker"] = membership["ticker"].astype(str)
    membership["formation_market_cap"] = _numeric(membership["formation_market_cap"])
    membership = membership.merge(
        periods[["Ky", "formation_date", "holding_start", "holding_end", "complete"]]
        .rename(columns={"Ky": "period"}),
        on="period",
        how="left",
        validate="many_to_one",
    )
    returns = pd.concat(period_frames, ignore_index=True) if period_frames else pd.DataFrame()
    return periods, membership, returns


def _xlsx_bytes(archive: zipfile.ZipFile, predicate) -> bytes:
    matches = [
        name for name in archive.namelist()
        if predicate(PurePosixPath(name).name)
    ]
    if len(matches) != 1:
        raise ValueError(f"expected one matching workbook, found {matches}")
    return archive.read(matches[0])


def load_master_archive(
    path: str | Path,
    *,
    rf_tenor: str = "1Y",
) -> tuple[
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
]:
    """Load events, caps, returns, market series, sectors, RF, and conflicts."""
    if rf_tenor not in {"1Y", "3Y", "10Y"}:
        raise ValueError("rf_tenor must be one of: 1Y, 3Y, 10Y")
    path = Path(path)
    with zipfile.ZipFile(path) as archive:
        master_raw = _xlsx_bytes(
            archive,
            lambda name: name.lower().startswith("file data") and name.lower().endswith(".xlsx"),
        )
        master = pd.read_excel(BytesIO(master_raw), sheet_name="Tổng hợp", engine="openpyxl")
        sector_raw = pd.read_excel(BytesIO(master_raw), sheet_name="Biến", engine="openpyxl")
        rf_raw = _xlsx_bytes(
            archive, lambda name: name.lower() == f"rrf {rf_tenor.lower()}.xlsx"
        )
        rf = pd.read_excel(BytesIO(rf_raw), sheet_name="Table Data", engine="openpyxl")

    required = {
        "Ticker", "Date", "Market Cap", "Book Equity", "OP", "INV",
        "Ngày công bố BCTC gần nhất",
    }
    if not required.issubset(master.columns):
        missing = sorted(required.difference(master.columns))
        raise ValueError(f"master data is missing columns: {missing}")
    return_columns = {"Close (EOM)", "Monthly Return (%)", *MARKET_COLUMNS}
    if not return_columns.issubset(master.columns):
        missing = sorted(return_columns.difference(master.columns))
        raise ValueError(f"master data is missing return columns: {missing}")
    master = master.copy()
    master["ticker"] = master["Ticker"].astype(str)
    master["source_date"] = pd.to_datetime(master["Date"], errors="coerce")
    master["information_date"] = pd.to_datetime(
        master["Ngày công bố BCTC gần nhất"], errors="coerce"
    )
    for source, target in {
        "Close (EOM)": "close",
        "Market Cap": "market_cap",
        "Book Equity": "book_equity",
        "OP": "operating_profitability",
        "INV": "investment",
    }.items():
        master[target] = _numeric(master[source])
    master["reported_return"] = _numeric(master["Monthly Return (%)"]) / 100.0
    for name in MARKET_COLUMNS:
        master[name] = _numeric(master[name]) / 100.0

    event_columns = [
        "ticker", "information_date", "source_date", "book_equity",
        "operating_profitability", "investment",
    ]
    event_source = master[event_columns].dropna(subset=["ticker", "information_date"]).copy()
    conflict_rows: list[dict] = []
    for (ticker, info_date), group in event_source.groupby(["ticker", "information_date"]):
        conflicts = {
            name: int(group[name].dropna().nunique())
            for name in ["book_equity", "operating_profitability", "investment"]
        }
        if any(value > 1 for value in conflicts.values()):
            conflict_rows.append({
                "ticker": ticker,
                "information_date": info_date,
                **{f"{name}_unique": value for name, value in conflicts.items()},
            })
    events = (
        event_source.sort_values("source_date")
        .groupby(["ticker", "information_date"], as_index=False)
        .last()
        .sort_values(["ticker", "information_date"])
    )
    if conflict_rows:
        conflict_keys = pd.DataFrame(conflict_rows)[["ticker", "information_date"]]
        conflict_keys["event_conflict"] = True
        events = events.merge(
            conflict_keys, on=["ticker", "information_date"], how="left",
            validate="one_to_one",
        )
        events["event_conflict"] = (
            events["event_conflict"].astype("boolean").fillna(False).astype(bool)
        )
    else:
        events["event_conflict"] = False

    monthly_caps = master[["ticker", "source_date", "market_cap"]].dropna(
        subset=["ticker", "source_date"]
    )
    monthly_caps = monthly_caps.assign(month=monthly_caps["source_date"].dt.to_period("M"))
    monthly_caps = (
        monthly_caps.sort_values("source_date")
        .groupby(["month", "ticker"], as_index=False)
        .tail(1)[["month", "ticker", "market_cap"]]
    )

    monthly_prices = master[
        ["ticker", "source_date", "close", "reported_return"]
    ].dropna(
        subset=["ticker", "source_date"]
    )
    monthly_prices = monthly_prices.assign(
        month=monthly_prices["source_date"].dt.to_period("M")
    )
    monthly_prices = (
        monthly_prices.sort_values("source_date")
        .groupby(["month", "ticker"], as_index=False)
        .tail(1)[["month", "ticker", "close", "reported_return"]]
        .sort_values(["ticker", "month"])
    )
    monthly_prices["previous_close"] = monthly_prices.groupby("ticker")["close"].shift()
    month_number = monthly_prices["month"].astype("int64")
    previous_month_number = month_number.groupby(monthly_prices["ticker"]).shift()
    consecutive = month_number.sub(previous_month_number).eq(1)
    monthly_prices["price_return"] = (
        monthly_prices["close"] / monthly_prices["previous_close"] - 1.0
    ).where(consecutive)
    monthly_prices["date"] = monthly_prices["month"].dt.to_timestamp("M")

    market_source = master[["source_date", *MARKET_COLUMNS]].dropna(
        subset=["source_date"]
    )
    market_source = market_source.assign(
        month=market_source["source_date"].dt.to_period("M")
    )
    market_monthly = (
        market_source.sort_values("source_date")
        .groupby("month", as_index=False)
        .tail(1)[["month", *MARKET_COLUMNS]]
        .sort_values("month")
    )
    market_monthly["date"] = market_monthly["month"].dt.to_timestamp("M")

    sectors = pd.DataFrame(columns=["ticker", "sector"])
    if len(sector_raw.columns) >= 4:
        sectors = sector_raw.iloc[:, [0, 3]].copy()
        sectors.columns = ["ticker", "sector"]
        sectors = sectors.dropna(subset=["ticker"])
        sectors["ticker"] = sectors["ticker"].astype(str)
        sectors = sectors.drop_duplicates("ticker", keep="last")

    rf = rf.iloc[1:].copy() if pd.isna(rf.iloc[0, 0]) else rf.copy()
    rf.columns = ["date", "annual_yield_percent"]
    rf["date"] = pd.to_datetime(rf["date"], errors="coerce")
    rf["annual_yield_percent"] = _numeric(rf["annual_yield_percent"])
    rf = rf.dropna().sort_values("date")
    rf["month"] = rf["date"].dt.to_period("M")
    rf_monthly = rf.groupby("month", as_index=False).tail(1).copy()
    rf_monthly["RF"] = annual_yield_percent_to_monthly(
        rf_monthly["annual_yield_percent"]
    )
    rf_monthly["date"] = rf_monthly["month"].dt.to_timestamp("M")
    rf_monthly = rf_monthly.set_index("date")[["RF", "annual_yield_percent"]]
    return (
        events,
        monthly_caps,
        monthly_prices,
        market_monthly,
        sectors,
        rf_monthly,
        pd.DataFrame(conflict_rows),
    )


def reconcile_period_returns(
    period_returns: pd.DataFrame,
    monthly_prices: pd.DataFrame,
) -> pd.DataFrame:
    """Prefer reproducible price returns while preserving supplied returns for audit."""
    reconciled = period_returns.rename(columns={"return": "reported_return"}).merge(
        monthly_prices[["ticker", "date", "close", "previous_close", "price_return"]],
        on=["ticker", "date"],
        how="left",
        validate="many_to_one",
    )
    reconciled["return"] = reconciled["price_return"].combine_first(
        reconciled["reported_return"]
    )
    reconciled["return_source"] = np.where(
        reconciled["price_return"].notna(), "close_eom", "reported_fallback"
    )
    reconciled["reported_minus_price_return"] = (
        reconciled["reported_return"] - reconciled["price_return"]
    )
    return reconciled


def build_annual_july_panel(
    supplied_periods: pd.DataFrame,
    supplied_membership: pd.DataFrame,
    monthly_prices: pd.DataFrame,
    market_monthly: pd.DataFrame,
    *,
    include_incomplete: bool = False,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Build June formation and July-to-June holding panels from supplied data."""
    june_periods = supplied_periods.loc[
        supplied_periods["formation_date"].dt.month.eq(6)
    ].copy()
    if june_periods.empty:
        raise ValueError("no June formation memberships were found")

    available_market_months = set(market_monthly["month"].dropna())
    period_rows: list[dict] = []
    membership_blocks: list[pd.DataFrame] = []
    return_blocks: list[pd.DataFrame] = []

    for source in june_periods.itertuples(index=False):
        formation_date = pd.Timestamp(source.formation_date)
        holding_start = formation_date + pd.offsets.MonthEnd(1)
        holding_end = formation_date + pd.offsets.MonthEnd(12)
        holding_months = pd.period_range(holding_start, holding_end, freq="M")
        observed_months = sum(month in available_market_months for month in holding_months)
        complete = observed_months == 12
        formation_year = int(formation_date.year)
        period_rows.append({
            "period": formation_year,
            "source_period": int(source.Ky),
            "formation_date": formation_date,
            "holding_start": holding_start,
            "holding_end": holding_end,
            "scheduled_months": 12,
            "observed_market_months": observed_months,
            "complete": complete,
        })
        if not complete and not include_incomplete:
            continue

        members = supplied_membership.loc[
            supplied_membership["period"].eq(int(source.Ky))
        ].copy()
        if members.empty:
            raise ValueError(f"missing membership for supplied period {source.Ky}")
        members["source_period"] = members["period"]
        members["period"] = formation_year
        members["formation_date"] = formation_date
        members["holding_start"] = holding_start
        members["holding_end"] = holding_end
        members["complete"] = complete
        membership_blocks.append(members)

        grid = pd.MultiIndex.from_product(
            [members["ticker"].unique(), holding_months],
            names=["ticker", "month"],
        ).to_frame(index=False)
        grid["period"] = formation_year
        grid["date"] = grid["month"].dt.to_timestamp("M")
        grid = grid.merge(
            monthly_prices[["ticker", "month", "reported_return"]],
            on=["ticker", "month"],
            how="left",
            validate="one_to_one",
        )
        grid = grid.merge(
            market_monthly[["month", *MARKET_COLUMNS]],
            on="month",
            how="left",
            validate="many_to_one",
        )
        grid = grid.rename(columns={"reported_return": "return"})
        return_blocks.append(
            grid[["period", "ticker", "date", "return", *MARKET_COLUMNS]]
        )

    annual_periods = pd.DataFrame(period_rows).sort_values("period").reset_index(drop=True)
    membership = (
        pd.concat(membership_blocks, ignore_index=True)
        if membership_blocks else pd.DataFrame()
    )
    returns = (
        pd.concat(return_blocks, ignore_index=True)
        if return_blocks else pd.DataFrame()
    )
    return annual_periods, membership, returns


def build_point_in_time_formations(
    membership: pd.DataFrame,
    events: pd.DataFrame,
    sectors: pd.DataFrame | None = None,
    *,
    exclude_financials: bool = False,
) -> pd.DataFrame:
    """Attach the latest announced accounting information to each formation row."""
    formation = membership.copy()
    events = events.copy()
    if "event_conflict" not in events.columns:
        events["event_conflict"] = False
    matched: list[pd.DataFrame] = []
    event_groups = {ticker: group for ticker, group in events.groupby("ticker")}
    for ticker, left in formation.groupby("ticker", sort=False):
        right = event_groups.get(ticker)
        left = left.sort_values("formation_date")
        if right is None or right.empty:
            for name in [
                "information_date", "book_equity", "operating_profitability", "investment"
            ]:
                left[name] = pd.NaT if name == "information_date" else np.nan
            left["event_conflict"] = False
            matched.append(left)
            continue
        joined = pd.merge_asof(
            left,
            right.drop(columns=["source_date"]).sort_values("information_date"),
            left_on="formation_date",
            right_on="information_date",
            direction="backward",
        )
        joined["ticker"] = ticker
        matched.append(joined)
    formation = pd.concat(matched, ignore_index=True)
    formation["event_conflict"] = (
        formation["event_conflict"].astype("boolean").fillna(False).astype(bool)
    )
    if sectors is not None and not sectors.empty:
        formation = formation.merge(sectors, on="ticker", how="left", validate="many_to_one")
    else:
        formation["sector"] = np.nan
    formation["book_to_market"] = (
        formation["book_equity"] / formation["formation_market_cap"]
    )
    formation["is_financial"] = formation["sector"].eq("Financials")
    formation["valid_size"] = (
        formation["formation_market_cap"].notna()
        & np.isfinite(formation["formation_market_cap"])
        & formation["formation_market_cap"].gt(0)
    )
    formation["valid_book_equity"] = (
        formation["book_equity"].notna()
        & np.isfinite(formation["book_equity"])
        & formation["book_equity"].gt(0)
    )
    allowed_sector = ~formation["is_financial"] if exclude_financials else True
    formation["eligible_bm"] = (
        formation["valid_size"]
        & formation["valid_book_equity"]
        & formation["book_to_market"].notna()
        & np.isfinite(formation["book_to_market"])
        & formation["book_to_market"].gt(0)
        & ~formation["event_conflict"]
        & allowed_sector
    )
    formation["eligible_op"] = (
        formation["eligible_bm"]
        & formation["operating_profitability"].notna()
        & np.isfinite(formation["operating_profitability"])
    )
    formation["eligible_inv"] = (
        formation["eligible_bm"]
        & formation["investment"].notna()
        & np.isfinite(formation["investment"])
    )
    formation["look_ahead"] = formation["information_date"].gt(formation["formation_date"])
    if formation["look_ahead"].any():
        raise AssertionError("point-in-time join selected information announced after formation")

    def reason(row, field):
        if exclude_financials and row["is_financial"]:
            return "financial_sector_excluded"
        if not row["valid_size"]:
            return "missing_or_nonpositive_size"
        if pd.isna(row["information_date"]):
            return "no_statement_available_at_formation"
        if row["event_conflict"]:
            return "conflicting_fundamental_event"
        if not row["valid_book_equity"]:
            return "missing_or_nonpositive_book_equity"
        if field == "bm" and not row["eligible_bm"]:
            return "missing_or_invalid_book_to_market"
        if field == "op" and pd.isna(row["operating_profitability"]):
            return "missing_operating_profitability"
        if field == "inv" and pd.isna(row["investment"]):
            return "missing_investment"
        return "eligible"

    for field in ("bm", "op", "inv"):
        formation[f"reason_{field}"] = formation.apply(reason, axis=1, field=field)
    return formation.sort_values(["period", "ticker"]).reset_index(drop=True)


def _lagged_cap_weights(
    monthly_caps: pd.DataFrame,
    holding_months: pd.PeriodIndex,
    tickers: pd.Index,
) -> pd.DataFrame:
    pivot = monthly_caps.pivot(index="month", columns="ticker", values="market_cap")
    full_months = pd.period_range(pivot.index.min(), pivot.index.max(), freq="M")
    pivot = pivot.reindex(full_months).shift(1)
    return pivot.reindex(index=holding_months, columns=tickers)


def _sort_block(
    period: int,
    sort_name: str,
    formation: pd.DataFrame,
    returns: pd.DataFrame,
    characteristic: str,
    eligible: str,
    labels: tuple[str, str, str, str, str, str],
    weights: pd.Series | pd.DataFrame,
) -> tuple[pd.DataFrame | None, pd.DataFrame, pd.DataFrame]:
    chars = formation.loc[formation[eligible]].set_index("ticker")
    tickers = chars.index.intersection(returns.columns)
    if len(tickers) < 6:
        return None, pd.DataFrame(), pd.DataFrame()
    size = chars.loc[tickers, "formation_market_cap"].astype(float)
    values = chars.loc[tickers, characteristic].astype(float)
    groups = portfolio_sort(size, values, labels=labels)
    try:
        portfolios = portfolio_returns(
            returns.reindex(columns=tickers), groups, weights, required_groups=labels
        )
    except ValueError:
        return None, pd.DataFrame(), pd.DataFrame()
    assignments = pd.DataFrame({
        "period": period,
        "sort": sort_name,
        "ticker": tickers,
        "portfolio": groups.reindex(tickers).to_numpy(),
        "formation_market_cap": size.reindex(tickers).to_numpy(),
        "characteristic": values.reindex(tickers).to_numpy(),
    })
    counts = (
        assignments.groupby(["period", "sort", "portfolio"], as_index=False)
        .size()
        .rename(columns={"size": "ticker_count"})
    )
    return portfolios, assignments, counts


def construct_period_factors(
    period_returns: pd.DataFrame,
    formation: pd.DataFrame,
    rf_monthly: pd.DataFrame,
    monthly_caps: pd.DataFrame,
    *,
    market_proxy: str = "VNINDEX",
    weighting: str = "lagged_market_cap",
) -> PeriodFactorResult:
    """Construct monthly factors using the selected VN100 holding periods."""
    if market_proxy not in MARKET_COLUMNS:
        raise ValueError(f"market_proxy must be one of {MARKET_COLUMNS}")
    if weighting not in {"formation", "lagged_market_cap"}:
        raise ValueError("weighting must be 'formation' or 'lagged_market_cap'")
    factor_blocks: list[pd.DataFrame] = []
    assignment_blocks: list[pd.DataFrame] = []
    count_blocks: list[pd.DataFrame] = []
    quality_rows: list[dict] = []

    for period, block in period_returns.groupby("period", sort=True):
        block = block.copy()
        block["month"] = block["date"].dt.to_period("M")
        returns = block.pivot(index="month", columns="ticker", values="return")
        chars = formation.loc[formation["period"].eq(period)].copy()
        formation_weights = chars.set_index("ticker")["formation_market_cap"].astype(float)
        weights: pd.Series | pd.DataFrame
        if weighting == "formation":
            weights = formation_weights
        else:
            weights = _lagged_cap_weights(monthly_caps, returns.index, returns.columns)

        bm_labels = ("SL", "SN", "SH", "BL", "BN", "BH")
        bm, bm_assign, bm_counts = _sort_block(
            period, "BM", chars, returns, "book_to_market", "eligible_bm",
            bm_labels, weights,
        )
        op_labels = ("SW", "SN", "SR", "BW", "BN", "BR")
        op, op_assign, op_counts = _sort_block(
            period, "OP", chars, returns, "operating_profitability", "eligible_op",
            op_labels, weights,
        )
        inv_labels = ("SC", "SN", "SA", "BC", "BN", "BA")
        inv, inv_assign, inv_counts = _sort_block(
            period, "INV", chars, returns, "investment", "eligible_inv",
            inv_labels, weights,
        )
        assignment_blocks.extend([x for x in (bm_assign, op_assign, inv_assign) if not x.empty])
        count_blocks.extend([x for x in (bm_counts, op_counts, inv_counts) if not x.empty])

        factors = pd.DataFrame(index=returns.index)
        if bm is not None:
            factors["SMB"] = bm[["SL", "SN", "SH"]].mean(axis=1) - bm[
                ["BL", "BN", "BH"]
            ].mean(axis=1)
            factors["HML"] = bm[["SH", "BH"]].mean(axis=1) - bm[["SL", "BL"]].mean(axis=1)
        if op is not None:
            factors["RMW"] = op[["SR", "BR"]].mean(axis=1) - op[["SW", "BW"]].mean(axis=1)
        if inv is not None:
            factors["CMA"] = inv[["SC", "BC"]].mean(axis=1) - inv[["SA", "BA"]].mean(axis=1)
        if bm is not None and op is not None and inv is not None:
            size_spreads = pd.concat([
                bm[["SL", "SN", "SH"]].mean(axis=1) - bm[["BL", "BN", "BH"]].mean(axis=1),
                op[["SW", "SN", "SR"]].mean(axis=1) - op[["BW", "BN", "BR"]].mean(axis=1),
                inv[["SC", "SN", "SA"]].mean(axis=1) - inv[["BC", "BN", "BA"]].mean(axis=1),
            ], axis=1)
            factors["SMB_FF5"] = size_spreads.mean(axis=1)

        market_by_month = block.groupby("month")[market_proxy].agg(["min", "max", "first"])
        inconsistent_market = int((market_by_month["max"] - market_by_month["min"]).abs().gt(1e-12).sum())
        dates = factors.index.to_timestamp("M")
        factors.index = dates
        factors["MARKET"] = market_by_month["first"].reindex(dates.to_period("M")).to_numpy()
        factors["RF"] = rf_monthly["RF"].reindex(dates).to_numpy()
        factors["MKT_RF"] = factors["MARKET"] - factors["RF"]
        factors["period"] = period
        factor_blocks.append(factors)
        quality_rows.append({
            "period": period,
            "months": int(returns.index.nunique()),
            "return_rows": int(len(block)),
            "return_outliers_abs_gt_100pct": int(block["return"].abs().gt(1.0).sum()),
            "reported_return_outliers_abs_gt_100pct": int(
                block["reported_return"].abs().gt(1.0).sum()
            ),
            "return_discrepancies_abs_gt_1pp": int(
                block["reported_minus_price_return"].abs().gt(0.01).sum()
            ),
            "return_discrepancies_abs_gt_10pp": int(
                block["reported_minus_price_return"].abs().gt(0.10).sum()
            ),
            "reported_return_fallbacks": int(
                block["return_source"].eq("reported_fallback").sum()
            ),
            "market_return_inconsistent_months": inconsistent_market,
            "eligible_bm": int(chars["eligible_bm"].sum()),
            "eligible_op": int(chars["eligible_op"].sum()),
            "eligible_inv": int(chars["eligible_inv"].sum()),
            "bm_sort_constructed": bm is not None,
            "op_sort_constructed": op is not None,
            "inv_sort_constructed": inv is not None,
        })

    if not factor_blocks:
        raise ValueError("no complete VN100 periods could be constructed")
    factors = pd.concat(factor_blocks).sort_index()
    factors.index.name = "Date"
    ordered = ["MKT_RF", "SMB", "HML", "SMB_FF5", "RMW", "CMA", "RF", "MARKET", "period"]
    factors = factors.reindex(columns=ordered)
    assignments = pd.concat(assignment_blocks, ignore_index=True) if assignment_blocks else pd.DataFrame()
    counts = pd.concat(count_blocks, ignore_index=True) if count_blocks else pd.DataFrame()
    quality = pd.DataFrame(quality_rows)
    return PeriodFactorResult(
        factors=factors,
        formation_audit=formation,
        group_assignments=assignments,
        group_counts=counts,
        returns_panel=period_returns,
        data_quality=quality,
    )


def build_vn_period_factors(
    period_archive: str | Path,
    master_archive: str | Path,
    *,
    rf_tenor: str = "1Y",
    market_proxy: str = "VNINDEX",
    weighting: str = "lagged_market_cap",
    schedule: str = "annual_july",
    include_incomplete: bool = False,
    exclude_financials: bool = False,
) -> tuple[PeriodFactorResult, pd.DataFrame, pd.DataFrame]:
    """Load, align, audit, and construct factors from the two supplied archives."""
    if schedule not in {"annual_july", "supplied_semiannual"}:
        raise ValueError("schedule must be 'annual_july' or 'supplied_semiannual'")
    supplied_periods, supplied_membership, supplied_returns = load_period_archive(
        period_archive,
        include_incomplete=True if schedule == "annual_july" else include_incomplete,
    )
    (
        events,
        monthly_caps,
        monthly_prices,
        market_monthly,
        sectors,
        rf_monthly,
        event_conflicts,
    ) = load_master_archive(master_archive, rf_tenor=rf_tenor)
    if schedule == "annual_july":
        periods, membership, returns = build_annual_july_panel(
            supplied_periods,
            supplied_membership,
            monthly_prices,
            market_monthly,
            include_incomplete=include_incomplete,
        )
    else:
        periods, membership, returns = (
            supplied_periods,
            supplied_membership,
            supplied_returns,
        )
    returns = reconcile_period_returns(returns, monthly_prices)
    formation = build_point_in_time_formations(
        membership, events, sectors, exclude_financials=exclude_financials
    )
    result = construct_period_factors(
        returns, formation, rf_monthly, monthly_caps,
        market_proxy=market_proxy, weighting=weighting,
    )
    return result, periods, event_conflicts
