# Audit Factor Team cho Mục 4.7

## Nguồn và phiên bản

- Period archive: `drive-download-20260929T114415Z-1-001.zip` — SHA-256
  `04F233A314C32E295D11874BF615A66B380E74EE7143A0E977196B3C6B896FE1`.
- Master/RF archive: `drive-download-20260929T113528Z-1-001.zip` — SHA-256
  `DD10BF9DF75D9CE3365A942345A1F5D6012E1E3DDD026AE4AE485CE1F1461DD3`.
- Factor code commit: `57c916834b8d6dbf32d02f81df271162884dbeb4`.
- `scripts/build_vn_period_factors.py` và `src/factors/` không có thay đổi chưa commit
  tại thời điểm chạy.

## Kết quả ba lần chạy

| Kịch bản | Khoảng output | MKT-RF | SMB/HML | RMW | SMB_FF5/CMA | Sort thiếu nhóm |
|---|---|---:|---:|---:|---:|---:|
| Lịch sáu tháng | 02/2018–07/2026 | 102 | 96 | 78 | 66 | 0/40 period-sort |
| Trọng số formation | 07/2018–06/2026 | 96 | 96 | 72 | 60 | 0/19 period-sort |
| Loại tài chính | 07/2018–06/2026 | 96 | 96 | 72 | 60 | 0/19 period-sort |

Mỗi period-sort có đủ sáu danh mục và mỗi danh mục có ít nhất một cổ phiếu.

## Lưu ý chất lượng dữ liệu

- Cả ba lần chạy giữ quan sát VIX.HM 07/2025 có mức sinh lợi trên 100%; đây là
  quan sát đã được pipeline gắn cờ, không phải lỗi phát sinh từ robustness.
- Bộ lịch sáu tháng thiếu lợi suất SSB.HM tại 07/2021 đối với universe kinh tế lượng
  cố định. Kinh tế lượng dùng 59 tháng chung, từ 08/2021 đến 06/2026, và ghi tháng
  bị loại trong `run_manifest.json`.
- `vn100_returns_clean.csv` của lần loại tài chính vẫn chứa 27 mã tài chính. Tùy chọn
  `--exclude-financials` loại các mã này khỏi factor sorts, không xóa chúng khỏi panel
  lợi suất. Vế trái được xử lý riêng bằng
  `config/vn_econometrics_universe_ex_financials.csv`, gồm đúng 30 mã phi tài chính.
