# Trả lời nhận xét ngày 30/09 — cập nhật 01/10/2026

Nguồn: https://docs.google.com/document/d/1h0en39GLsip5OIXjF4w-17u2sMkwrrEuZQL0tFaO2Tw/edit

Nhận xét áp dụng cho các file ở gốc repo. Bản sửa này bổ sung trực tiếp module và test tại gốc, không chỉ đặt một gói riêng rồi coi lỗi gốc đã hết.

| Nhận xét | Cách xử lý |
|---|---|
| run_cost_scenarios thiếu, backtest rỗng | Khôi phục walk_forward, transaction_costs, benchmark, performance và dynamic; có mô phỏng, phí tự tài trợ, căn lịch, chỉ tiêu và kiểm tra dữ liệu |
| prices thiếu, optimizer rỗng | Thêm prices.py và optimizer SLSQP, covariance ridge; constraints.py xuất validator chung; efficient_frontier.py xuất hàm đường biên đã kiểm thử |
| reporting/charts thiếu | Thêm báo cáo HTML và SVG; bảng Sharpe từng mã, biểu đồ phí, drawdown và đường vốn |
| Test rỗng, số 47 không kiểm chứng | Thêm test thật tại tests/; verify_backtest.py chạy pytest và tạo BACKTEST_TEST_RESULTS.txt; không dùng số test cũ làm bằng chứng mới |
| Config và tài liệu thiếu | Thêm example.json chạy được, research.template.json có placeholder chủ ý, docs/input_contract.md và docs/decisions.md |
| CMD sai đường dẫn | Loại bỏ hướng dẫn dựa vào runner đã mất; dùng trực tiếp `run_backtest.py`, `run_vn100.py` và Python của môi trường đang kích hoạt |

## Lệnh tại gốc repo

```powershell
python -m pip install -r requirements_backtest.txt
python verify_backtest.py
python -m pytest tests -q
python run_backtest.py --config config/example.json
python run_vn100.py --input <thu_muc_du_lieu> --output local_runs/vn_01 --return-basis provided --rf-basis annual_effective_percent
```

`run_backtest.py` từ example tạo `sample_run`; hãy chọn output mới trong config nếu chạy lại. Các lệnh trên không ghi đè outputs của nhân tố/kinh tế lượng. Runner chung cũng hỗ trợ universe động bằng `config/dynamic.template.json`; membership phải được khai báo tường minh cho mọi cặp tháng/mã.

Để chạy VN dùng lệnh và giả định trong back_test_hoan_chinh/README.md hoặc root run_vn100.py. Các lỗi tích hợp được sửa không đồng nghĩa đã xác nhận dữ liệu/RF VN. Không thay đổi kết quả thống kê của nhóm khác để đạt một kết luận mong muốn.

## Kết quả kiểm tra bản sửa

- `python verify_all.py`: 76 passed (66 backtest/portfolio và 10 factor). Log: TEST_RESULTS.txt.
- `python verify_backtest.py`: 66 passed. Log: BACKTEST_TEST_RESULTS.txt.
- Chạy config/example.json thành công và sinh báo cáo HTML/SVG cùng CSV chi tiết. Chưa kiểm tra giao diện bằng mắt.
- Một cảnh báo pandas về PyArrow; không phải lỗi kiểm thử.
- Giữ nguyên outputs, src/models, src/factors và scripts của nhóm so với main.
- Root run_vn100.py chạy thành công 78 tháng cho MinVariance, MaxSharpe và EqualWeight với return-basis=provided, rf-basis=annual_effective_percent. Chỉ dùng folder VN100 theo kỳ. Trạng thái thực thi PASS; nghiệm thu nghiên cứu vẫn NOT_CONFIRMED vì đơn vị RF và các sai khác giá/lợi suất cần xác nhận.
- TEST_RESULTS_V3.txt là log lịch sử, không dùng nghiệm thu phiên bản hiện tại.
