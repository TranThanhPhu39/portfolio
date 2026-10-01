# VN100 exploratory backtest — 01/10/2026

## Trạng thái

Đã chạy thành công trên dữ liệu thị trường Việt Nam đã chuẩn hóa, nhưng **chưa nghiệm thu nghiên cứu**. Archive nguồn thô không có trong workspace; thời điểm công bố membership và đơn vị RF chưa được xác minh độc lập.

## Dữ liệu và phương pháp

- Nguồn trực tiếp: `outputs/vn_period_factors/vn100_returns_clean.csv` và `vn100_factors_monthly.csv`.
- Giai đoạn đầu vào: 07/2018–06/2026, 96 tháng.
- Universe: 145 mã hợp nhất, 100 thành viên mỗi tháng.
- Return: simple return tháng từ Close EOM; 11/9.600 quan sát dùng reported-return fallback.
- Cửa sổ huấn luyện: 24 tháng kết thúc tại t-2; lag triển khai một tháng.
- Ngoài mẫu: 71 tháng; 73–91 mã đủ điều kiện mỗi tháng.
- Chiến lược: MinVariance, MaxSharpe, EqualWeight; long-only, fully invested.
- Phí mỗi chiều: 0%, 0,15%, 0,25%, 0,35%.
- Benchmark chính: VNINDEX; độ nhạy: VN30.

## Kết quả tại phí 0,25% mỗi chiều

| Danh mục | Sharpe | CAGR | Max drawdown | Total return | Tổng phí/vốn đầu |
|---|---:|---:|---:|---:|---:|
| MinVariance | 0,7473 | 10,46% | -14,31% | 80,18% | 0,0866 |
| MaxSharpe | 1,3047 | 19,91% | -15,05% | 192,82% | 0,1442 |
| EqualWeight | 0,9319 | 21,35% | -34,37% | 214,14% | 0,0340 |
| VNINDEX, không mô phỏng phí | 0,7227 | 15,37% | -32,78% | 133,06% | — |
| VN30, không mô phỏng phí | 0,8130 | 18,24% | -34,63% | 169,44% | — |

Sharpe chiến lược giống nhau giữa hai lần chạy vì benchmark chỉ dùng để so sánh; đường lợi nhuận chiến lược, RF và optimizer không thay đổi.

## Vị trí kết quả

- Input đã chuyển đổi: `local_runs/vn100_inputs_20261001/`.
- Báo cáo VNINDEX: `local_runs/vn100_backtest_vnindex_20261001/report.html`.
- Báo cáo VN30: `local_runs/vn100_backtest_vn30_20261001/report.html`.
- Mỗi thư mục có `comparison.csv`, `run_metadata.json`, eligibility, periods, trades, weights và SVG.

## Hậu kiểm

- 24/24 tổ hợp chiến lược–mức phí đạt đẳng thức kế toán.
- Phí cộng từ trades khớp phí theo periods.
- Trọng số không âm và tổng bằng 1 tại mỗi ngày.
- Tất cả kịch bản dùng đúng 71 ngày ngoài mẫu.
- Hai lần chạy VNINDEX/VN30 tạo đường lợi nhuận chiến lược giống nhau.

## Điều kiện trước khi dùng trong báo cáo nghiên cứu

1. Khôi phục archive nguồn và lưu SHA-256 của từng file thô.
2. Xác nhận `rRF` là lợi suất năm hay tháng và cách chuyển đổi.
3. Xác nhận membership VN100 được công bố trước thời điểm giao dịch mô phỏng.
4. Duyệt 11 reported-return fallback và các chênh lệch return/giá đã được audit.
5. Chốt benchmark là VNINDEX hay VN30 và nêu rõ price return/total return.
6. Không chọn chiến lược hoặc tham số dựa riêng trên kết quả tốt nhất của chính mẫu này.
