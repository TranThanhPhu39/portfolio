# Điểm vào các phần của nhóm

**Sửa nhận xét 30/09:** các runner backtest ở gốc repo đã có module, test và config đầy đủ. Xem [bảng trả lời từng lỗi](docs/backtest_review_resolution.md). Tại gốc repo chạy `python -m pip install -r requirements_backtest.txt`, rồi `python verify_all.py`. Demo cố định chạy bằng `python run_backtest.py --config config/example.json`; dữ liệu VN100 theo kỳ chạy bằng `run_vn100.py` với các giả định được khai báo rõ.

- **Backtest hiện hành của Thành:** [back_test_hoan_chinh/README.md](back_test_hoan_chinh/README.md). Chạy script trong thư mục này để dùng đúng mã nguồn và dữ liệu đi kèm.
- **Kinh tế lượng:** [docs/econometrics_audit_guide.md](docs/econometrics_audit_guide.md).
- **Nhân tố VN:** [docs/vn_period_factor_pipeline.md](docs/vn_period_factor_pipeline.md).

Các thư mục `config/` và `outputs/` ở gốc được giữ để phục vụ phần nhân tố và kinh tế lượng. Phần hướng dẫn v3 dưới đây là tài liệu cũ, không phải lệnh chạy gói backtest theo kỳ hiện hành.

# Bản v3: hướng dẫn chính là TEST_6_MUC.md

Đã bổ sung src/portfolio/prices.py và markowitz.py cho các mục 1–5, run_six_steps.py chạy cả 6 mục trên giá tháng giả lập, prepare_prices.py chuẩn bị giá tháng thật. Hai optimizer builtin dùng mean/covariance lịch sử, long-only; không phải mô hình kỳ vọng CAPM/FF.

Đọc TEST_6_MUC.md trước. Các nội dung dưới mô tả engine ban đầu; hướng dẫn mới thay thế phần yêu cầu phải nhận optimizer từ nhóm nếu dùng baseline builtin. Nhóm vẫn phải duyệt phương pháp và dữ liệu trước mục 7.

# Phần backtest của Thành - bộ code bàn giao v3

Gói này để ghép vào repo `TranThanhPhu39/portfolio`. Được tạo cục bộ; chưa push hoặc sửa repo trên GitHub. Có thêm baseline tối ưu Markowitz và xử lý giá tháng để kiểm tra sáu mục; chưa thay code hoặc push lên repo nhóm.

Hướng dẫn chạy từng bước: **HUONG_DAN_TEST.md**. Runner CSV: `run_backtest.py`; cấu hình mẫu cố định: `config/example.json`; template nghiên cứu cố định: `config/research.template.json`; template universe động: `config/dynamic.template.json`. Kết quả kiểm thử hiện tại được tạo bằng `verify_all.py`; `TEST_RESULTS_V3.txt` chỉ là log lịch sử.

## Trạng thái

- Đã viết tính phí, mô phỏng cuốn chiếu, chỉ tiêu hiệu quả, so sánh benchmark và chạy kịch bản phí.
- Đã có kiểm thử tự động với kết quả tính tay và các trường hợp lỗi.
- demo_synthetic.py vẫn là demo chia đều cũ. run_six_steps.py chạy Min Variance, Max Sharpe và chia đều trên dữ liệu giả lập; không phải kết quả VN30 và không dùng làm kết luận nghiên cứu.
- Chưa nhận dữ liệu thật và quyết định phương pháp cuối cùng. Baseline tối ưu lịch sử đã có nhưng cần nhóm xác nhận phù hợp đề tài.
- Bản đầu chỉ hỗ trợ bảng lợi suất tháng liên tục, tập cổ phiếu cố định, không thiếu dữ liệu. Chưa hỗ trợ universe thay đổi theo lịch sử: không được dùng việc chọn các mã sống sót đầy đủ để gọi là nghiên cứu VN100 không có survivorship bias.

## Chạy trên máy

Mở thư mục này trong VS Code, dùng Python 3.10 trở lên:

```sh
python -m pip install -r requirements_backtest.txt
python -m unittest discover -s tests -v
python demo_synthetic.py
```

