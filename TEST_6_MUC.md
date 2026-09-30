# Thành: kiểm tra lần lượt 6 mục — bản v3

## Cài và mở đúng bản

Giải nén v3 vào thư mục mới, không chép đè bản v2. Ví dụ đặt thư mục code tại `D:\Back_test_goi_1\thanh_backtest_v3`. Bên trong phải có `run_six_steps.py`, `src`, `tests`. Dùng lại môi trường `.venv` đang chạy được của bạn.

Chạy từng dòng trong PowerShell:

```powershell
cd "D:\Back_test_goi_1\thanh_backtest_v3"
& "D:\Back_test_goi_1\.venv\Scripts\python.exe" -m pip install -r requirements_backtest.txt
```

Nếu thư mục giải nén khác, thay đường dẫn ở lệnh cd. Không tạo lại `.venv`. Bộ này cần NumPy 1.26.0, pandas 2.2.0, SciPy 1.13.0; chưa gọi statsmodels hay vnstock.

## Mục 1 — Giá thành lợi suất

```powershell
& "D:\Back_test_goi_1\.venv\Scripts\python.exe" -m unittest discover -s tests -p test_portfolio.py -k Stage1 -v
```

Đạt: OK. Kiểm tra giá 100 → 110 → 99 tạo lợi suất +10%, -10%; giá thiếu/0 và tháng thiếu bị từ chối. File xử lý: `src/portfolio/prices.py`.

Đầu vào là GIÁ ĐÃ ĐIỀU CHỈNH THEO THÁNG, mỗi tháng một giá/mã, nhãn ngày cuối tháng. Code sắp xếp theo ngày, chuyển kiểu số, kiểm tra trùng/thiếu/sai; không tự sửa giá bất thường, điền giá hay tự điều chỉnh cổ tức. Với dữ liệu ngày, team data phải xác nhận lịch giao dịch và lấy giá cuối phiên cuối tháng trước khi bàn giao. Không dùng giá thô chưa điều chỉnh rồi gọi là total return.

## Mục 2 — Ước lượng

```powershell
& "D:\Back_test_goi_1\.venv\Scripts\python.exe" -m unittest discover -s tests -p test_portfolio.py -k Stage2 -v
```

Đạt: OK. Kiểm tra mean và covariance bằng ví dụ tính tay. Mean là trung bình số học lợi suất tháng; covariance mẫu ddof=1. Có cộng `ridge * I` (mặc định 1e-8) để ổn định số; xuất riêng cả covariance mẫu và covariance dùng tối ưu. Ridge là giả định phải công khai, không phải tham số được suy ra từ bài báo.

## Mục 3 — Min Variance và Max Sharpe

```powershell
& "D:\Back_test_goi_1\.venv\Scripts\python.exe" -m unittest discover -s tests -p test_portfolio.py -k Stage3 -v
```

Đạt: OK. Bao gồm nghiệm tối thiểu phương sai hai tài sản là 9/13 và 4/13, nghiệm Sharpe tính bằng đại số, căn chỉnh nhãn, từ chối covariance không hợp lệ và không sử dụng RF tương lai. Long-only, tổng trọng số 1, không giới hạn tỷ trọng riêng ngoài [0,1]. Solver lỗi sẽ dừng, không chuyển ngầm sang chia đều.

## Mục 4 — Đường biên hiệu quả

```powershell
& "D:\Back_test_goi_1\.venv\Scripts\python.exe" -m unittest discover -s tests -p test_portfolio.py -k Stage4 -v
```

Đạt: OK. Kiểm tra trọng số, lợi suất mục tiêu và nhánh hiệu quả từ Min Variance đến lợi suất kỳ vọng lớn nhất. Trục ngang là độ lệch chuẩn tháng, trục dọc là lợi suất kỳ vọng tháng. Các mức mục tiêu bất khả thi bị từ chối.

## Mục 5 — So sánh danh mục

```powershell
& "D:\Back_test_goi_1\.venv\Scripts\python.exe" -m unittest discover -s tests -p test_portfolio.py -k Stage5 -v
```

