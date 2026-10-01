# Asset Pricing VN — hướng dẫn chạy backtest từ đầu đến cuối

## 1. Trạng thái dữ liệu thật

Workspace hiện tại **chưa có một lần chạy backtest dữ liệu thật có đủ đầu vào, metadata và kết quả để kiểm chứng/tái lập**.

- `sample_inputs/` và `sample_run/` là dữ liệu/kết quả giả lập.
- `outputs/vn_period_factors/` là đầu ra xây dựng nhân tố, không phải portfolio backtest.
- Không có bộ nguồn `Top100_Ky*.csv`, `local_runs/` hoặc `RUN_STATUS.json` của một lần chạy VN100 thật.
- Không dùng kết quả demo để kết luận MinVariance, MaxSharpe hay EqualWeight tốt hơn VN30.

Engine đã được kiểm thử cho cả universe cố định và universe thay đổi theo thời gian. Để tạo kết quả nghiên cứu thật, cần cung cấp đúng dữ liệu và xác nhận các giả định trong `docs/decisions.md`.

## 2. Thành phần chính

| Thành phần | Công dụng |
|---|---|
| `run_backtest.py` | Runner CSV chung cho universe `fixed` và `dynamic` |
| `run_vn100.py` | Runner chuyên biệt cho bộ file kỳ `Top100_Ky*.csv` |
| `config/example.json` | Demo giả lập chạy được ngay |
| `config/research.template.json` | Template dữ liệu thật, universe cố định |
| `config/dynamic.template.json` | Template dữ liệu thật, universe động |
| `docs/input_contract.md` | Hợp đồng dữ liệu đầu vào |
| `docs/decisions.md` | Các giả định nhóm phải xác nhận |
| `verify_all.py` | Chạy test và lưu `TEST_RESULTS.txt` |

## 3. Bước 1 — mở đúng thư mục

```powershell
cd "D:\UEL\7. HK 1 2026 - 2027\GPM2\b4\asset_pricing_vn"
Get-ChildItem
```

Phải nhìn thấy `run_backtest.py`, `src`, `tests` và `config`.

## 4. Bước 2 — tạo môi trường Python

