# Asset Pricing VN — quy trình Factor → Kinh tế lượng → Backtest

README này là hướng dẫn chạy toàn bộ dự án theo đúng thứ tự phụ thuộc:

```text
ZIP dữ liệu gốc
   ↓
Xây dựng factor và panel lợi suất VN100
   ├──→ Kinh tế lượng: CAPM / FF3 / FF5 / HAC / VIF / GRS
   └──→ Chuẩn bị returns / membership / benchmark / RF
                                      ↓
                         Backtest danh mục động VN100
```

Tất cả lệnh bên dưới chạy từ thư mục gốc `asset_pricing_vn` bằng PowerShell.

## 1. Trạng thái hiện tại

Các output factor VN đã được lưu tại `outputs/vn_period_factors/`. Archive nguồn thô không có trong workspace hiện tại, vì vậy có hai cách bắt đầu:

1. Có ZIP nguồn: chạy lại từ bước Factor ở Mục 6.
2. Chưa có ZIP nguồn: dùng các output factor đã version hóa và bắt đầu ở Mục 7.

Ngày 01/10/2026 đã chạy backtest exploratory từ các output này:

- VNINDEX: `local_runs/vn100_backtest_vnindex_20261001/`.
- VN30: `local_runs/vn100_backtest_vn30_20261001/`.
- Tóm tắt: `docs/vn100_backtest_run_20261001.md`.

Trạng thái vẫn là **exploratory, chưa nghiệm thu nghiên cứu**, do archive nguồn, đơn vị RF và thời điểm công bố membership chưa được xác minh độc lập.

## 2. Cấu trúc quan trọng

| Đường dẫn | Vai trò |
|---|---|
| `scripts/build_vn_period_factors.py` | Xây factor và panel VN100 từ ZIP nguồn |
| `outputs/vn_period_factors/` | Output factor/panel lợi suất dùng chung |
| `scripts/run_vn_econometrics.py` | Chạy CAPM, FF3, FF5, HAC, VIF và GRS cho Việt Nam |
| `config/vn_econometrics_universe.csv` | Danh sách 30 tài sản cho kinh tế lượng |
| `prepare_vn100_backtest_inputs.py` | Chuyển output Factor thành input backtest động |
| `run_backtest.py` | Runner backtest chung cho fixed/dynamic universe |
| `config/dynamic.template.json` | Template backtest universe động |
| `local_runs/` | Dữ liệu trung gian và output backtest cục bộ |
| `docs/` | Phương pháp, audit và tóm tắt kết quả |

## 3. Bước 0 — clone dự án và tải data

### 3.1 Kiểm tra Git và Python

Mở PowerShell:

```powershell
git --version
py -3.12 --version
```

Nếu lệnh đầu không tồn tại, cài Git for Windows. Nếu lệnh thứ hai không tồn tại, cài Python 3.12 và bật tùy chọn thêm Python Launcher/Python vào PATH.

### 3.2 Clone mới từ GitHub

Chọn thư mục cha nơi muốn lưu dự án, ví dụ:

```powershell
cd "D:\UEL\7. HK 1 2026 - 2027\GPM2\b4"
git clone https://github.com/TranThanhPhu39/portfolio.git asset_pricing_vn
cd asset_pricing_vn
git switch main
git pull --ff-only origin main
```

Tham số `asset_pricing_vn` ở cuối lệnh clone đặt tên thư mục local. Không chạy `git clone` bên trong một bản clone đã tồn tại.

Nếu đã có dự án:

```powershell
cd "D:\UEL\7. HK 1 2026 - 2027\GPM2\b4\asset_pricing_vn"
git status --short
git switch main
git pull --ff-only origin main
```

Nếu `git status --short` hiển thị thay đổi chưa lưu, dừng lại và commit/stash chúng trước; không dùng `git reset --hard` để bỏ dữ liệu.

Xác nhận đúng repository:

```powershell
git remote -v
git branch --show-current
Get-ChildItem
```

Remote phải là `https://github.com/TranThanhPhu39/portfolio.git`, branch là `main`, và thư mục phải có `scripts`, `src`, `tests`, `config`, `run_backtest.py`.

### 3.3 Tải dữ liệu từ Google Drive

Link folder chuẩn (link trong tin nhắn ban đầu bị lặp hai lần):

