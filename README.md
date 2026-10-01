# Asset Pricing VN

Dự án kiểm định CAPM, Fama-French 3/5 nhân tố và backtest danh mục Markowitz
long-only trên thị trường Việt Nam. Nhân tố được xây từ VN100; kinh tế lượng dùng
30 cổ phiếu vốn hóa lớn tại formation 30/06/2021; backtest đầu tư trên universe VN100
động và dùng VN30 làm benchmark chính.

```text
Hai ZIP dữ liệu nguồn
        |
        v
Factor VN100 + panel lợi suất sạch
        |-------------------------------|
        v                               v
CAPM / FF3 / FF5 / HAC / VIF / GRS     Markowitz + walk-forward + phí
        |                               |
        v                               v
Robustness Mục 4.7                     VN30 / VN-Index sensitivity
```

## 1. Kết quả đã xác nhận

- Bộ kiểm thử: **67 passed** trên Python 3.12.
- Factor cơ sở: 96 tháng, 07/2018-06/2026.
- Kinh tế lượng cơ sở: 30 cổ phiếu, 60 tháng, 90 hồi quy.
- Backtest ngoài mẫu: 71 tháng, 08/2020-06/2026.
- Robustness đã hoàn thành: lịch sáu tháng, trọng số formation và loại tài chính.
- Các output robustness không ghi đè bộ cơ sở.

Kết quả chính:

| Mô hình | R² trung bình | \|alpha\| trung bình (%/tháng) | GRS F | p-value |
|---|---:|---:|---:|---:|
| CAPM | 0,3097 | 0,7006 | 0,4837 | 0,9738 |
| FF3 | 0,3683 | 0,7359 | 0,7079 | 0,8211 |
| FF5 | 0,4702 | 0,7923 | 0,7727 | 0,7519 |

Các giá trị trên là **R² thông thường**, không phải adjusted R². Không bác bỏ GRS
không có nghĩa mô hình chắc chắn đúng.

Tại phí 0,25% mỗi chiều, Sharpe ngoài mẫu là 0,747 cho MinVariance, 1,305 cho
MaxSharpe, 0,932 cho EqualWeight và 0,813 cho VN30. Kết quả là bằng chứng thăm dò;
chênh lệch Sharpe chưa được kiểm định ý nghĩa thống kê.

## 2. Cấu trúc repository

| Đường dẫn | Vai trò |
|---|---|
| `src/factors/` | Xây nhân tố và kiểm tra portfolio-sort |
| `src/models/` | Hồi quy, HAC, VIF và GRS |
| `src/portfolio/` | Markowitz long-only và đường biên hiệu quả |
| `src/backtest/` | Walk-forward, phí, chỉ tiêu và báo cáo |
| `scripts/` | Các runner có thể gọi lại từ CLI hoặc notebook |
| `config/` | Universe và template cấu hình |
| `notebooks/` | Trình diễn từng giai đoạn nghiên cứu |
| `outputs/` | Bảng, audit, hình và kết quả kinh tế lượng |
| `local_runs/` | Input/output backtest cục bộ, không phải nguồn gốc |
| `docs/` | Phương pháp, audit và kết luận |
| `tests/` | Kiểm thử tự động |

## 3. Notebook

Các notebook chỉ điều phối và trình bày; logic thật nằm trong `src/` và `scripts/`:

| Notebook | Nội dung |
|---|---|
| `01_data_and_quality.ipynb` | Kiểm tra panel lợi suất, formation và chất lượng dữ liệu |
| `02_factor_construction.ipynb` | Kiểm tra sáu danh mục, thống kê và biểu đồ nhân tố |
| `03_asset_pricing_tests.ipynb` | CAPM/FF3/FF5, GRS, HAC và VIF |
| `04_portfolio_optimization.ipynb` | Đường biên hiệu quả và ba danh mục |
| `05_backtest.ipynb` | Walk-forward, phí, VN30, equity và drawdown |

Mở Jupyter từ thư mục gốc:

```powershell
.\.venv\Scripts\python.exe -m jupyter lab
```

Notebook 01-04 đọc output cơ sở đã lưu. Notebook 04-05 tự tạo input cục bộ trong
`local_runs/notebook_vn100_inputs/` khi cần. Notebook 05 chỉ chạy backtest nếu
`local_runs/notebook_vn100_backtest/` chưa tồn tại, nên không ghi đè kết quả.

## 4. Môi trường