Khuyến nghị Python 3.12:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements_backtest.txt
.\.venv\Scripts\python.exe -m pip install "pytest>=8,<9"
```

Nếu không có lệnh `py`, dùng `python -m venv .venv`. Không bắt buộc activate môi trường.

## 5. Bước 3 — kiểm tra source code

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Trạng thái tham chiếu hiện tại là `67 passed`. Nếu có `FAILED` hoặc `ERROR`, không diễn giải dữ liệu thật trước khi xử lý lỗi.

Muốn lưu log kiểm thử:

```powershell
.\.venv\Scripts\python.exe verify_all.py
```

## 6. Bước 4 — chạy demo giả lập

`config/example.json` dùng dữ liệu giả lập trong `sample_inputs/`. Mỗi lần chạy phải chọn một `output_dir` chưa tồn tại:

```powershell
Copy-Item config\example.json config\example.local.json
```

Mở `config/example.local.json`, đổi thành một tên output mới, ví dụ:

```json
"output_dir": "../sample_run_02"
```

Chạy và mở báo cáo:

```powershell
.\.venv\Scripts\python.exe run_backtest.py --config config\example.local.json
Start-Process .\sample_run_02\report.html
```

Demo hợp lệ tạo `comparison.csv`, `run_metadata.json`, `report.html`, các file `*_periods.csv`, `*_trades.csv`, `*_weights.csv` và biểu đồ SVG.

## 7. Bước 5 — chuẩn bị dữ liệu thật

Tất cả lợi suất phải là **simple return dạng số thập phân**. Ví dụ `0.025` là `2.5%`. Không truyền phần trăm hoặc log-return. Ngày phải là cuối tháng theo `YYYY-MM-DD`, tăng dần và không trùng khóa.

### 7.1 Universe cố định

`data/returns.csv`:

```csv
date,ticker,return
2020-01-31,FPT,0.021
2020-01-31,VCB,-0.008
2020-02-29,FPT,0.015
2020-02-29,VCB,0.011
```

Mỗi mã phải có return đầy đủ cho mọi tháng.

`data/benchmark.csv`:

```csv
date,return
2020-01-31,0.012
2020-02-29,0.009
```

`data/risk_free.csv`:

```csv
date,rf_return
2020-01-31,0.003
2020-02-29,0.003
```

Nếu đầu vào là giá điều chỉnh cuối tháng với cột `date,ticker,adjusted_price`:

```powershell
.\.venv\Scripts\python.exe prepare_prices.py --input data\adjusted_prices.csv --output data\returns.csv
```

### 7.2 Universe thay đổi theo thời gian

Ngoài ba file trên, tạo `data/membership.csv`:

```csv
date,ticker,member
2020-01-31,FPT,true
2020-01-31,VCB,true
2020-01-31,AAA,false
2020-02-29,FPT,true
2020-02-29,VCB,false
2020-02-29,AAA,true
```

Quy tắc:

- Mỗi cặp tháng/mã phải có membership tường minh.
- `member` chỉ nhận `true`, `false`, `1` hoặc `0`; không để trống.
- Returns chỉ được thiếu đối với tài sản không nắm giữ.
- Membership thay đổi sẽ buộc tái cân bằng để bán mã vừa rời universe.
- Phải xác nhận thành phần rổ đã được công bố trước ngày giao dịch để tránh look-ahead bias.

## 8. Bước 6A — chạy dữ liệu thật, universe cố định

```powershell
Copy-Item config\research.template.json config\research.json
```

Mở `config/research.json`, thay toàn bộ `REPLACE_WITH...` và `CONFIRM_...`. Một cấu hình điển hình:

```json
{
  "synthetic": false,
  "universe_mode": "fixed",
  "data_source": "Tên nhà cung cấp và ngày tải dữ liệu",
  "benchmark_name": "VN30 price return",
  "return_basis": "Monthly simple return from adjusted month-end prices",
  "universe_selection": "Danh sách mã cố định và quy tắc lựa chọn",
  "execution_assumption": "24 tháng huấn luyện tới t-2; giao dịch trước return tháng t",
  "returns": "../data/returns.csv",
  "benchmark": "../data/benchmark.csv",
  "risk_free": "../data/risk_free.csv",
  "output_dir": "../local_runs/fixed_20261001_01",
  "lookback": 24,
  "rebalance_every": 1,
  "decision_lag_periods": 1,
  "rates": [0, 0.0015, 0.0025, 0.0035],
  "strategies": {
    "MinVariance": "builtin:min_variance",
    "MaxSharpe": "builtin:max_sharpe",
    "EqualWeight": "builtin:equal_weight"
  },
  "ridge": 1e-08
}
```

Chạy:

```powershell
.\.venv\Scripts\python.exe run_backtest.py --config config\research.json
Start-Process .\local_runs\fixed_20261001_01\report.html
```

## 9. Bước 6B — chạy dữ liệu thật, universe động

```powershell
Copy-Item config\dynamic.template.json config\dynamic.json
```

Điền đầy đủ template, đặc biệt:

```json
{
  "universe_mode": "dynamic",
  "returns": "../data/returns.csv",
  "membership": "../data/membership.csv",
  "benchmark": "../data/benchmark.csv",
  "risk_free": "../data/risk_free.csv",
  "rf_basis": "Monthly simple decimal return; ghi rõ cách chuyển đổi",
  "end": "2026-08-31",
  "output_dir": "../local_runs/dynamic_20261001_01"
}
```

Đoạn trên chỉ minh họa các trường quan trọng; giữ và điền các trường phương pháp, chiến lược, lookback, lag và phí còn lại trong template.

```powershell
.\.venv\Scripts\python.exe run_backtest.py --config config\dynamic.json
Start-Process .\local_runs\dynamic_20261001_01\report.html
```

Mỗi chiến lược dynamic có thêm file `*_eligibility.csv`.

## 10. Chạy bộ file kỳ `Top100_Ky*.csv`

Chỉ dùng khi nhóm cung cấp các cột `Date`, `Ticker`, `Monthly Return (%)`, `Close (EOM)`, `rRF` và `VN30`. Đặt file trong `data/vn100_periods/`:

```powershell
.\.venv\Scripts\python.exe run_vn100.py `
  --input data\vn100_periods `
  --output local_runs\vn100_provided_20261001_01 `
  --return-basis provided `
  --rf-basis annual_effective_percent `
  --end 2026-08
```

