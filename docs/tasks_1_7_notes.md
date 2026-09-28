# Ghi chú nhiệm vụ 1–7 — Factor Team

## 1. Dữ liệu kiểm thử

`get_test_data.py` đã tạo đủ năm file trong `test_data/`:

- `ff3_factors_monthly.csv`: Mkt-RF, SMB, HML, RF của Kenneth French.
- `ff5_factors_monthly.csv`: Mkt-RF, SMB, HML, RMW, CMA, RF.
- `25_portfolios_size_bm.csv`: 25 danh mục Size–B/M cho hồi quy và GRS.
- `us_test_prices.csv`: adjusted close ngày của 30 mã Mỹ.
- `us_test_characteristics.csv`: Size và B/M giả lập để kiểm tra code.

## 2. Cấu trúc FF3

Mỗi dòng là một tháng. Script nguồn đã chia dữ liệu Kenneth French cho 100,
do đó các cột trong CSV là số thập phân: `0.02 = 2%`.

- `Mkt-RF`: lợi suất thị trường vượt lãi suất phi rủi ro.
- `SMB`: Small Minus Big, phần bù quy mô.
- `HML`: High Minus Low, phần bù giá trị.
- `RF`: lãi suất phi rủi ro tháng.

## 3–4. Sort 2x3 và SMB/HML

`src/factors/portfolio_sort.py` chia toàn bộ mã thành SL/SN/SH/BL/BN/BH.
Hàm kiểm tra index, dữ liệu thiếu và bảo đảm không mã nào bị bỏ sót.

`src/factors/smb_hml.py` hỗ trợ cả equal-weighted và value-weighted:

`SMB = mean(SL, SN, SH) - mean(BL, BN, BH)`

`HML = mean(SH, BH) - mean(SL, BL)`

## 5. Đối chiếu Kenneth French

`scripts/run_us_factor_demo.py` chuyển adjusted price ngày thành giá cuối tháng,
tính lợi suất tháng, căn chỉnh theo tháng và xuất correlation/biểu đồ. Dữ liệu thử
chỉ gồm 30 mã lớn, Size/B/M giả lập và formation weights cố định nên correlation
không phải tiêu chí xác nhận tính đúng của phương pháp.

## 6. RMW và CMA

`src/factors/rmw_cma.py` đã cài đặt sort Size–OP và Size–Investment. OP và Inv
trong demo là số giả lập có seed cố định, chỉ để kiểm thử. Kết luận nghiên cứu chỉ
được thực hiện khi thay bằng BCTC point-in-time.

## 7. Điều kiện để chạy VN100

Dataset dạng long cần tối thiểu các cột:

`date, ticker, adjusted_price, market_cap, book_to_market, operating_profitability, investment, information_date`

Trong đó `information_date` là ngày số liệu BCTC đã có thể được nhà đầu tư biết.
Formation cuối tháng 6/tái cân bằng tháng 7 năm t chỉ dùng BCTC năm t-1 đã công bố
trước ngày formation. Giá phải là giá điều chỉnh. Mã có book equity không dương
hoặc thiếu dữ liệu phải được loại theo quy tắc công khai và xuất audit table ghi
rõ lý do loại.

Đầu ra cuối: factor returns tháng, mean, std, t-stat, correlation matrix và biểu
đồ chuỗi thời gian. Task 7 chưa thể tạo kết quả số nếu chưa có dataset VN100 thật.
