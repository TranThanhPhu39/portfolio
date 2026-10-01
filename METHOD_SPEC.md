# METHOD SPEC — back_test_hoan_chinh

Phiên bản 2.0 — 30/09/2026. Thay thế bản 1.1 về tình trạng triển khai. Code hỗ trợ rổ cố định và rổ theo kỳ; kết quả VN hiện là chạy thử theo giả định, chưa nghiệm thu nguồn dữ liệu.

## Dữ liệu và mẫu

Mục 1–6: 30 mã Mỹ, giá điều chỉnh 2018–2022, RF Kenneth French và SPY tham chiếu; chỉ kiểm thử. Mục 7: chỉ 18 CSV theo kỳ của nhóm; 159 mã xuất hiện qua các kỳ. Lần chạy cột lợi suất nguồn có 78 tháng ngoài mẫu từ 03/2020 đến 08/2026; lần tính từ giá có 77 tháng từ 04/2020. Không so sánh trực tiếp hai Sharpe như cùng mẫu. Benchmark VN30 từ cột nguồn, chia 100.

Rổ theo tháng được lấy từ các mã hiện diện trong file kỳ. Thành viên phải có đủ 24 lợi suất tháng liên tiếp trong cửa sổ kết thúc tại t−2 để được mua trong tháng t. Danh sách đủ điều kiện không dựa trên lợi suất tương lai. 71–90 mã đủ điều kiện mỗi tháng; nhật ký ghi cả mã bị loại. Lịch sử ngoài rổ không được bổ sung từ folder dự phòng. Giả định thành phần đã biết trước giao dịch; ngày thông báo chưa được kiểm chứng độc lập. Rổ do nhóm xác nhận là VN100; chưa đối chiếu HOSE.

## Lợi suất và RF

Lợi suất dùng dạng thập phân. Chế độ provided lấy Monthly Return (%) / 100; prices dùng P(t)/P(t−1)−1, không forward-fill. Hai cơ sở được tách riêng, không sửa bản gốc. Giá chưa được xác minh điều chỉnh cổ tức/quyền. Tháng 09/2026 chỉ đến 25/09 nên loại khỏi cả hai lần chạy.

RF theo giả định năm hiệu dụng: (1+rRF/100)^(1/12)−1. Đây là giả định minh bạch; nguồn và kỳ hạn cột rRF vẫn cần xác nhận. Trung bình RF trong chính cửa sổ huấn luyện dùng cho mục tiêu MaxSharpe; RF thực của tháng đánh giá dùng tính excess return. Không dùng RF Mỹ cho VN.

## Ước lượng và tối ưu

mu là trung bình số học của lợi suất tháng; S là covariance mẫu với mẫu số L−1. Sigma = S + lambda I, lambda mặc định 1e−8 (phương sai lợi suất tháng dạng thập phân). Với L=24, hạng S tối đa 23; ridge xử lý suy biến nhưng không loại bỏ sai số ước lượng.

MinVariance tối thiểu w′Sigma w. MaxSharpe tối đa (w′mu−RF_train)/sqrt(w′Sigma w). Ràng buộc w>=0, tổng w=1; không giới hạn ngành hoặc trần trọng số riêng. Khi tồn tại excess return dương, code giải bài toán bậc hai tương đương min y′Sigma y với y′excess=1, y>=0, rồi chuẩn hóa w=y/sum(y); dùng SciPy SLSQP và co giãn để ổn định số học. Nhánh tỷ số trực tiếp vẫn làm phương án dự phòng; không thay bằng EqualWeight khi lỗi. Nếu mọi excess kỳ vọng không dương, chọn tài sản đơn lẻ có tỷ số cao nhất theo ràng buộc hiện tại. EqualWeight dùng 1/N của cùng tập đủ điều kiện.

Đường biên giải MinVariance tại các mức mục tiêu từ lợi suất danh mục phương sai tối thiểu đến mu lớn nhất; mặc định 30 điểm. Không ép hình dạng hoặc kết quả tốt hơn một đối chứng.

## Cuốn chiếu, giao dịch và phí

24 tháng từ t−25 đến t−2, bỏ tháng t−1, giao dịch trước lợi suất tháng t. Tái cân bằng mỗi tháng, vốn đầu 1, nắm giữ phân số. Mã rời rổ có mục tiêu 0 và bị bán tại biên kỳ; phí được tính. Mã thiếu lợi suất khi đang nắm giữ làm chương trình dừng, không thay bằng 0. Trọng số trước giao dịch phản ánh biến động giá kỳ trước.

Phí c trên từng chiều mua/bán; giải V_after + c sum|w_i V_after−h_i| = V_before. Có phí mua ban đầu, không thanh lý cuối mẫu. Turnover hai chiều = sum|trade_i|/V_before. Kịch bản c = 0, 0.0015, 0.0025, 0.0035; dùng cùng lịch trọng số mục tiêu, không tối ưu lại theo mức phí. Chưa mô hình riêng thuế, thanh khoản, lô giao dịch, trượt giá hoặc giới hạn khớp lệnh.

## Chỉ tiêu và đối chiếu

Sharpe năm = sqrt(12) mean(r−RF)/std(r−RF, ddof=1). CAGR = W_T^(12/T)−1. Maximum drawdown = min[W_t/max(1,W_1,...,W_t)−1], báo số âm. Tổng lợi suất W_T−1. Lợi suất ròng = V_end/V_before−1, đã trừ phí.

Bảng mục 5 đối chiếu trong cửa sổ đầu: MaxSharpe, từng mã và trung bình cộng Sharpe các mã, chung RF/thời gian, chưa phí. Trung bình Sharpe không phải Sharpe của EqualWeight. Mục tiêu dùng covariance ridge và RF trung bình, bảng thực nghiệm dùng SD excess return; hai thước đo có thể khác. Sharpe không xác định khi SD gần 0, không thay bằng 0.

Sharpe và drawdown VN dùng cùng lịch ngoài mẫu với VN30 trong mỗi lần chạy. VN30 là chuỗi tham chiếu không bị áp phí danh mục. Độ nhạy phí xuất bằng bảng và biểu đồ; không cưỡng ép giảm đơn điệu. Chỉ báo khoảng đổi dấu lợi thế giữa các mức phí quan sát, không gọi đó là ngưỡng chính xác hoặc bảo đảm luôn có ngưỡng.

## Giới hạn và kết luận được phép

66 unit/integration tests đạt; lần chạy 30 mã và hai lần VN hoàn tất. Đây là bằng chứng code thực thi, không chứng minh dữ liệu sạch 100%. Còn chênh lệch giá/lợi suất, 15 dòng thiếu giá, RF chưa xác nhận quotation, giả định giao dịch biên kỳ, thiếu lịch sử ngoài rổ, chưa kiểm tra công bố thành phần. Bộ này chưa dùng FF3/FF5 dự báo mu nên không kết luận về lợi ích đầu tư của mô hình nhân tố. Các biến BCTC không tham gia tối ưu hiện tại.

Để viết báo cáo nghiên cứu, mô tả đúng tập đủ điều kiện, cơ sở lợi suất, nguồn RF, ridge và giới hạn trên; không đổi nhãn chạy thử thành nghiệm thu. Xem README và CHECKLIST_STATUS.json để tìm từng đầu ra. Tài liệu Markowitz (1952) và Fama–French (2015) dùng làm căn cứ học thuật riêng, không phải nguồn cho các lựa chọn kỹ thuật của nhóm.