Demo xuất `demo_outputs/report.html`, bảng CSV, lịch sử giao dịch, trọng số, cấu hình và ba biểu đồ SVG. Mở report.html bằng trình duyệt. Mọi kết quả demo phải giữ nhãn SYNTHETIC. Chạy lại ghi đè các kết quả demo cùng tên.

## Các file thuộc phần Thành

| File | Nhiệm vụ |
|---|---|
| src/backtest/transaction_costs.py | Tính tiền mua/bán, phí và kiểm tra cân đối vốn |
| src/backtest/walk_forward.py | Lịch tối ưu theo cửa sổ, mô phỏng danh mục và kịch bản phí |
| src/backtest/performance.py | Sharpe, CAGR, drawdown và khoảng phí mất lợi thế |
| src/backtest/benchmark.py | Căn chỉnh benchmark/RF; gộp lợi suất ngày thành tháng |
| tests/test_backtest.py | Kiểm thử độc lập với dữ liệu thật |
| demo_synthetic.py | Ví dụ kết nối, xuất bảng và biểu đồ bằng dữ liệu giả lập |
| docs/input_contract.md | Quy định đầu vào gửi nhóm data/optimization |
| docs/decisions.md | Giả định bản đầu và các nội dung nhóm phải chốt |

Không chép đè src/__init__.py hoặc các file khác nếu repo nhóm đã cập nhật. Khi tích hợp, so sánh thay đổi và chỉ đưa phần cần thiết vào nhánh làm việc của Thành.

## Cách kết nối optimizer thật

```python
import pandas as pd
from src.backtest.walk_forward import run_cost_scenarios
from src.backtest.performance import comparison_table, fee_crossings

# returns: DataFrame lợi suất tháng dạng số thập phân, cột là mã cổ phiếu.
# risk_free và benchmark: Series cùng ngày, lợi suất tháng, KHÔNG phải mức giá.
# optimizer(history) -> Series trọng số có index là mã cổ phiếu.
# Thay bằng hàm đã thống nhất với người làm Markowitz.
results = run_cost_scenarios(
    returns, optimizer,
    lookback=24,                  # ví dụ, CHƯA CHỐT với nhóm
    rebalance_every=1,            # ví dụ, CHƯA CHỐT với nhóm
    decision_lag_periods=1,       # một tháng trễ để triển khai, xem bên dưới
    rates=(0.0, 0.0015, 0.0025, 0.0035),
)
summary = comparison_table(results, risk_free, benchmark)
print(summary)
print(fee_crossings(summary))
```

Chạy riêng với optimizer Min Variance và optimizer Max Sharpe khi nhận hai hàm thật. Nếu Max Sharpe cần RF kỳ vọng, hàm optimizer phải sử dụng RF đã biết tại ngày train_end; không truyền RF tương lai. Backtest dùng lợi suất thực tế chưa trừ RF để cập nhật tài sản; chỉ trừ RF khi tính Sharpe.

## Cơ chế thời gian và lợi suất

- Mỗi dòng ngày cuối tháng t chứa lợi suất đơn từ cuối tháng t-1 đến cuối tháng t. Không dùng log-return trực tiếp.
- `decision_lag_periods=1` mặc định: đầu tư trong tháng t dựa trên cửa sổ kết thúc tháng t-2. Tháng t-1 là khoảng trễ triển khai. Đây là giả định bảo thủ để không khớp lệnh tại đúng giá đóng cửa vừa dùng để tối ưu; không phải lịch T+ của thị trường.
- Ví dụ demo 84 tháng, 24 tháng ước lượng, thêm 1 tháng trễ: còn 59 tháng ngoài mẫu.
- `decision_lag_periods=0` chỉ phù hợp nếu nhóm chấp nhận giả định ra quyết định và khớp tại cùng giá cuối kỳ trước, hoặc đầu vào đã được xây theo giá thực thi tương thích. Không dùng mặc định để tuyên bố không có look-ahead.
- Giao dịch ở đầu kỳ đầu tư; tính phí trước, sau đó áp dụng lợi suất kỳ đó. Giữa hai lần tái cân bằng, giữ khoản đầu tư để trọng số tự thay đổi theo giá.
- Chỉ số `market_return` là lợi suất phần tài sản sau tái cân bằng trước tác động phí kỳ đó. Muốn đường không phí, dùng kết quả chạy độc lập với rate=0, không cộng phí cơ học vào net_return.