Khuyến nghị Python 3.12. Trên một clone mới:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install "pytest>=8,<9" "jupyterlab>=4,<5"
```

Nếu `.venv` được chép từ máy hoặc thư mục khác và báo đường dẫn Python không tồn tại,
hãy tạo lại môi trường; virtual environment không có tính di động giữa các máy.

Chạy kiểm thử:

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q
```

Không chạy `pytest -q` ở toàn repository vì có các module kiểm chứng mang hậu tố
`_test.py` ngoài thư mục `tests/`.

## 5. Dữ liệu nguồn

Dữ liệu thực nghiệm cuối cùng là bộ Refinitiv LSEG do nhóm cung cấp. `vnstock` và
Kenneth French không phải nguồn chính của kết quả Việt Nam; dữ liệu Kenneth French
chỉ dùng kiểm thử logic.

Đặt hai ZIP, giữ nguyên nội dung, tại:

```text
data/raw_downloads/vn100_periods.zip
data/raw_downloads/vn100_master.zip
```

| File | Nội dung | SHA-256 của bản đã chạy |
|---|---|---|
| `vn100_periods.zip` | 18 file `Top100_Ky*.csv` và bảng tổng hợp | `04f233a314c32e295d11874bf615a66b380e74ee7143a0e977196b3c6b896fe1` |
| `vn100_master.zip` | `VN100.xlsx`, master data và RF 1Y/3Y/10Y | `dd10bf9df75d9ce3365a942345a1f5d6012e1e3ddd026ae4ae485ce1f1461dd3` |

`data/raw_downloads/` bị bỏ qua bởi Git. Không đẩy dữ liệu có giới hạn chia sẻ lên
GitHub. Kiểm tra hash trước khi tái tạo kết quả:

```powershell
Get-FileHash data\raw_downloads\vn100_periods.zip -Algorithm SHA256
Get-FileHash data\raw_downloads\vn100_master.zip -Algorithm SHA256
```

## 6. Chạy lại factor cơ sở

Không ghi đè output đã nghiệm thu; luôn chọn thư mục mới:

Hai đối số vị trí của script có thứ tự cố định: **ZIP period trước, ZIP master sau**.
Không dựa vào tên file nếu ZIP đã được đổi tên thủ công: ZIP period phải chứa
`_Tom_tat_cac_ky.csv` và các file `Top100_Ky*.csv`; ZIP master phải chứa `VN100.xlsx`
và `rRF 1Y.xlsx`. Nếu lệnh chỉ chạy khi đặt `vn100_master.zip` lên trước, hai file trên
máy đó đang bị đặt tên ngược; hãy đối chiếu SHA-256 ở Mục 5 và đổi lại tên.

```powershell
.\.venv\Scripts\python.exe scripts\build_vn_period_factors.py `
  data\raw_downloads\vn100_periods.zip `
  data\raw_downloads\vn100_master.zip `
  --rf-tenor 1Y `
  --market-proxy VNINDEX `
  --weighting lagged_market_cap `
  --schedule annual_july `
  --output-dir outputs\vn_period_factors_rerun
```

Output quan trọng gồm `vn100_factors_monthly.csv`, `vn100_returns_clean.csv`,
`vn100_factor_summary.csv`, `vn100_factor_correlations.csv`,
`vn100_formation_audit.csv`, `vn100_group_counts.csv`, `vn100_data_quality.csv` và
`vn100_return_reconciliation.csv`.

Phương pháp là khung 2×3 Size × Characteristic của Fama-French được điều chỉnh cho
VN100. Dữ liệu kế toán dùng báo cáo gần nhất có ngày công bố không sau formation;
đây không phải bản sao hoàn toàn quy tắc book equity tháng 12 năm t-1 của Hoa Kỳ.

## 7. Chạy kinh tế lượng

```powershell
.\.venv\Scripts\python.exe scripts\run_vn_econometrics.py `
  --returns outputs\vn_period_factors\vn100_returns_clean.csv `
  --factors outputs\vn_period_factors\vn100_factors_monthly.csv `
  --universe config\vn_econometrics_universe.csv `
  --universe-status team-baseline `
  --start 2021-07 --end 2026-06 `
  --market-proxy VN100 `
  --output-dir outputs\vn_econometrics_rerun
```

