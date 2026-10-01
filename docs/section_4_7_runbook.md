# Quy trình hoàn thành Mục 4.7

## Trạng thái đầu vào

Pipeline đã hỗ trợ và đã tạo output cho ba kiểm tra độ bền. Để tái tạo từ đầu, đặt hai
archive nguồn tại:

```text
data/raw_downloads/vn100_periods.zip
data/raw_downloads/vn100_master.zip
```

Thứ tự hai đối số vị trí là **period trước, master sau**. ZIP period chứa
`_Tom_tat_cac_ky.csv` và `Top100_Ky*.csv`; ZIP master chứa `VN100.xlsx` và các file
`rRF*.xlsx`. Nếu tên file trên một máy không khớp nội dung, đối chiếu hash trong README
thay vì đảo thứ tự tùy ý.

## 1. Chạy Factor Team

```powershell
.\.venv\Scripts\python.exe scripts\build_vn_period_factors.py `
  data\raw_downloads\vn100_periods.zip data\raw_downloads\vn100_master.zip `
  --rf-tenor 1Y --market-proxy VNINDEX --weighting lagged_market_cap `
  --schedule supplied_semiannual `
  --output-dir outputs\vn_period_factors_semiannual

.\.venv\Scripts\python.exe scripts\build_vn_period_factors.py `
  data\raw_downloads\vn100_periods.zip data\raw_downloads\vn100_master.zip `
  --rf-tenor 1Y --market-proxy VNINDEX --weighting formation `
  --schedule annual_july `
  --output-dir outputs\vn_period_factors_formation_weights

.\.venv\Scripts\python.exe scripts\build_vn_period_factors.py `
  data\raw_downloads\vn100_periods.zip data\raw_downloads\vn100_master.zip `
  --rf-tenor 1Y --market-proxy VNINDEX --weighting lagged_market_cap `
  --schedule annual_july --exclude-financials `
  --output-dir outputs\vn_period_factors_ex_financials
```

Không chạy nếu một trong ba thư mục output đã tồn tại mà chưa kiểm tra nguồn gốc.

## 2. Chạy Econometrics Team

Thêm `--factor-commit <mã commit Factor Team>` và `--econometrics-commit <mã commit
Econometrics Team>` vào từng lệnh sau khi hai nhánh đã chốt commit. Không để nguyên
commit mặc định của lần chạy cơ sở trong manifest robustness.

```powershell
.\.venv\Scripts\python.exe scripts\run_vn_econometrics.py `
  --returns outputs\vn_period_factors_semiannual\vn100_returns_clean.csv `
  --factors outputs\vn_period_factors_semiannual\vn100_factors_monthly.csv `
  --universe config\vn_econometrics_universe.csv `
  --market-proxy VN100 --start 2021-07 --end 2026-06 `
  --allow-incomplete-sample --factor-schedule supplied_semiannual `
  --factor-weighting lagged_market_cap --factor-financials included `
  --run-label ROBUSTNESS_SEMIANNUAL `
  --output-dir outputs\vn_econometrics_semiannual

.\.venv\Scripts\python.exe scripts\run_vn_econometrics.py `
  --returns outputs\vn_period_factors_formation_weights\vn100_returns_clean.csv `
  --factors outputs\vn_period_factors_formation_weights\vn100_factors_monthly.csv `
  --universe config\vn_econometrics_universe.csv `
  --market-proxy VN100 --start 2021-07 --end 2026-06 `
  --factor-schedule annual_july --factor-weighting formation `
  --factor-financials included --run-label ROBUSTNESS_FORMATION_WEIGHTS `
  --output-dir outputs\vn_econometrics_formation_weights

.\.venv\Scripts\python.exe scripts\run_vn_econometrics.py `
  --returns outputs\vn_period_factors_ex_financials\vn100_returns_clean.csv `
  --factors outputs\vn_period_factors_ex_financials\vn100_factors_monthly.csv `
  --universe config\vn_econometrics_universe_ex_financials.csv `
  --universe-status group-approved `
  --market-proxy VN100 --start 2021-07 --end 2026-06 `
  --factor-schedule annual_july --factor-weighting lagged_market_cap `
  --factor-financials excluded --run-label ROBUSTNESS_EX_FINANCIALS `
  --output-dir outputs\vn_econometrics_ex_financials
```

File universe loại tài chính giữ đúng 30 mã, chọn theo vốn hóa formation 30/06/2021.
Cả 30 mã đã được kiểm tra có đủ 60 lợi suất từ 07/2021 đến 06/2026.

## 3. Lập bảng Mục 4.7

```powershell
.\.venv\Scripts\python.exe scripts\summarize_section_4_7.py --require-all
```

Lệnh tạo:

- `outputs/vn_econometrics_robustness_comparison.csv`;
- `docs/section_4_7_results.md`.

Bảng gồm R² trung bình, alpha tuyệt đối trung bình, GRS F/p-value, alpha và p-value
của hồi quy bao phủ HML, phần bù HML trung bình/t-stat, số tháng thực tế và danh sách
tháng bị loại. P-value HML chính dùng HAC Bartlett lag 12; CSV vẫn giữ p-value OLS.