## Quy ước chi phí - bản đầu, cần nhóm xác nhận

`transaction_cost_rate` là tỷ lệ chi phí trên từng đồng giá trị mua HOẶC bán. Bán 10 và mua 10 tạo tổng giá trị giao dịch 20. Đây không phải mức phí tính một lần cho cả vòng mua-bán và không phải phí trên toàn bộ tài sản mỗi tháng.

Với V là vốn trước giao dịch, h là giá trị đang nắm giữ, w là trọng số mục tiêu và c là phí, hàm giải:

`V_after + c * sum(abs(w * V_after - h)) = V`

Phí được trả từ vốn, không vay tiền để trả phí. Tính cả phí mua ban đầu từ tiền mặt. Không tính phí thanh lý cuối mẫu: tài sản cuối mẫu được định giá theo thị trường, chưa bán hết. Thuế, trượt giá, tác động thị trường chỉ được xem là có nếu nhóm định nghĩa chúng đã nằm trong c; bản này không tự thêm khoản nào.

`turnover_two_way = (giá trị mua + giá trị bán) / vốn trước giao dịch`, không nhân 1/2. Phí trên mỗi giao dịch được ghi trong bảng trades. Không cộng các tỷ lệ turnover rồi gọi đó là phần trăm vốn mất đi; tiền phí phải lấy từ cột fee.

## Chỉ tiêu

- Sharpe năm = sqrt(12) * mean(lợi suất tháng sau phí - RF tháng) / sd(lợi suất tháng sau phí - RF tháng), sd mẫu ddof=1. Đây là quy ước annualization thông dụng; không bảo đảm điều chỉnh đúng khi có tự tương quan. Không dùng Sharpe làm kiểm định ý nghĩa thống kê.
- Độ lệch chuẩn gần bằng 0: Sharpe trả NaN, không trả 0 hay vô cực để giả vờ có kết quả.
- CAGR = (giá trị cuối / giá trị đầu)^(12/số tháng) - 1.
- Maximum drawdown trả số âm, tính cả vốn ban đầu để không bỏ sót khoản lỗ ở tháng đầu. Drawdown dựa trên dữ liệu tháng sẽ không phản ánh sụt giảm trong tháng.
- Benchmark được căn chỉnh đúng kỳ ngoài mẫu; thiếu ngày sẽ báo lỗi thay vì tự bỏ dòng. Benchmark là chỉ số tham chiếu không phí; phải ghi rõ cơ sở cổ tức/price return/total return và khả năng đầu tư thực tế.
- `fee_crossings` chỉ báo khoảng giữa các mức phí đã thử. Không ngoại suy ra một ngưỡng chính xác và không buộc Sharpe giảm đơn điệu. Khi phí 0 đã không thắng benchmark, báo không có lợi thế ban đầu.

Tham khảo công thức Sharpe: William F. Sharpe (1994), The Sharpe Ratio, https://web.stanford.edu/~wfsharpe/art/sr/SR.htm . Markowitz (1952) là cơ sở tối ưu của nhóm, không phải nguồn quy định cửa sổ 24 tháng hoặc mức phí của demo.

## Giới hạn nghiên cứu và bước tiếp theo

Chưa mô phỏng khớp lệnh thực tế, lô cổ phiếu, trần/sàn, ngừng giao dịch, thanh khoản, thanh toán T+, cổ phiếu mới vào/rời rổ, hủy niêm yết hoặc lợi suất -100%. Các trường hợp dữ liệu thiếu và return <= -100% hiện bị từ chối rõ ràng, không tự điền 0. Không sử dụng kết quả bản đầu để khẳng định đã mô phỏng đầy đủ thị trường Việt Nam.

Thứ tự tiếp: nhận dữ liệu và optimizer thật; chốt decisions.md; kiểm tra universe theo lịch sử và cách thực thi; mở rộng engine nếu cần; mới chạy nghiên cứu và viết kết luận. Không lựa chọn cửa sổ/tần suất chỉ vì cho Sharpe tốt nhất trên chính mẫu đánh giá.
