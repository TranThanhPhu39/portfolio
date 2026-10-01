# Hướng dẫn kiểm tra phần backtest

## 1. Mở đúng thư mục

Giải nén gói bàn giao. Trong VS Code chọn File → Open Folder, mở thư mục chứa `run_backtest.py`, `src`, `tests`. Chọn Terminal → New Terminal; các lệnh dưới đây dùng PowerShell.

## 2. Tạo môi trường Python

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements_backtest.txt
.\.venv\Scripts\python.exe -m pip install "pytest>=8,<9"
```

Nếu `py` không có, thử `python -m venv .venv`. Không cần activate môi trường nên không cần sửa ExecutionPolicy. Đây là code Python, không chạy bằng R. Nếu cả hai lệnh không có, cần cài Python trước.

## 3. Test các phép tính và lỗi dữ liệu

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q
```

Kết quả đạt: cuối màn hình có `67 passed`, không có `FAILED` hoặc `ERROR`. Xem `TEST_RESULTS.txt` để đối chiếu lần chạy đã thực hiện khi bàn giao. Không dùng `unittest discover` cho toàn bộ thư mục vì `tests/test_factors.py` sử dụng trực tiếp pytest.

| File | Test gì? |
|---|---|
| transaction_costs.py | Phí mua ban đầu, phí cả mua và bán, bảo toàn vốn, không giao dịch thì không phí |
| walk_forward.py | Chỉ truyền cửa sổ quá khứ; lag; trọng số trôi theo giá; lịch chung giữa các mức phí |
| benchmark.py | Gộp lợi suất bằng tích; benchmark/RF thiếu tháng phải báo lỗi |
| performance.py | Sharpe dùng lợi suất vượt RF và SD mẫu; CAGR; drawdown tính cả vốn đầu; khoảng phí mất lợi thế |
| run_backtest.py | Nạp CSV, chặn dữ liệu sai, chạy nhiều adapter, xuất đủ file, không ghi đè kết quả |

Test hai adapter dùng cùng hàm chia đều chỉ kiểm tra đường chạy nhiều chiến lược; không kiểm chứng thuật toán Markowitz của nhóm.

## 4. Chạy toàn bộ quy trình bằng dữ liệu giả lập

Tạo một config cục bộ để không sửa config mẫu:

```powershell
Copy-Item config\example.json config\example.local.json
```

Sau đó **mở file `config/example.local.json` trong VS Code** và sửa giá trị `output_dir` thành một thư mục chưa tồn tại, ví dụ:

```json
"output_dir": "../sample_run_02"
```

Dòng JSON trên phải được sửa trong file, không nhập trực tiếp vào PowerShell. Dữ liệu mẫu đã có sẵn; chỉ cần chạy:

```powershell
.\.venv\Scripts\python.exe run_backtest.py --config config\example.local.json
Start-Process .\sample_run_02\report.html
```

Nếu `sample_run_02` đã tồn tại, chọn tên mới như `sample_run_03`. Chương trình cố ý không ghi đè lần chạy cũ.

Đối chiếu: bảng có 5 dòng (4 mức phí và benchmark), mỗi dòng 59 tháng ngoài mẫu; Sharpe không phí khoảng 0,385379, benchmark khoảng 0,398129. Dữ liệu demo không có lợi thế ngay cả khi chưa tính phí; đây là kết quả hợp lệ.

## 5. Đọc file kết quả

- `comparison.csv`: Sharpe năm, CAGR, drawdown, lợi suất toàn kỳ, tổng phí và turnover. CAGR/drawdown ở dạng thập phân; -0,20 là -20%.
- `*_periods.csv`: từng tháng, vốn đầu/cuối, phí, lợi suất ròng. Kiểm tra vốn cuối tháng trước bằng vốn đầu tháng sau.
- `*_trades.csv`: giao dịch và ngày đầu/cuối cửa sổ ước lượng. `trade_value` dương là mua, âm là bán. Tổng phí các mã trong tháng phải bằng phí của tháng.
- `*_weights.csv`: trọng số đầu mỗi kỳ sau tái cân bằng; tổng mỗi tháng bằng 1, không có số âm.
- `*_equity.svg`, `*_drawdown.svg`, `sharpe_vs_fee.svg`: biểu đồ mở trực tiếp trong VS Code hoặc trình duyệt.
- `run_metadata.json`: cấu hình, mã băm dữ liệu đầu vào, phiên bản thư viện, trạng thái khoảng phí mất lợi thế.
- `report.html`: xem bảng và biểu đồ chung. Không cần extension biểu đồ hoặc máy chủ web.

## 6. Chạy dữ liệu thật khi nhóm bàn giao

1. Nhận đúng dữ liệu/optimizer theo `docs/input_contract.md`. Chốt các lựa chọn ở `docs/decisions.md` trước khi diễn giải kết quả.
2. Copy `config/research.template.json` thành `config/research.json`. Thay tất cả nội dung `REPLACE_WITH`/`CONFIRM_`, đường dẫn và cấu hình được nhóm thống nhất. Các đường dẫn tính từ thư mục chứa config.
3. Đặt ba CSV vào thư mục `data`: lợi suất `date,ticker,return`; benchmark `date,return`; RF `date,rf_return`. Ngày cuối tháng, lợi suất dạng thập phân. Không tự xóa mã thiếu hoặc điền 0 để vượt qua kiểm tra.
4. Nhận adapter `group_optimizers.py` của nhóm với hai hàm `min_variance(history)` và `max_sharpe(history)`, trả Series trọng số theo mã. Hoặc sửa tên `module:function` trong config theo code thật. Backtest không tự thay solver lỗi bằng danh mục chia đều.
5. Chạy:

```powershell
.\.venv\Scripts\python.exe run_backtest.py --config config/research.json
Start-Process .\research_run\report.html
```

Nếu nhóm dùng rổ VN100 thay đổi theo thời gian, dùng `config/dynamic.template.json` với `membership.csv` tường minh hoặc runner `run_vn100.py`. Xem quy trình hiện hành và định dạng dữ liệu đầy đủ trong `README.md`; không đặt `universe_mode` thành fixed để bỏ qua lịch thành phần rổ.

## 7. Những gì gửi lại nhóm

Gửi code backtest, runner, tests, hướng dẫn và hợp đồng đầu vào. Sau khi có dữ liệu thật mới gửi thêm thư mục kết quả của hai chiến lược: bảng so sánh, ba loại biểu đồ, nhật ký giao dịch/trọng số và metadata. Giữ nguyên nhãn giả lập cho mọi kết quả demo; không dùng chúng để kết luận Markowitz tốt hơn VN30.

Phần code có thể kiểm thử độc lập ngay. Việc nghiệm thu nghiên cứu còn cần dữ liệu thật, optimizer thật, quyết định phương pháp và đối chiếu kết quả với nhóm; kiểm thử thành công không thay thế các bước đó.