Đạt: OK. Trên cùng đầu vào ước lượng, Min Variance có rủi ro không lớn hơn chia đều; Max Sharpe có Sharpe không thấp hơn chia đều trong ví dụ kiểm thử. Không áp đặt điều kiện này lên kết quả ngoài mẫu.

## Mục 6 — Backtest và kiểm tra toàn quy trình

```powershell
& "D:\Back_test_goi_1\.venv\Scripts\python.exe" -m unittest discover -s tests -v
& "D:\Back_test_goi_1\.venv\Scripts\python.exe" run_six_steps.py --output six_steps_output
Start-Process .\six_steps_output\report.html
Start-Process .\six_steps_output\04_frontier.svg
```

Kết quả kiểm thử bản v3: **47 tests, OK**. File TEST_RESULTS_V3.txt ghi lại phiên bản và từng test.

Chạy từng dòng. Nếu output đã tồn tại, đổi tên thành `six_steps_output_02` trong cả lệnh chạy và mở file. Không cần xóa lần chạy trước.

Kết quả: 3 chiến lược × 4 mức phí, cộng một dòng benchmark cho mỗi chiến lược = 15 dòng bảng tổng hợp. Mỗi lần chạy có 59 tháng ngoài mẫu. Hai optimizer tính lại theo cửa sổ 24 tháng; chừa một tháng trễ trước đầu tư. RF kỳ vọng lấy trung bình RF trong đúng cửa sổ huấn luyện; Sharpe sau backtest dùng RF thực tế cùng kỳ.

## Đối chiếu sản phẩm theo số đầu tên file

| Mục | File trong thư mục kết quả |
|---|---|
| 1 | `01_SYNTHETIC_prices.csv`, `01_monthly_returns.csv`, `01_validation.json` |
| 2 | `02_expected_returns.csv`, `02_sample_covariance.csv`, `02_regularized_covariance.csv` |
| 3 | `03_weights.csv` |
| 4 | `04_frontier.csv`, `04_frontier_weights.csv`, `04_frontier.svg` |
| 5 | `05_in_sample_comparison.csv` |
| 6 | `06_comparison.csv`, `06_*_periods.csv`, `06_*_trades.csv`, `06_*_weights.csv`, report và biểu đồ |

Mục 2–5 của demo chỉ dùng cửa sổ huấn luyện đầu tiên, không dùng toàn mẫu để sinh trọng số backtest. Mục 6 ước lượng lại qua từng cửa sổ. Trọng số file 03 không phải danh mục cố định áp cho toàn bộ giai đoạn.

## Điều kiện chuyển mục 7

Đây là triển khai Markowitz với mean/covariance lịch sử. Nếu nhóm yêu cầu kỳ vọng lợi suất từ CAPM/FF3/FF5, phải thay bộ ước lượng theo đúng mô hình trước khi dùng kết quả nghiên cứu.

Nhóm còn phải chốt giai đoạn, universe, giá điều chỉnh/price vs total return, RF, benchmark, cửa sổ, lịch giao dịch, ridge và quy ước phí. Universe động và dữ liệu thiếu/hủy niêm yết vẫn cần quy tắc và mở rộng riêng; bản này chỉ dùng fixed universe đầy đủ. Không lọc các mã còn sống để giả vờ đã xử lý survivorship bias.

Sau khi xác nhận đầu vào phù hợp, chuyển giá tháng thật thành lợi suất bằng:

```powershell
& "D:\Back_test_goi_1\.venv\Scripts\python.exe" prepare_prices.py --input data/monthly_prices.csv --output data/returns.csv
```

CSV giá phải có `date,ticker,adjusted_price`. Tạo `config/research.json` từ `config/research.template.json`, thay các chỗ REPLACE_WITH/CONFIRM và cấu hình nhóm đã chốt. Template v3 đã nối 3 optimizer builtin; vẫn có thể dùng module:function của nhóm. Các đường dẫn trong config tính từ thư mục chứa config.

```powershell
& "D:\Back_test_goi_1\.venv\Scripts\python.exe" run_backtest.py --config config/research.json
```

Không chạy template chưa điền để tạo kết luận. Kết quả giả lập chỉ chứng minh code chạy đúng trên các trường hợp đã kiểm tra, không chứng minh hiệu quả đầu tư ngoài thực tế.
