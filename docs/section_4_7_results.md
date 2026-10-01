# Kết quả kiểm tra độ bền — Mục 4.7

| scenario | model | t_months | mean_r_squared | mean_abs_alpha_pct | grs_f | grs_p_value | hml_spanning_alpha_pct_per_month | hml_spanning_p_hac12 | hml_premium_mean_pct | hml_premium_t |
|---|---|---|---|---|---|---|---|---|---|---|
| baseline | CAPM | 60 | 0.3097 | 0.7006 | 0.4837 | 0.9738 | 0.8097 | 0.2666 | 1.7410 | 2.6027 |
| baseline | FF3 | 60 | 0.3683 | 0.7359 | 0.7079 | 0.8211 | 0.8097 | 0.2666 | 1.7410 | 2.6027 |
| baseline | FF5 | 60 | 0.4702 | 0.7923 | 0.7727 | 0.7519 | 0.8097 | 0.2666 | 1.7410 | 2.6027 |
| semiannual | CAPM | 59 | 0.3101 | 0.7273 | 0.4870 | 0.9720 | 0.5625 | 0.3127 | 1.5656 | 2.2914 |
| semiannual | FF3 | 59 | 0.3690 | 0.7593 | 0.9241 | 0.5854 | 0.5625 | 0.3127 | 1.5656 | 2.2914 |
| semiannual | FF5 | 59 | 0.4811 | 0.8163 | 0.9844 | 0.5218 | 0.5625 | 0.3127 | 1.5656 | 2.2914 |
| formation_weights | CAPM | 60 | 0.3097 | 0.7006 | 0.4837 | 0.9738 | 1.1256 | 0.0864 | 1.6692 | 2.8026 |
| formation_weights | FF3 | 60 | 0.3737 | 0.7614 | 0.7536 | 0.7748 | 1.1256 | 0.0864 | 1.6692 | 2.8026 |
| formation_weights | FF5 | 60 | 0.4806 | 0.7645 | 0.7669 | 0.7581 | 1.1256 | 0.0864 | 1.6692 | 2.8026 |
| ex_financials | CAPM | 60 | 0.2499 | 0.8562 | 0.5525 | 0.9441 | 1.3692 | 0.1425 | 1.9755 | 2.9311 |
| ex_financials | FF3 | 60 | 0.3583 | 0.9237 | 0.9134 | 0.5972 | 1.3692 | 0.1425 | 1.9755 | 2.9311 |
| ex_financials | FF5 | 60 | 0.4402 | 1.0788 | 0.9243 | 0.5854 | 1.3692 | 0.1425 | 1.9755 | 2.9311 |

P-value chính của hồi quy bao phủ HML trong bảng là HAC Bartlett, lag 12. CSV giữ thêm p-value OLS để đối chiếu.

## Kết luận dùng cho Mục 4.7

Kết quả định tính bền vững qua ba đặc tả thay thế. Không kiểm định GRS nào bác bỏ giả thuyết đồng thời alpha bằng 0 ở mức 5% (p-value nhỏ nhất = 0.5218).

Phần bù HML giữ dấu dương trong mọi trường hợp; t-stat nhỏ nhất là 2.2914. Alpha của hồi quy bao phủ HML cũng luôn dương nhưng không có ý nghĩa ở mức 5% theo HAC lag 12 (p-value lớn nhất = 0.3127). Trường hợp trọng số formation gần ngưỡng 10% (p = 0.0864), vì vậy không nên diễn giải HML là hoàn toàn dư thừa hoặc hoàn toàn độc lập.

Lịch sáu tháng sử dụng 59 tháng vì tháng 07/2021 thiếu lợi suất SSB.HM trong panel tương ứng. Loại tài chính làm R² giảm và alpha tuyệt đối tăng rõ rệt, đặc biệt ở FF5; do đó độ lớn kết quả phụ thuộc cấu trúc ngành, dù kết luận GRS và dấu HML không đổi.

Trong cả bốn đặc tả, FF5 có R² trung bình cao nhất nhưng không làm alpha tuyệt đối giảm một cách nhất quán. Bằng chứng ủng hộ khả năng giải thích tốt hơn của mô hình nhiều nhân tố, nhưng không ủng hộ kết luận rằng thêm nhân tố luôn cải thiện sai lệch định giá.
