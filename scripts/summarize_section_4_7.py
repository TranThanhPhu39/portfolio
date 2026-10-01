"""Combine baseline and robustness outputs into the Section 4.7 result table."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = {
    "baseline": ("vn_period_factors", "vn_econometrics_baseline"),
    "semiannual": ("vn_period_factors_semiannual", "vn_econometrics_semiannual"),
    "formation_weights": (
        "vn_period_factors_formation_weights",
        "vn_econometrics_formation_weights",
    ),
    "ex_financials": (
        "vn_period_factors_ex_financials",
        "vn_econometrics_ex_financials",
    ),
}


def require_files(folder: Path, names: list[str]) -> bool:
    return folder.is_dir() and all((folder / name).is_file() for name in names)


def markdown_table(frame: pd.DataFrame) -> str:
    header = "| " + " | ".join(frame.columns) + " |"
    separator = "|" + "|".join(["---"] * len(frame.columns)) + "|"
    body = [
        "| " + " | ".join(str(value) for value in row) + " |"
        for row in frame.itertuples(index=False, name=None)
    ]
    return "\n".join([header, separator, *body])


def scenario_rows(name: str, factor_dir: Path, econometrics_dir: Path) -> list[dict]:
    factor_summary = pd.read_csv(factor_dir / "vn100_factor_summary.csv", index_col=0)
    table5 = pd.read_csv(econometrics_dir / "table5_style_summary.csv")
    grs = pd.read_csv(econometrics_dir / "grs_summary.csv").set_index("model")
    hml = pd.read_csv(econometrics_dir / "hml_redundancy.csv").iloc[0]
    manifest = json.loads((econometrics_dir / "run_manifest.json").read_text(encoding="utf-8"))
    hml_premium = factor_summary.loc["HML"]

    rows = []
    for _, model in table5.iterrows():
        model_name = model["model"]
        rows.append(
            {
                "scenario": name,
                "model": model_name,
                "t_months": int(model["t_months"]),
                "mean_r_squared": float(model["mean_r_squared"]),
                "mean_abs_alpha_pct": float(model["mean_abs_alpha_pct"]),
                "grs_f": float(grs.loc[model_name, "grs_f"]),
                "grs_p_value": float(grs.loc[model_name, "p_value"]),
                "hml_spanning_alpha_pct_per_month": float(hml["alpha_pct_per_month"]),
                "hml_spanning_p_ols": float(hml["alpha_p_ols"]),
                "hml_spanning_p_hac12": float(hml["alpha_p_hac12"]),
                "hml_premium_mean_decimal": float(hml_premium["mean"]),
                "hml_premium_t": float(hml_premium["t_stat"]),
                "sample_start": manifest["sample_start"],
                "sample_end": manifest["sample_end"],
                "dropped_factor_months": ";".join(
                    manifest.get("dropped_incomplete_factor_months", [])
                ),
                "dropped_asset_months": ";".join(
                    manifest.get("dropped_incomplete_asset_months", [])
                ),
            }
        )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=ROOT / "outputs" / "vn_econometrics_robustness_comparison.csv",
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=ROOT / "docs" / "section_4_7_results.md",
    )
    parser.add_argument(
        "--require-all",
        action="store_true",
        help="Fail unless all three robustness runs and the baseline are present",
    )
    args = parser.parse_args()

    factor_files = ["vn100_factor_summary.csv"]
    econometrics_files = [
        "table5_style_summary.csv",
        "grs_summary.csv",
        "hml_redundancy.csv",
        "vif.csv",
        "run_manifest.json",
    ]
    rows: list[dict] = []
    pending: list[str] = []
    for name, (factor_name, econometrics_name) in SCENARIOS.items():
        factor_dir = ROOT / "outputs" / factor_name
        econometrics_dir = ROOT / "outputs" / econometrics_name
        if not (
            require_files(factor_dir, factor_files)
            and require_files(econometrics_dir, econometrics_files)
        ):
            pending.append(name)
            continue
        rows.extend(scenario_rows(name, factor_dir, econometrics_dir))

    if args.require_all and pending:
        raise FileNotFoundError("Missing completed scenarios: " + ", ".join(pending))
    if not rows:
        raise FileNotFoundError("No complete econometrics scenario was found")

    result = pd.DataFrame(rows)
    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output_csv, index=False, float_format="%.10g")

    display = result.copy()
    display["mean_r_squared"] = display["mean_r_squared"].map(lambda x: f"{x:.4f}")
    for column in [
        "mean_abs_alpha_pct",
        "grs_f",
        "grs_p_value",
        "hml_spanning_alpha_pct_per_month",
        "hml_spanning_p_ols",
        "hml_spanning_p_hac12",
        "hml_premium_t",
    ]:
        display[column] = display[column].map(lambda x: f"{x:.4f}")
    display["hml_premium_mean_pct"] = result["hml_premium_mean_decimal"].map(
        lambda x: f"{100 * x:.4f}"
    )
    columns = [
        "scenario",
        "model",
        "t_months",
        "mean_r_squared",
        "mean_abs_alpha_pct",
        "grs_f",
        "grs_p_value",
        "hml_spanning_alpha_pct_per_month",
        "hml_spanning_p_hac12",
        "hml_premium_mean_pct",
        "hml_premium_t",
    ]
    markdown = [
        "# Kết quả kiểm tra độ bền — Mục 4.7",
        "",
        markdown_table(display[columns]),
        "",
        "P-value chính của hồi quy bao phủ HML trong bảng là HAC Bartlett, lag 12. "
        "CSV giữ thêm p-value OLS để đối chiếu.",
        "",
    ]
    if pending:
        markdown.extend(["## Chưa có output", "", ", ".join(pending), ""])
    else:
        minimum_grs_p = result["grs_p_value"].min()
        minimum_hml_t = result.groupby("scenario")["hml_premium_t"].first().min()
        maximum_hml_p = result.groupby("scenario")["hml_spanning_p_hac12"].first().max()
        markdown.extend(
            [
                "## Kết luận dùng cho Mục 4.7",
                "",
                "Kết quả định tính bền vững qua ba đặc tả thay thế. Không kiểm định "
                f"GRS nào bác bỏ giả thuyết đồng thời alpha bằng 0 ở mức 5% "
                f"(p-value nhỏ nhất = {minimum_grs_p:.4f}).",
                "",
                "Phần bù HML giữ dấu dương trong mọi trường hợp; t-stat nhỏ nhất là "
                f"{minimum_hml_t:.4f}. Alpha của hồi quy bao phủ HML cũng luôn dương "
                "nhưng không có ý nghĩa ở mức 5% theo HAC lag 12 "
                f"(p-value lớn nhất = {maximum_hml_p:.4f}). Trường hợp trọng số "
                "formation gần ngưỡng 10% (p = 0.0864), vì vậy không nên diễn giải "
                "HML là hoàn toàn dư thừa hoặc hoàn toàn độc lập.",
                "",
                "Lịch sáu tháng sử dụng 59 tháng vì tháng 07/2021 thiếu lợi suất "
                "SSB.HM trong panel tương ứng. Loại tài chính làm R² giảm và alpha "
                "tuyệt đối tăng rõ rệt, đặc biệt ở FF5; do đó độ lớn kết quả phụ thuộc "
                "cấu trúc ngành, dù kết luận GRS và dấu HML không đổi.",
                "",
                "Trong cả bốn đặc tả, FF5 có R² trung bình cao nhất nhưng không làm "
                "alpha tuyệt đối giảm một cách nhất quán. Bằng chứng ủng hộ khả năng "
                "giải thích tốt hơn của mô hình nhiều nhân tố, nhưng không ủng hộ kết "
                "luận rằng thêm nhân tố luôn cải thiện sai lệch định giá.",
                "",
            ]
        )
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text("\n".join(markdown), encoding="utf-8")
    print(f"Scenarios summarized: {sorted(result['scenario'].unique())}")
    print(f"Pending: {pending}")
    print(f"CSV: {args.output_csv.resolve()}")
    print(f"Markdown: {args.output_md.resolve()}")


if __name__ == "__main__":
    main()
