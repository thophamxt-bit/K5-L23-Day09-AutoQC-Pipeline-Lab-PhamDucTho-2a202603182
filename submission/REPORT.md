# Báo cáo Day 09 — <Họ và tên>, <MSHV>

> Xoá mọi `TODO(học viên)` và dòng gợi ý. Mỗi ý trả lời bằng **số lấy từ `submission/reports/`**, kèm mẫu số. Cả báo cáo ~1–2 trang.

## 1. Kết luận trước
TODO(học viên): pipeline kết luận **Release / Hold / Rework**? 
HOLD — Không còn lỗi bắt buộc, nhưng có 60/205 ảnh (29.27%) còn cảnh báo chưa duyệt >= ngưỡng 10.00% -> Hold.


Bao nhiêu ảnh vào, bao nhiêu ảnh ra dataset? Lý do chính (1–3 câu).
224 ảnh vào, 205 ảnh ra dataset. Bởi vì có :
rror BAD_SIZE               3: cạnh ngắn là" img_0107,img_0113, img_0122"
error CORRUPT_IMAGE          2: không mở được là" img_0122,img_0136 "
error DUP_IMAGE_EXACT        8: trùng byte với các ảnh như "img_0012,img_0012,..."
error DUP_IMAGE_NEAR         2:trùng gần đúng với các ảnh"img_0042,img_0037"
error LEAK_TEST              4:rùng ảnh kho test/val là"test_033.jpg,test_044.jpg,test_085.jpg,test_009.jpg"

## 2. Lỗi và phân việc
Lấy từ `02_error_list_v1` (gom theo mã lỗi). Cột "ai sửa": **máy** (autofix) hay **người** (hàng đợi); chỉ ghi những mã có mặt trong lô của bạn.

| Mã lỗi | Số ảnh/dòng | Ai sửa (máy/người) | Vì sao |
||---:|---|---|
|  BAD_CLASS_ID  | 6| máy| ID lớp nằm ngoài 0..3, vì không tự đoán được lớp đúng|
| BAD_CLASSNAME |2| máy|Sửa tên lớp trong data.yaml|
|BAD_FORMAT |3| máy|Dòng thiếu cột gây crash khi đọc nhãn|
|BAD_SIZE   | 3| máy|Ảnh có cạnh ngắn < 250px không đạt chuẩn đầu vào|
|BOX_OUT_OF_IMAGE|8|máy|Boxtràn viền [0, 1], máy cắt an toàn về đúng biên ảnh|
|BOX_ZERO | 4|máy|Box có w <= 0 hoặc h <= 0 (không có diện tích),                            
|DUP_BOX||  7|máy|Hai box cùng lớp trùng lặp gần như hoàn toàn IoU > 0.9|
| DUP_IMAGE_EXACT|  8| máy|Ảnh trùng từng byte , máy xóa bản dư để tránh lặp dữ liệu train.|
| DUP_IMAGE_NEAR | 2|máy|Ảnh trùng gần đúng theo pHash, máy xóa bản dư.
|LEAK_TEST|4|máy|Ảnh bị rò rỉ từ tập test/val, máy bắt buộc xóa để đảm bảo đánh giá công bằng|
|MISSING_LABEL_FILE|6|người|Ảnh chưa có file .txt, máy không thể tự bịa nhãn|
|BOX_HUGE |3|người|Cảnh báo box chiếm > 95%
|BOX_TINY |6|người|Cảnh báo box cạnh ngắn < 12px, cần người phân biệt vật ở xa hay nhiễu gán nhãn.|
|CLASS_RARE| | 4|máy|Cảnh báo thống kê cho các ID lớp lạ|
|EMPTY_LABEL|  12|người|cần người xác nhận là ảnh nền sạch hay người gán bỏ sót|
|POSSIBLE_FALSE_POS|29|người|cần người xác nhận là ảnh nền người gán bỏ sót|
|POSSIBLE_LOOSE_BOX |45|người|Box đúng lớp nhưng lệch/lỏng so với model, cần người căn chỉnh lại cho khít vật.|
|POSSIBLE_MISSING |152|người|Model phát hiện vật nhưng nhãn không có, model có thể đoán nhầm nên người phải xác nhận|
|POSSIBLE_WRONG_CLASS | 22|người|Bất đồng lớp giữa nhãn và model, cần người đọc ngữ nghĩa ảnh để chốt lớp đúng.|