Muốn tính return từ `Close (EOM)`, đổi `--return-basis prices`. Không chọn `annual_effective_percent` hoặc `monthly_percent` theo kết quả đẹp hơn; phải xác nhận đơn vị `rRF` từ nguồn.

## 11. Bước 7 — kiểm tra và nghiệm thu kết quả

| File | Nội dung |
|---|---|
| `comparison.csv` | Sharpe, CAGR, drawdown, total return, phí, turnover |
| `*_periods.csv` | Vốn đầu/cuối, return ròng và phí từng tháng |
| `*_trades.csv` | Giao dịch, cửa sổ huấn luyện và phí từng mã |
| `*_weights.csv` | Trọng số đầu kỳ; tổng mỗi ngày phải xấp xỉ 1 |
| `*_eligibility.csv` | Mã dynamic đủ/không đủ lịch sử |
| `run_metadata.json` | Config, SHA-256 đầu vào, phiên bản thư viện |
| `RUN_STATUS.json` | Trạng thái runner chuyên biệt VN100 |
| `report.html` | Báo cáo tổng hợp và biểu đồ |

Checklist tối thiểu:

1. Không có `FAILED`, `ERROR`, `NaN` bất ngờ hoặc tháng bị mất.
2. `train_end` phải trước ngày thực thi theo lag đã khai báo.
3. Chiến lược, benchmark và RF phải dùng cùng kỳ đánh giá.
4. Tổng phí trong trades phải khớp phí trong periods.
5. Các kịch bản phí phải dùng cùng lịch và cùng trọng số mục tiêu.
6. Metadata phải ghi đúng nguồn, return basis, RF, universe và giả định thực thi.
7. Nhóm phải duyệt `docs/decisions.md` trước khi diễn giải kết quả thật.

## 12. Lỗi thường gặp

- `FileExistsError`: đổi `output_dir`; runner cố ý không ghi đè.
- `Missing calendar month`: bổ sung tháng thiếu, không xóa dòng để lách kiểm tra.
- `Membership cannot contain missing values`: điền membership cho mọi cặp tháng/mã.
- `Missing/invalid return for held asset`: sửa return tại tháng đang giữ mã.
- `RF missing in training window`: chuỗi RF chưa phủ đủ cửa sổ huấn luyện.
- `Complete the research template field`: config vẫn còn placeholder.
- `Insufficient eligible assets`: tháng đó có ít hơn hai mã thuộc universe và đủ lịch sử.

## 13. Giới hạn nghiên cứu

Backtest giả định long-only, fully invested, fractional holdings và giao dịch ở đầu kỳ trước return tháng. Phí áp dụng cho cả mua và bán, có phí mua ban đầu nhưng không thanh lý cuối mẫu. Engine chưa mô phỏng đầy đủ lô cổ phiếu, trần/sàn, ngừng giao dịch, thanh khoản, market impact, thuế và thanh toán T+.

Một lần chạy thành công chỉ xác nhận code và dữ liệu đáp ứng hợp đồng kỹ thuật; không tự động xác nhận nguồn dữ liệu hoặc phương pháp nghiên cứu là đúng.
