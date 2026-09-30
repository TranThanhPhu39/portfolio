# Backtest — phần đóng góp của Thành

Gói độc lập để đặt trong thư mục `back_test_hoan_chinh/` của repo nhóm. Không ghi đè `src/`, cấu hình hoặc kết quả của các thành viên khác ở gốc repo.

**Code đã chạy thành công; dữ liệu nghiên cứu chưa được nghiệm thu độc lập.** Có 66 kiểm thử đạt, lần chạy 30 cổ phiếu Mỹ cho mục 1–6 và hai lần chạy VN theo kỳ. Không diễn giải nhãn PASS của chương trình là xác nhận mọi dữ liệu đúng hoặc chiến lược luôn thắng benchmark.

## 1. Mở báo cáo đã chạy

- `results/checklist_1_6/results/report.html`: mục 1–6, 30 mã Mỹ, RF Kenneth French; chỉ kiểm thử.
- `results/vn100_provided_final/report.html`: giữ lợi suất do nhóm cung cấp, 78 tháng ngoài mẫu (03/2020–08/2026).
- `results/vn100_prices_final/report.html`: tính lợi suất từ giá, 77 tháng ngoài mẫu (04/2020–08/2026).

Hai lần VN có số tháng khác nhau vì lần tính từ giá cần một giá quá khứ để tạo lợi suất đầu tiên. Không dùng chênh lệch Sharpe giữa hai báo cáo như một so sánh cùng mẫu. Cả hai dùng chỉ folder VN100 theo kỳ, không dùng Data tổng hợp; nhận danh sách do nhóm xác nhận nhưng chưa đối chiếu HOSE độc lập.

## 2. Cài đặt và chạy

Khuyến nghị Python 3.12. Đã kiểm thử Python 3.12.14, NumPy 1.26.0, pandas 2.2.0, SciPy 1.13.0. Không cần vnstock, yfinance hay statsmodels để chạy gói offline này. Các bộ giá/CSV đã đi kèm.

Mở PowerShell **tại thư mục có `run_all.py`** (không dán cây thư mục làm lệnh). Nếu đã có môi trường của Thành:

```powershell
$btPython = "D:\Back_test_goi_1\.venv\Scripts\python.exe"
& $btPython -m pip install -r .\requirements_backtest.txt
& $btPython .\verify_all.py
& $btPython .\run_all.py --return-basis provided --rf-basis annual_effective_percent
```

Lệnh cuối tự chạy lại test, mục 1–6, rồi VN; in đường dẫn báo cáo mới trong `results/local_<thời điểm>/`. Tên folder mới tránh ghi đè lần trước. RF năm hiệu dụng là **giả định quy đổi công khai**, chưa xác minh kỳ hạn/quotation của cột rRF trong các CSV.