TODO(học viên): vì sao `05_review_queue.csv` xếp ảnh đầu hàng như vậy? 
Hàng đợi sắp xếp giảm dần theo điểm ưu tiên priority (tính bằng tổng weight × (1 + conf) của các cảnh báo trên ảnh đó, cộng thêm điểm cho các lỗi máy vừa sửa như FIXED_DROP_LINE = 2, FIXED_CLIP_BOX = 1 và NEEDS_LABEL = 10). Nhờ vậy, những ảnh đứng đầu hàng (như img_0160 đạt 35.692, img_0127 đạt 22.753, img_0020 đạt 17.449) là các ảnh tích tụ nhiều nghi vấn ngữ nghĩa có trọng số và độ tự tin cao
Với ngân sách 80 ảnh, người xem được bao nhiêu lỗi ngữ nghĩa?
243 lỗi ngữ nghĩa,xử lý được 187

## 3. Calibration (2 ngưỡng)
| Tham số | Khởi đầu | Đã chọn | Precision / Recall (trước → sau) | Lý do (đánh đổi) |
|---|---|---|---|---|
| `duplicates.phash_dist` | 2 | 6 | DUP_IMAGE_NEAR: 1.00 / 0.50 → 1.00 / 0.67 (F1: 0.67 → 0.80)| Tăng từ 2 lên 6 giúp bắt thêm ảnh trùng gần đúng (F1 từ 0.67 lên 0.80) mà vẫn giữ biên an toàn,|
| `second_opinion.conf` | 0.25 |0.6 |	WRONG_CLASS: 0.56/0.83 → 0.62/0.83; MISSING: 0.50/1.00 → 0.57/1.00 | Tăng lên 0.6 giúp lọc bớt cảnh báo giả (tăng Precision, tiết kiệm ngân sách 80 ảnh duyệt) mà không làm tụt Recall của MISSING (vẫn 1.00) và WRONG_CLASS (0.83)|

TODO(học viên): **một chỗ calibration có thể đánh lừa bạn**, kèm bằng chứng từ dữ liệu của bạn (vd. mở xem vài cặp ảnh bị cho là trùng; số ảnh bị loại ở bước 1 có hợp lý không?).

## 4. Cửa chặn và điều pipeline KHÔNG bắt được
TODO(học viên): (a) chứng minh gate chặn đúng: chạy `python -m pipeline.run --budget 0 --reports work/rep_nb --export-dir work/exp_nb` (không có người duyệt nên ảnh thiếu file nhãn còn nguyên), chỉ ra kết luận **Rework**, mã thoát 20 và việc **không xuất** dataset. (Đừng sửa tay `work/run/ds`: pipeline dựng lại thư mục này từ raw mỗi lần chạy.) (b) ≥ 2 điểm mù có bằng chứng (box lỏng nhẹ, nhầm lớp mà model lớn cũng nhầm, ảnh trùng biến đổi mạnh…).

Khi chạy python -m pipeline.run --budget 0 --reports work/rep_nb --export-dir work/exp_nb, vì không có người duyệt nên 6 ảnh Ở bước 4/5, gate kết luận REWORK (Còn 6 lỗi bắt buộc (ERROR) chưa xử lý -> trả về Rework), trả về mã thoát 20 và ở bước 5/5 không xuất dataset (work/exp_nb không được tạo).
## 5. Train: raw vs clean (tùy chọn, chấm riêng)
Chưa train: ghi "chưa chạy" và lý do, rồi bỏ qua phần còn lại của mục này. Nếu đã train: dán bảng từ `submission/results/comparison.md` (model, epoch, seed, số ảnh train mỗi biến thể).
| biến thể | #ảnh train | số seed | map50 (TB ± độ lệch) | map50_95 (TB ± độ lệch) | precision (TB ± độ lệch) | recall (TB ± độ lệch) |
|---|---|---|---|---|---|---|
| raw | 224 | 2 | 0.726 ± 0.000 | 0.512 ± 0.004 | 0.764 ± 0.061 | 0.649 ± 0.028 |
| clean | 205 | 2 | 0.711 ± 0.021 | 0.500 ± 0.009 | 0.753 ± 0.054 | 0.620 ± 0.016 |