[Google Drive — dữ liệu dự án](https://drive.google.com/drive/folders/16OWRSgSubrc-Bkyog9mRIdpLk0q3UOZ8?usp=sharing)

Thực hiện trong trình duyệt:

1. Mở link trên và đăng nhập Google nếu Drive yêu cầu.
2. Chọn tên folder ở đầu trang hoặc chọn toàn bộ nội dung.
3. Chọn **Download / Tải xuống**.
4. Chờ Google Drive nén xong; trình duyệt sẽ tải một file dạng `drive-download-....zip` vào `Downloads`.
5. Không sửa file bên trong ZIP trước khi lưu bản gốc và hash.

Google Drive folder không phải đường dẫn mà script Factor có thể đọc trực tiếp; phải tải ZIP về máy trước.

Tạo chỗ lưu raw data trong clone:

```powershell
New-Item -ItemType Directory -Force data\raw_downloads
Get-ChildItem "$env:USERPROFILE\Downloads" -Filter "drive-download-*.zip" |
  Sort-Object LastWriteTime -Descending |
  Select-Object -First 5 Name,Length,LastWriteTime
```

Copy đúng file vừa tải. Ví dụ tên archive lịch sử:

```powershell
Copy-Item -LiteralPath "$env:USERPROFILE\Downloads\drive-download-20260929T092926Z-1-001.zip" `
  -Destination "data\raw_downloads\vn100_combined.zip"
```

Nếu Drive tạo tên khác, thay phần tên nguồn bằng tên vừa hiển thị. `data/raw_downloads/` đã được `.gitignore`; không commit archive lớn hoặc dữ liệu có giới hạn chia sẻ lên GitHub.

Kiểm tra file và mã băm:

```powershell
Get-Item data\raw_downloads\vn100_combined.zip
Get-FileHash data\raw_downloads\vn100_combined.zip -Algorithm SHA256
tar -tf data\raw_downloads\vn100_combined.zip | Select-Object -First 30
```

Archive từng dùng để tái tạo output hiện hành có SHA-256:

```text
2e0627c061811f96eadbf57a13df6629473b715dd6eb71e9b09e636d6d56180c
```

Nếu hash hiện tại khác, Drive có thể đã được cập nhật hoặc bạn tải nhầm file. Không tự đổi dữ liệu để khớp hash: ghi lại hash mới, kiểm tra danh sách file trong ZIP và xác nhận với nhóm trước khi so sánh kết quả.

Nếu Google Drive tải nhiều ZIP riêng thay vì một ZIP kết hợp, giữ nguyên từng ZIP trong `data/raw_downloads/`; ở Mục 6 truyền ZIP kỳ và ZIP master tương ứng thay vì truyền một file hai lần.

## 4. Bước 1 — tạo môi trường Python đầy đủ

Khuyến nghị Python 3.12:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install "pytest>=8,<9"
```

`requirements.txt` là môi trường đầy đủ cho factor, kinh tế lượng và backtest. Nếu chỉ cài `requirements_backtest.txt`, các runner kinh tế lượng có thể thiếu `statsmodels`.

Nếu không có lệnh `py`, dùng:

```powershell
python -m venv .venv
```

Không bắt buộc activate môi trường; các lệnh sau gọi trực tiếp `.venv`.

## 5. Bước 2 — chạy kiểm thử trước khi xử lý dữ liệu

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q
```

Trạng thái tham chiếu hiện tại:

```text
67 passed
```

Không dùng `python -m pytest -q` không kèm `tests`, vì pytest có thể thu thập các module `_test.py` ngoài thư mục kiểm thử. Không tiếp tục nếu có `FAILED` hoặc `ERROR`.

Muốn lưu log:

```powershell
.\.venv\Scripts\python.exe verify_all.py
```

## 6. Giai đoạn A — xây dựng Factor VN

### 6.1 Trường hợp có archive nguồn

Pipeline nhận:

- ZIP chứa các file kỳ VN100.
- ZIP master chứa dữ liệu thị trường và báo cáo tài chính.
- Nếu tất cả nằm trong một ZIP kết hợp, truyền cùng một đường dẫn hai lần.

Nếu Drive cung cấp hai ZIP riêng, tạo output mới và không ghi đè output đã version hóa:

```powershell
.\.venv\Scripts\python.exe scripts\build_vn_period_factors.py `
  "data\raw_downloads\PERIOD_ARCHIVE.zip" `
  "data\raw_downloads\MASTER_ARCHIVE.zip" `
  --rf-tenor 1Y `
  --market-proxy VNINDEX `
  --weighting lagged_market_cap `
  --output-dir outputs\vn_period_factors_rerun_20261001
```

Với ZIP kết hợp đã tải và đổi tên theo Mục 3.3:

```powershell
.\.venv\Scripts\python.exe scripts\build_vn_period_factors.py `
  "data\raw_downloads\vn100_combined.zip" `
  "data\raw_downloads\vn100_combined.zip" `
  --output-dir outputs\vn_period_factors_rerun_20261001
```

Xem toàn bộ tùy chọn:

```powershell
.\.venv\Scripts\python.exe scripts\build_vn_period_factors.py --help
```

### 6.2 Trường hợp chưa có archive nguồn

Dùng bộ đã lưu:

```text
outputs/vn_period_factors/
```

Không chạy builder với dữ liệu giả hoặc ZIP không đúng cấu trúc chỉ để tạo output.

### 6.3 Output Factor cần kiểm tra

| File | Nội dung |
|---|---|
| `vn100_factors_monthly.csv` | MKT_RF, SMB, HML, SMB_FF5, RMW, CMA, RF và MARKET |
| `vn100_returns_clean.csv` | Return từng tháng/ticker và nguồn return |
| `vn100_factor_summary.csv` | Mean, SD, t-stat và số quan sát |
| `vn100_factor_correlations.csv` | Tương quan factor |
| `vn100_formation_audit.csv` | Kiểm tra thông tin tại ngày formation |
| `vn100_group_assignments.csv` | Phân nhóm portfolio |
| `vn100_group_counts.csv` | Số mã từng nhóm |
| `vn100_return_reconciliation.csv` | Sai khác reported return và price return |
| `vn100_data_quality.csv` | Chất lượng dữ liệu theo kỳ |
| `vn100_periods_audit.csv` | Lịch formation/holding và độ đầy đủ |
| `vn100_fundamental_event_conflicts.csv` | Xung đột sự kiện BCTC |

Trước khi sang kinh tế lượng/backtest, kiểm tra:

1. Ngày tăng dần và đúng cuối tháng.
2. Không trùng `date,ticker`.
3. Return và RF là số thập phân, không phải phần trăm.
4. Không có return `<= -1`.
5. Đọc và xử lý các dòng reconciliation/conflict thay vì xóa im lặng.

Chi tiết phương pháp: `docs/vn_period_factor_pipeline.md`.

## 7. Giai đoạn B — kinh tế lượng

### 7.1 Kiểm chứng module bằng dữ liệu Mỹ

Đây là kiểm tra phần mềm, không phải kết quả Việt Nam:

```powershell
.\.venv\Scripts\python.exe scripts\compare_factor_models.py
.\.venv\Scripts\python.exe scripts\compare_to_fama_french_2015.py
.\.venv\Scripts\python.exe scripts\run_grs_test.py
.\.venv\Scripts\python.exe scripts\run_step6_diagnostics.py
```

Các file được ghi vào `outputs/step3_*`, `outputs/step4_*`, `outputs/step5_*` và `outputs/step6_*`.

### 7.2 Chạy kinh tế lượng Việt Nam

Nếu dùng output Factor hiện hành:

```powershell
.\.venv\Scripts\python.exe scripts\run_vn_econometrics.py `
  --returns outputs\vn_period_factors\vn100_returns_clean.csv `
  --factors outputs\vn_period_factors\vn100_factors_monthly.csv `
  --universe config\vn_econometrics_universe.csv `
  --universe-status team-baseline `
  --start 2021-07 `
  --end 2026-06 `
  --market-proxy VN100 `
  --output-dir outputs\vn_econometrics_rerun_20261001
```

Nếu nhóm đã duyệt chính thức danh sách 30 mã, đổi:

```text
--universe-status group-approved
```

Nếu vừa xây factor vào thư mục mới, thay cả `--returns` và `--factors` bằng đường dẫn trong thư mục mới đó.

### 7.3 Output kinh tế lượng

| File | Nội dung |
|---|---|
| `run_report.md` | Báo cáo tổng hợp và diễn giải |
| `run_manifest.json` | Hash, commit, phương pháp và trạng thái mẫu |
| `asset_model_summary.csv` | Alpha, beta, t-stat, R² theo mã/mô hình |
| `coefficient_detail.csv` | OLS và HAC chi tiết |
| `grs_summary.csv` | Kiểm định GRS cho CAPM/FF3/FF5 |
| `vif.csv` | Đa cộng tuyến |
| `market_proxy_sensitivity.csv` | VN100 so với VNINDEX |
| `table5_style_summary.csv` | Tổng hợp kiểu Table 5 |
| `table7_style_assets.csv` | Kết quả từng tài sản kiểu Table 7 |
| `hml_redundancy.csv` | Kiểm tra HML redundancy |
| `selected_tickers.csv` | 30 mã được chọn |
| `sample_months.csv` | Các tháng dùng chung |
| `model_summaries.txt` | Summary đầy đủ của statsmodels |

Mở báo cáo:

```powershell
code outputs\vn_econometrics_rerun_20261001\run_report.md
```

Không diễn giải “không bác bỏ GRS” thành “mô hình chắc chắn đúng”. Xem thêm `docs/econometrics_audit_guide.md` và `docs/vn_econometrics_method_choices.md`.

## 8. Giai đoạn C — chuẩn bị input backtest

Backtest động cần bốn file:

- `returns.csv`: `date,ticker,return`.
- `membership.csv`: `date,ticker,member`.
- `risk_free.csv`: `date,rf_return`.
- `benchmark_*.csv`: `date,return`.

Tạo chúng từ output Factor:

```powershell
.\.venv\Scripts\python.exe prepare_vn100_backtest_inputs.py `
  --source outputs\vn_period_factors `
  --output local_runs\vn100_inputs_20261001_02
```

Script cố ý không ghi đè thư mục cũ. Nếu tên đã tồn tại, tăng hậu tố `_02`, `_03`, v.v.

Output gồm:

```text
returns.csv
membership.csv
risk_free.csv
benchmark_vnindex.csv
benchmark_vn30.csv
preparation_metadata.json
```

`preparation_metadata.json` ghi hash nguồn, giai đoạn, số mã, số tháng và số reported-return fallback.

## 9. Giai đoạn D — cấu hình backtest

### 9.1 Tạo config VNINDEX

```powershell
Copy-Item config\dynamic.template.json config\vn100_vnindex_02.local.json
```

Mở file vừa copy và điền đầy đủ. Các trường đường dẫn tối thiểu:

```json
{
  "synthetic": false,
  "universe_mode": "dynamic",
  "returns": "../local_runs/vn100_inputs_20261001_02/returns.csv",
  "membership": "../local_runs/vn100_inputs_20261001_02/membership.csv",
  "benchmark": "../local_runs/vn100_inputs_20261001_02/benchmark_vnindex.csv",
  "risk_free": "../local_runs/vn100_inputs_20261001_02/risk_free.csv",
  "output_dir": "../local_runs/vn100_backtest_vnindex_20261001_02",
  "lookback": 24,
  "rebalance_every": 1,
  "decision_lag_periods": 1,
  "rates": [0, 0.0015, 0.0025, 0.0035]
}
```

Đây chỉ là phần đường dẫn/tham số. Giữ ba chiến lược và điền các trường mô tả phương pháp còn lại trong template. Không nhập dòng JSON trực tiếp vào PowerShell; phải sửa trong file bằng VS Code.

### 9.2 Tạo config VN30 sensitivity

Copy config VNINDEX rồi đổi benchmark và output:

```powershell
Copy-Item config\vn100_vnindex_02.local.json config\vn100_vn30_02.local.json
```

Trong file VN30, đổi:

```json
"benchmark_name": "VN30 monthly price return",
"benchmark": "../local_runs/vn100_inputs_20261001_02/benchmark_vn30.csv",
"output_dir": "../local_runs/vn100_backtest_vn30_20261001_02"
```

## 10. Giai đoạn E — chạy backtest

```powershell
.\.venv\Scripts\python.exe run_backtest.py --config config\vn100_vnindex_02.local.json
.\.venv\Scripts\python.exe run_backtest.py --config config\vn100_vn30_02.local.json
```

Mở báo cáo:

```powershell
Start-Process .\local_runs\vn100_backtest_vnindex_20261001_02\report.html
Start-Process .\local_runs\vn100_backtest_vn30_20261001_02\report.html
```

### 10.1 Output backtest

| File | Nội dung |
|---|---|
| `report.html` | Báo cáo tổng hợp và biểu đồ |
| `comparison.csv` | Sharpe, CAGR, drawdown, return, phí, turnover |
| `run_metadata.json` | Config, hash input và phiên bản thư viện |
| `*_periods.csv` | Giá trị và return từng tháng |
| `*_trades.csv` | Giao dịch và phí từng mã |
| `*_weights.csv` | Trọng số đầu kỳ |
| `*_eligibility.csv` | Mã đủ/không đủ lịch sử huấn luyện |
| `*_equity.svg`, `*_drawdown.svg` | Biểu đồ theo chiến lược |

### 10.2 Checklist hậu kiểm

1. Tất cả chiến lược/mức phí có cùng số tháng ngoài mẫu.
2. `start_value - fee = end_value / (1 + market_return)` trong sai số số học.
3. Tổng fee theo tháng trong trades khớp fee trong periods.
4. Trọng số không âm và tổng xấp xỉ 1.
5. `train_end` luôn trước tháng giao dịch đúng theo lag.
6. Hai lần VNINDEX/VN30 phải có đường chiến lược giống nhau; chỉ dòng benchmark và so sánh thay đổi.
7. Không coi benchmark là danh mục đã chịu cùng chi phí giao dịch.

## 11. Quy trình ngắn cho workspace hiện tại

Vì factor VN hiện đã tồn tại, có thể chạy theo thứ tự:

```powershell
# 1. Kiểm thử
.\.venv\Scripts\python.exe -m pytest tests -q

# 2. Kinh tế lượng vào output mới
.\.venv\Scripts\python.exe scripts\run_vn_econometrics.py `
  --returns outputs\vn_period_factors\vn100_returns_clean.csv `
  --factors outputs\vn_period_factors\vn100_factors_monthly.csv `
  --universe config\vn_econometrics_universe.csv `
  --start 2021-07 --end 2026-06 `
  --market-proxy VN100 `
  --output-dir outputs\vn_econometrics_rerun_20261001

# 3. Chuẩn bị input backtest mới
.\.venv\Scripts\python.exe prepare_vn100_backtest_inputs.py `
  --source outputs\vn_period_factors `
  --output local_runs\vn100_inputs_20261001_02

# 4. Sửa hai config local như Mục 9, sau đó chạy
.\.venv\Scripts\python.exe run_backtest.py --config config\vn100_vnindex_02.local.json
.\.venv\Scripts\python.exe run_backtest.py --config config\vn100_vn30_02.local.json
```

## 12. Lỗi thường gặp

- `ModuleNotFoundError: statsmodels`: cài `requirements.txt`, không chỉ `requirements_backtest.txt`.
- `ModuleNotFoundError: pytest`: cài `pytest>=8,<9` và chạy `pytest tests -q`.
- `FileExistsError`: chọn output mới; runner backtest cố ý không ghi đè.
- `Complete the research template field`: config vẫn còn `REPLACE_WITH` hoặc `CONFIRM_`.
- `Missing calendar month`: dữ liệu thiếu tháng; không xóa dòng để lách kiểm tra.
- `Membership cannot contain missing values`: mọi cặp tháng/mã phải có membership tường minh.
- `Missing/invalid return for held asset`: return bị thiếu tại tháng đang nắm giữ mã.
- `RF missing in training window`: RF chưa phủ đủ cửa sổ huấn luyện.
- Cảnh báo PyArrow của pandas 2.2: không làm hỏng kết quả hiện tại; đây là cảnh báo dependency cho pandas tương lai.

## 13. Điều kiện nghiệm thu nghiên cứu

Trước khi dùng kết quả trong luận văn/báo cáo cuối:

1. Lưu archive nguồn và SHA-256.
2. Xác nhận cơ sở giá: price return hay total return, có điều chỉnh cổ tức/quyền hay không.
3. Xác nhận đơn vị và kỳ hạn RF.
4. Xác nhận ngày công bố membership trước thời điểm giao dịch mô phỏng.
5. Duyệt reconciliation và fundamental conflicts.
6. Chốt universe kinh tế lượng và benchmark bằng quyết định nhóm, không theo kết quả đẹp nhất.
7. Ghi rõ ridge, lookback, lag, phí và giới hạn thực thi.
8. Không diễn giải test pass như bằng chứng dữ liệu/phương pháp chắc chắn đúng.

Các tài liệu liên quan:

- `docs/vn_period_factor_pipeline.md`
- `docs/econometrics_audit_guide.md`
- `docs/vn_econometrics_method_choices.md`
- `docs/input_contract.md`
- `docs/decisions.md`
- `HUONG_DAN_TEST.md`
- `METHOD_SPEC.md`