Máy mới chưa có môi trường:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements_backtest.txt
.\.venv\Scripts\python.exe run_all.py --return-basis provided --rf-basis annual_effective_percent
```

Không tạo lại `.venv` khi đang sử dụng chính nó. Cảnh báo pandas về pyarrow không phải lỗi chạy. Nếu bộ test thất bại, `run_all.py` dừng trước khi chạy tiếp.

Chạy riêng VN tính từ giá:

```powershell
& $btPython .\run_vn100.py --output .\results\local_vn_prices_01 --return-basis prices --rf-basis annual_effective_percent --end 2026-08
```

Chọn tên output mới cho lần tiếp theo. `run_six_steps.py` là demo giả lập bốn mã, không phải điểm vào VN và không thay cho `run_checklist.py` dùng 30 mã thị trường.

## 3. Đối chiếu yêu cầu

| Mục | Triển khai | Bằng chứng đầu ra |
|---|---|---|
| 1: 20–30 mã | 30 mã giá điều chỉnh Yahoo lưu offline; RF Kenneth French | `results/checklist_1_6/data/quality.json`, `monthly_prices.csv`, `returns.csv` |
| 2: E và covariance | Trung bình lịch sử, covariance mẫu và ridge | `02_expected_returns.csv`, `02_sample_covariance.csv`, `02_regularized_covariance.csv` |
| 3: Markowitz long-only | SciPy SLSQP, tổng trọng số 1, không bán khống | `03_weights.csv`, nhật ký trọng số hàng tháng |
| 4: Efficient frontier | Quét mục tiêu lợi suất trên nhánh hiệu quả | `04_frontier.csv`, `04_frontier.svg`, `04_frontier_weights.csv` |
| 5: So sánh Sharpe | MaxSharpe, từng mã, trung bình Sharpe; cùng RF và cửa sổ | `05_sharpe_assets_comparison.csv`, metadata và đầu vào so sánh |
| 6: Walk-forward có phí | 24 tháng, trễ một tháng, tái cân bằng tháng, phí tự tài trợ | `*_periods.csv`, `*_trades.csv`, `*_weights.csv` và biểu đồ |
| 7: VN thật | Rổ theo kỳ, VN30 tham chiếu, chỉ mua mã đủ lịch sử | hai folder VN; `eligibility.csv`, `comparison.csv`, `RUN_STATUS.json` |
| Bổ sung phí | 0%; 0,15%; 0,25%; 0,35% | `sharpe_vs_fee.svg`, `comparison.csv`, `fee_crossings.json` |

Phí là tham số: API cố định `run_walk_forward(..., transaction_cost_rate=...)`; engine động `simulate_dynamic(..., rate)`. Bộ chạy VN dùng bốn kịch bản trên trong `run_vn100.py`. Không ép biểu đồ Sharpe giảm đơn điệu hoặc sửa số liệu để đạt điều kiện thắng benchmark. Tiêu chí mục 5 về vượt Sharpe từng mã là kết quả cần đối chiếu, không phải bảo đảm của định lý đa dạng hóa trong mọi mẫu.

## 4. Giả định quan trọng của lần chạy VN

- Chỉ mã trong rổ tháng giao dịch và đủ 24 tháng lợi suất lịch sử (đến t−2) được mua. Có 71–90 mã đủ điều kiện mỗi tháng, **không phải luôn nắm giữ đủ 100 mã**. Bảng loại trừ đi kèm.
- Thiếu dữ liệu trước lúc vào rổ có thể khiến mã bị loại dù đã niêm yết; không truy cập folder dự phòng để bổ sung vì yêu cầu của Thành.
- Tháng 09/2026 trong dữ liệu chỉ đến 25/09, nên kết thúc đánh giá ở 08/2026.
- `provided`: giữ cột Monthly Return (%) và chia 100; không âm thầm sửa những lợi suất bất thường.
- `prices`: tính P(t)/P(t−1)−1, không điền giá thiếu. Chưa xác minh cơ sở điều chỉnh giá/cổ tức.
- `annual_effective_percent`: RF tháng = (1+rRF/100)^(1/12)−1. Cần nhóm xác nhận nguồn và quy ước cột RF trước khi chốt nghiên cứu. Không khẳng định cột RF là kỳ hạn 1Y chỉ dựa vào độ lớn.
- Ngày công bố thành phần chưa được cung cấp riêng; giả định lịch rổ đã biết trước giao dịch. Không gọi đây là backtest point-in-time đã được xác minh đầy đủ.
- Cột lợi suất và giá nguồn có 515 cặp lệch quá 0,02 điểm phần trăm ở bản đã kiểm tra. Báo cáo kiểm tra trong `data_audit/`. Giữ nhãn chạy thử vì các khác biệt cơ sở giá chưa được giải thích.

## 5. Đưa lên GitHub

Giải nén ZIP. Upload thư mục **`back_test_hoan_chinh`**, không upload `.venv`, `__pycache__` hoặc ZIP. Không cần upload kết quả của những lần chạy mới trong `results/local_*`.

Chọn đúng nhánh nhóm giao trong giao diện GitHub trước khi upload. Gói đã có `.gitignore`, mã nguồn, test, dữ liệu đầu vào và kết quả mẫu.

Không có thao tác push trong gói; người dùng tự upload theo yêu cầu mới nhất. `METHOD_SPEC.md` là phương pháp hiện hành; `CHECKLIST_STATUS.json` là trạng thái thực thi, không chứng nhận nghiên cứu đạt 100%.