Output gồm `table5_style_summary.csv`, `table7_style_assets.csv`,
`coefficient_detail.csv`, `grs_summary.csv`, `vif.csv`, `hml_redundancy.csv`,
`run_manifest.json` và `run_report.md`. Kết quả cơ sở đã kiểm tra nằm trong
`outputs/vn_econometrics_baseline/`.

## 8. Kiểm tra độ bền Mục 4.7

Ba bộ factor và kinh tế lượng đã được tạo tại:

```text
outputs/vn_period_factors_semiannual/
outputs/vn_period_factors_formation_weights/
outputs/vn_period_factors_ex_financials/
outputs/vn_econometrics_semiannual/
outputs/vn_econometrics_formation_weights/
outputs/vn_econometrics_ex_financials/
```

Universe vế trái loại tài chính là
`config/vn_econometrics_universe_ex_financials.csv`. Lệnh chạy đầy đủ và audit nằm
trong `docs/section_4_7_runbook.md` và `docs/section_4_7_factor_audit.md`.
Các lệnh trong runbook dùng Python của chính môi trường dự án:
`.\.venv\Scripts\python.exe`; không dùng `py -3.12` sau khi đã kích hoạt/cài `.venv`.

Tạo lại bảng so sánh:

```powershell
.\.venv\Scripts\python.exe scripts\summarize_section_4_7.py --require-all
```

Kết quả cuối nằm tại `outputs/vn_econometrics_robustness_comparison.csv` và
`docs/section_4_7_results.md`. Lịch sáu tháng dùng 59 tháng chung vì SSB.HM thiếu
lợi suất tại 07/2021; hai đặc tả còn lại dùng đủ 60 tháng.

## 9. Chuẩn bị và chạy backtest

```powershell
.\.venv\Scripts\python.exe prepare_vn100_backtest_inputs.py `
  --source outputs\vn_period_factors `
  --output local_runs\vn100_inputs_rerun
```

Copy `config/dynamic.template.json` thành config cục bộ và điền đường dẫn tới
`returns.csv`, `membership.csv`, `risk_free.csv` và `benchmark_vn30.csv` hoặc
`benchmark_vnindex.csv`. Sau đó chạy:

```powershell
.\.venv\Scripts\python.exe run_backtest.py --config config\vn100_vn30.local.json
```

Runner cố ý từ chối ghi đè output đã tồn tại. Báo cáo hiện hành:

```text
local_runs/vn100_backtest_vn30_20261001/report.html
local_runs/vn100_backtest_vnindex_20261001/report.html
```

Backtest chưa mô hình hóa trượt giá, thuế, lô giao dịch, biên độ giá, room ngoại hoặc
tạm ngừng giao dịch. Benchmark không chịu phí và chưa được xác nhận độc lập là total
return; vì vậy kết quả phải được gọi là exploratory.

## 10. Tạo hình báo cáo

```powershell
.\.venv\Scripts\python.exe scripts\generate_missing_figures.py
```

Hình SVG và PNG 300 dpi được lưu tại `outputs/report_figures/`, gồm lợi suất tích lũy
nhân tố, R²/alpha theo mô hình và đường biên hiệu quả 05/2024-04/2026.

## 11. Kiểm tra trước khi nộp

1. `67 passed` trong `tests/`.
2. Hash hai ZIP khớp bản đã audit hoặc thay đổi được giải thích.
3. Không có ngày kế toán sau formation trong `vn100_formation_audit.csv`.
4. Mỗi period-sort có đủ sáu danh mục và không có danh mục rỗng.
5. GRS dùng cùng 30 tài sản và cùng tháng cho ba mô hình.
6. Báo cáo gọi chỉ tiêu đang dùng là R² thông thường, không phải adjusted R².
7. Không diễn giải “không bác bỏ GRS” thành “mô hình đúng”.
8. Ghi rõ nhân tố dùng VN100, LHS dùng 30 cổ phiếu lớn thuộc VN100 và benchmark
   backtest là VN30.
9. Commit code, notebook, config và output cần bàn giao; không commit ZIP nguồn nếu
   giấy phép không cho phép.

## 12. Tài liệu liên quan

- `docs/vn_period_factor_pipeline.md`
- `docs/vn_econometrics_method_choices.md`
- `docs/vn_econometrics_implementation_audit.md`
- `docs/section_4_7_results.md`
- `docs/section_4_7_factor_audit.md`
- `docs/vn100_backtest_run_20261001.md`
- `METHOD_SPEC.md`
- `HUONG_DAN_TEST.md`
