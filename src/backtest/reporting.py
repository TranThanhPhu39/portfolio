"""Generate a standalone HTML report and its SVG chart assets."""

import html

import numpy as np
import pandas as pd


def export_report(out, outputs, table, benchmark, cfg):
    from .charts import allocation_chart, monthly_heatmap, svg_plot

    escape = html.escape

    def card(title, description, body):
        return (
            f'<section class="card"><h2>{escape(title)}</h2>'
            f'<p class="muted">{escape(description)}</p>{body}</section>'
        )

    first = next(iter(next(iter(outputs.values())).values()))
    dates = first.periods.index
    status = (
        "DỮ LIỆU GIẢ LẬP · KHÔNG DÙNG LÀM KẾT QUẢ NGHIÊN CỨU"
        if cfg["synthetic"]
        else "KẾT QUẢ BACKTEST · TẬP CỔ PHIẾU CỐ ĐỊNH"
    )
    sections = [
        "<header>"
        f'<span class="badge">{status}</span>'
        '<h1>Hiệu quả danh mục đầu tư</h1>'
        '<p>Từ phân bổ danh mục đến hiệu quả sau chi phí giao dịch.</p>'
        "</header>"
        '<div class="stats">'
        f'<div><span>Chiến lược</span><strong>{len(outputs)}</strong></div>'
        f'<div><span>Tháng ngoài mẫu</span><strong>{len(dates)}</strong></div>'
        f'<div><span>Kịch bản phí</span><strong>{len(cfg["rates"])}</strong></div>'
        "</div>"
    ]
    assumptions = (
        '<div class="notes">'
        f'<div><h3>Dữ liệu và phạm vi</h3><p>{escape(cfg["universe_selection"])}</p></div>'
        f'<div><h3>Thời điểm giao dịch</h3><p>{escape(cfg["execution_assumption"])}</p></div>'
        '<div><h3>Quy ước chi phí</h3><p>Phí tính trên từng chiều mua/bán và được trả từ vốn danh mục.</p></div>'
        "</div>"
    )
    sections.append(card("Cách đọc báo cáo", "Các giả định của lần chạy.", assumptions))

    sharpe_file = out / "05_sharpe_assets_comparison.csv"
    if sharpe_file.exists():
        detail = pd.read_csv(sharpe_file)
        visible_columns = [
            column
            for column in [
                "name",
                "sharpe_annualized",
                "mean_excess_monthly",
                "excess_sd_monthly",
                "months",
            ]
            if column in detail.columns
        ]
        visible = detail[visible_columns].copy()
        for column in ["sharpe_annualized", "mean_excess_monthly", "excess_sd_monthly"]:
            if column in visible:
                visible[column] = visible[column].map(
                    lambda value: f"{value:.6f}" if np.isfinite(value) else "—"
                )
        visible = visible.rename(
            columns={
                "name": "Danh mục / mã",
                "sharpe_annualized": "Sharpe năm",
                "mean_excess_monthly": "Lợi suất vượt RF TB tháng",
                "excess_sd_monthly": "SD mẫu lợi suất vượt RF",
                "months": "Số tháng",
            }
        )
        sections.append(
            card(
                "05 · Sharpe từng mã và danh mục MaxSharpe",
                "So sánh cùng kỳ, cùng RF và chưa trừ phí.",
                '<div class="table-wrap">'
                + visible.to_html(index=False, border=0)
                + "</div>",
            )
        )

    weights_file = out / "03_weights.csv"
    if weights_file.exists():
        allocation = allocation_chart(pd.read_csv(weights_file, index_col=0))
        (out / "allocation.svg").write_text(allocation, encoding="utf-8")
        sections.append(
            card(
                "Phân bổ tại cửa sổ đầu tiên",
                "Mỗi thanh bằng 100% vốn.",
                allocation,
            )
        )

    frontier_file = out / "04_frontier.svg"
    if frontier_file.exists():
        sections.append(
            card(
                "Rủi ro và lợi suất kỳ vọng",
                "Đường biên hiệu quả tại cửa sổ huấn luyện đầu tiên.",
                frontier_file.read_text(encoding="utf-8"),
            )
        )

    sharpe_series = []
    for name in outputs:
        rows = table[(table.strategy == name) & (table.name == "strategy")].sort_values(
            "transaction_cost_rate"
        )
        sharpe_series.append(
            (name, list(zip(rows.transaction_cost_rate, rows.sharpe)))
        )
    benchmark_sharpe = float(table.loc[table.name == "benchmark", "sharpe"].iloc[0])
    sharpe_chart = svg_plot(
        sharpe_series,
        "Sharpe theo mức phí",
        "Phí trên mỗi chiều giao dịch",
        "Sharpe năm",
        kind="bar",
        x_percent=True,
        benchmark=benchmark_sharpe,
    )
    (out / "sharpe_vs_fee.svg").write_text(sharpe_chart, encoding="utf-8")
    sections.append(
        card(
            "So sánh độ nhạy với chi phí",
            "Đường nét đứt là Sharpe của benchmark.",
            sharpe_chart,
        )
    )

    heat_series = {}
    for name, runs in outputs.items():
        selected_rate = 0.0025 if 0.0025 in runs else sorted(runs)[len(runs) // 2]
        heat_series[name] = runs[selected_rate].periods.net_return
    heatmap = monthly_heatmap(heat_series)
    (out / "monthly_returns_heatmap.svg").write_text(heatmap, encoding="utf-8")
    sections.append(
        card("Lợi suất từng tháng", "Lợi suất sau phí theo chiến lược.", heatmap)
    )

    for name, results in outputs.items():
        curves = []
        for rate, result in results.items():
            values = np.r_[1.0, result.periods.end_value.to_numpy()]
            curves.append((f"Phí {rate * 100:.2f}%", list(enumerate(values))))
        benchmark_values = np.r_[
            1.0, (1 + benchmark.reindex(dates)).cumprod().to_numpy()
        ]
        curves.append((cfg["benchmark_name"], list(enumerate(benchmark_values))))
        equity = svg_plot(
            curves,
            f"{name} · Giá trị danh mục",
            "Tháng ngoài mẫu",
            "Giá trị / vốn ban đầu",
        )
        selected_rate = 0.0025 if 0.0025 in results else sorted(results)[len(results) // 2]
        values = np.r_[1.0, results[selected_rate].periods.end_value.to_numpy()]
        drawdowns = [
            (
                f"{name} · phí {selected_rate * 100:.2f}%",
                list(enumerate(values / np.maximum.accumulate(values) - 1)),
            ),
            (
                cfg["benchmark_name"],
                list(
                    enumerate(
                        benchmark_values / np.maximum.accumulate(benchmark_values) - 1
                    )
                ),
            ),
        ]
        drawdown = svg_plot(
            drawdowns,
            f"{name} · Sụt giảm từ đỉnh",
            "Tháng ngoài mẫu",
            "Drawdown (%)",
            kind="area",
            y_percent=True,
        )
        (out / f"{name}_equity.svg").write_text(equity, encoding="utf-8")
        (out / f"{name}_drawdown.svg").write_text(drawdown, encoding="utf-8")
        sections.append(card(name, "Giá trị danh mục và drawdown.", equity + drawdown))

    formatted = table.copy()
    formatted = formatted.rename(
        columns={
            "name": "Loại",
            "strategy": "Chiến lược",
            "transaction_cost_rate": "Phí / chiều",
            "months": "Số tháng",
            "sharpe": "Sharpe năm",
            "cagr": "CAGR",
            "max_drawdown": "Drawdown lớn nhất",
            "total_return": "Lợi suất toàn kỳ",
            "total_fee": "Tổng phí / vốn đầu",
            "total_turnover_two_way": "Tổng turnover hai chiều",
        }
    )
    sections.append(
        card(
            "Bảng kết quả đầy đủ",
            "CSV gốc giữ nguyên độ chính xác.",
            '<div class="table-wrap">'
            + formatted.to_html(index=False, border=0)
            + "</div>",
        )
    )
    css = """
*{box-sizing:border-box}body{margin:0;background:#f1f5f9;color:#172b4d;font:16px/1.6 Arial,sans-serif}
main{max-width:1200px;margin:auto;padding:36px 24px}h1{font-size:36px}.badge{display:inline-block;background:#fff3d6;
color:#815100;border:1px solid #f6d88a;border-radius:8px;padding:8px 14px;font-size:12px;font-weight:bold}
.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin:22px 0}.stats div,.card{background:white;
border:1px solid #dce5ef;border-radius:16px;padding:24px}.stats span{display:block;color:#63748b}.stats strong{font-size:28px}
.card{margin-bottom:24px}.muted{color:#63748b}.notes{display:grid;grid-template-columns:repeat(3,1fr);gap:20px}
svg{display:block;width:100%;height:auto;max-width:1050px;margin:12px auto}.table-wrap{overflow-x:auto}table{border-collapse:collapse;
width:100%;font-size:13px}th{background:#eef3fa}td,th{padding:10px;border-bottom:1px solid #e7edf4;text-align:right}
td:first-child,th:first-child{text-align:left}@media(max-width:700px){.stats,.notes{grid-template-columns:1fr}}
"""
    page = (
        '<!doctype html><html lang="vi"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>Báo cáo danh mục</title><style>{css}</style></head>"
        f'<body><main>{"".join(sections)}</main></body></html>'
    )
    (out / "report.html").write_text(page, encoding="utf-8")
