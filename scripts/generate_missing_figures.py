"""Generate the three research figures that are not produced by the main runners.

The figures are intentionally derived only from versioned project CSV files.  Both
SVG (for the report) and high-resolution PNG (for Word) are exported.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.portfolio.markowitz import estimate, frontier, portfolio_stats, solve


COLORS = {
    "SMB": "#2563eb",
    "HML": "#dc2626",
    "RMW": "#059669",
    "CMA": "#d97706",
    "frontier": "#2563eb",
    "MinVariance": "#059669",
    "MaxSharpe": "#dc2626",
    "EqualWeight": "#7c3aed",
}


def set_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.titlesize": 14,
            "axes.titleweight": "bold",
            "axes.labelsize": 10,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.alpha": 0.22,
            "grid.linewidth": 0.7,
            "legend.frameon": False,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
        }
    )


def save_figure(fig: plt.Figure, output_dir: Path, stem: str) -> None:
    fig.savefig(output_dir / f"{stem}.svg", bbox_inches="tight")
    fig.savefig(output_dir / f"{stem}.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def factor_cumulative_figure(output_dir: Path) -> None:
    path = ROOT / "outputs" / "vn_period_factors" / "vn100_factors_monthly.csv"
    data = pd.read_csv(path, parse_dates=["Date"]).set_index("Date").sort_index()
    factors = ["SMB", "HML", "RMW", "CMA"]

    fig, ax = plt.subplots(figsize=(10.2, 5.7))
    start_labels = []
    for factor in factors:
        observed = pd.to_numeric(data[factor], errors="coerce").dropna()
        cumulative = (1.0 + observed).cumprod()
        # Each factor is rebased to 1.0 at its first available observation.
        cumulative = pd.concat(
            [pd.Series([1.0], index=[observed.index[0] - pd.offsets.MonthEnd(1)]), cumulative]
        )
        ax.plot(
            cumulative.index,
            cumulative.values,
            label=factor,
            color=COLORS[factor],
            linewidth=2.1,
        )
        start_labels.append(f"{factor}: {observed.index[0]:%m/%Y}")

    ax.axhline(1.0, color="#64748b", linewidth=0.9, linestyle="--")
    ax.set_title("Lợi suất tích lũy của các nhân tố VN100")
    ax.set_ylabel("Giá trị tích lũy (khởi điểm = 1)")
    ax.set_xlabel("Tháng")
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.legend(ncol=4, loc="upper left")
    ax.text(
        0,
        -0.19,
        "Thời điểm bắt đầu chuỗi: " + "; ".join(start_labels) + ".",
        transform=ax.transAxes,
        fontsize=8.5,
        color="#475569",
    )
    fig.tight_layout()
    save_figure(fig, output_dir, "factor_cumulative_returns")


def model_fit_alpha_figure(output_dir: Path) -> None:
    path = ROOT / "outputs" / "vn_econometrics_baseline" / "table5_style_summary.csv"
    data = pd.read_csv(path)
    models = data["model"].tolist()
    x = np.arange(len(models))

    fig, ax_r2 = plt.subplots(figsize=(8.8, 5.5))
    width = 0.34
    r2_pct = data["mean_r_squared"].to_numpy(float) * 100
    alpha_pct = data["mean_abs_alpha_pct"].to_numpy(float)
    bars_r2 = ax_r2.bar(
        x - width / 2,
        r2_pct,
        width,
        color="#2563eb",
        label="R² trung bình",
    )
    ax_r2.set_ylabel("R² trung bình (%)", color="#1d4ed8")
    ax_r2.tick_params(axis="y", labelcolor="#1d4ed8")
    ax_r2.set_ylim(0, max(r2_pct) * 1.32)
    ax_r2.set_xticks(x, models)

    ax_alpha = ax_r2.twinx()
    ax_alpha.grid(False)
    bars_alpha = ax_alpha.bar(
        x + width / 2,
        alpha_pct,
        width,
        color="#dc2626",
        label="|alpha| trung bình",
    )
    ax_alpha.set_ylabel("|alpha| trung bình (%/tháng)", color="#b91c1c")
    ax_alpha.tick_params(axis="y", labelcolor="#b91c1c")
    ax_alpha.set_ylim(0, max(alpha_pct) * 1.42)
    ax_alpha.spines["right"].set_visible(True)

    ax_r2.bar_label(bars_r2, labels=[f"{v:.1f}%" for v in r2_pct], padding=3)
    ax_alpha.bar_label(bars_alpha, labels=[f"{v:.3f}%" for v in alpha_pct], padding=3)
    handles = [bars_r2, bars_alpha]
    ax_r2.legend(handles, [h.get_label() for h in handles], loc="upper left")
    ax_r2.set_title("Khả năng giải thích và sai lệch định giá theo mô hình")
    ax_r2.text(
        0,
        -0.16,
        "Mẫu chung: 30 cổ phiếu, 60 tháng (07/2021–06/2026).",
        transform=ax_r2.transAxes,
        fontsize=8.5,
        color="#475569",
    )
    fig.tight_layout()
    save_figure(fig, output_dir, "model_r2_mean_absolute_alpha")


def read_backtest_panel(input_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series]:
    returns_long = pd.read_csv(input_dir / "returns.csv", parse_dates=["date"])
    membership_long = pd.read_csv(input_dir / "membership.csv", parse_dates=["date"])
    rf_data = pd.read_csv(input_dir / "risk_free.csv", parse_dates=["date"])

    returns = returns_long.pivot(index="date", columns="ticker", values="return").sort_index()
    membership_long["member"] = membership_long["member"].astype(str).str.lower().map(
        {"true": True, "false": False, "1": True, "0": False}
    )
    membership = membership_long.pivot(index="date", columns="ticker", values="member")
    membership = membership.reindex(index=returns.index, columns=returns.columns).astype(bool)
    rf = rf_data.set_index("date")["rf_return"].sort_index()
    return returns, membership, rf


def efficient_frontier_figure(output_dir: Path, input_dir: Path) -> None:
    returns, membership, rf = read_backtest_panel(input_dir)
    train_start = pd.Timestamp("2024-05-31")
    train_end = pd.Timestamp("2026-04-30")
    deployment = pd.Timestamp("2026-06-30")
    history = returns.loc[train_start:train_end]
    eligible = membership.loc[deployment] & history.notna().all(axis=0)
    history = history.loc[:, eligible]
    if len(history) != 24 or history.shape[1] < 2:
        raise ValueError("The requested frontier window or eligible universe is incomplete")

    mu, covariance = estimate(history, ridge=1e-8)
    points, weights = frontier(mu, covariance, points=50)
    monthly_rf = float(rf.reindex(history.index).mean())
    portfolios = {
        "MinVariance": solve(mu, covariance, "min_variance"),
        "MaxSharpe": solve(mu, covariance, "max_sharpe", rf=monthly_rf),
        "EqualWeight": pd.Series(1.0 / len(mu), index=mu.index),
    }

    fig, ax = plt.subplots(figsize=(9.2, 5.7))
    ax.plot(
        points["volatility_monthly"] * 100,
        points["expected_return_monthly"] * 100,
        color=COLORS["frontier"],
        linewidth=2.4,
        label="Đường biên hiệu quả",
    )
    rows = []
    for name, portfolio_weights in portfolios.items():
        stats = portfolio_stats(portfolio_weights, mu, covariance, monthly_rf)
        x = stats["volatility_monthly"] * 100
        y = stats["expected_return_monthly"] * 100
        ax.scatter(x, y, s=75, color=COLORS[name], edgecolor="white", linewidth=0.8, zorder=3)
        ax.annotate(
            name,
            (x, y),
            xytext=(7, 7),
            textcoords="offset points",
            fontsize=9,
            color=COLORS[name],
        )
        rows.append({"portfolio": name, **stats})

    ax.set_title("Đường biên hiệu quả long-only và vị trí ba danh mục")
    ax.set_xlabel("Độ lệch chuẩn tháng (%)")
    ax.set_ylabel("Lợi suất kỳ vọng tháng (%)")
    ax.legend(loc="best")
    ax.text(
        0,
        -0.18,
        f"Cửa sổ huấn luyện 05/2024–04/2026; triển khai 06/2026; {history.shape[1]} cổ phiếu đủ dữ liệu.",
        transform=ax.transAxes,
        fontsize=8.5,
        color="#475569",
    )
    fig.tight_layout()
    save_figure(fig, output_dir, "efficient_frontier_2024_05_2026_04")

    points.to_csv(output_dir / "efficient_frontier_2024_05_2026_04.csv", index=False)
    weights.to_csv(output_dir / "efficient_frontier_weights_2024_05_2026_04.csv", index=False)
    pd.DataFrame(rows).to_csv(output_dir / "frontier_portfolio_positions.csv", index=False)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "outputs" / "report_figures",
    )
    parser.add_argument(
        "--backtest-input-dir",
        type=Path,
        default=ROOT / "local_runs" / "vn100_inputs_20261001",
    )
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    set_style()
    factor_cumulative_figure(args.output_dir)
    model_fit_alpha_figure(args.output_dir)
    efficient_frontier_figure(args.output_dir, args.backtest_input_dir)
    print(f"Created report figures in: {args.output_dir.resolve()}")


if __name__ == "__main__":
    main()