Chênh mAP50 (clean − raw) = **-0.015**.


TODO(học viên): chênh mAP50 (clean − raw) so với **độ lệch chuẩn giữa các seed**

raw (224 ảnh): mAP50 = 0.7258 ± 0.0002 (seed 0: 0.7256, seed 1: 0.7259).

  
clean (205 ảnh): mAP50 = 0.7107 ± 0.0211 (seed 0: 0.6958, seed 1: 0.7256).

  
Chênh lệch mAP50(clean − raw) = -0.0151 (-0.015), nhỏ hơn độ lệch chuẩn giữa các seed của clean (± 0.0211).
; kết luận **trung thực** (nằm trong nhiễu thì nói là chưa kết luận được)
Độ chênh nằm hoàn toàn trong khoảng nhiễu giữa các seed và ở seed 1, clean đạt 0.7256 gần bằng raw 0.7259.Với chỉ 2 seed trên tập test 100 ảnh, chưa đủ bằng chứng kết luận clean tốt hơn hay kém hơn raw.
 ≥ 2 giả thuyết giải thích (ảnh trùng/rò rỉ test trong `raw`, nhãn máy còn lại trong `clean`, test chỉ 100 ảnh…) và cách kiểm.
1.Ảnh rò rỉ từ tập test và ảnh trùng lặp làm thổi phồng điểm raw: raw chứa 4 ảnh LEAK_TEST trùng với tập test (4% tập test) và 10 ảnh trùng (8 DUP_IMAGE_EXACT, 2 DUP_IMAGE_NEAR), khiến raw được học trước một phần đề thi trong khi clean đã loại bỏ hoàn toàn các ảnh này.
Cách kiểm: Đánh giá lại model raw trên 96 ảnh test (sau khi loại 4 ảnh rò rỉ) hoặc train thêm biến thể raw_no_leak (chỉ xóa 4 ảnh LEAK_TEST) rồi so mAP50 với clean.
2. Tập clean vẫn còn lỗi ngữ nghĩa chưa duyệt hết do giới hạn ngân sách: Hàng đợi có 145 ảnh nhưng chỉ duyệt được 80 ảnh, nên clean vẫn còn 60/205 ảnh (29,27%) mang cảnh báo chưa duyệt (gồm 56 lỗi ngữ nghĩa như thiếu box, nhầm lớp ở 52 ảnh cuối hàng đợi), đồng thời giảm từ 224 xuống 205 ảnh khiến các lớp ít mẫu như truck dao động mạnh hơn (-0.061).
Cách kiểm: Chạy lại pipeline với ngân sách đủ lớn để duyệt hết toàn bộ hàng đợi (đạt Release) rồi train lại clean và so sánh mAP50.

## 6. Quyết định và ghi chú AI
TODO(học viên): (a) quyết định cuối; nếu Hold/Rework cần làm gì để thành Release? (b) Dùng AI viết code? Ghi 3 dòng: tóm tắt yêu cầu repo , giải thích cho tôi ý nghĩa các tệp file của các model cần làm, hãy giúp tôi code ra các model giải quyết các vấn đề trên 
 cách bạn kiểm code AI, 1 lần AI sai.
 Review lại đoạn code,tìm ra lỗi sai theo các trường hợp đặc biệt về các chủ đề tương ứng với chủ đề hiện tại,nếu có bug  đưa ra hướng giải quyết tốt nhất
*(Thưởng +2, tùy chọn)* CVAT: lọc `width < 20`, ảnh/số box khớp, đối chiếu `BOX_TINY` (xem docs/CVAT_FILTER.md), 1 câu về `can_review`.
