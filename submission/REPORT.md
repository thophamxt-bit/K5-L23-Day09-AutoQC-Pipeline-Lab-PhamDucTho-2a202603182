# Báo cáo Day 09 — Phạm Đức Thọ, 2a202603182

## 1. Kết luận trước
- **Kết luận pipeline:** **HOLD** — Không còn lỗi bắt buộc (`0` lỗi `ERROR`), nhưng vẫn còn **38/203 ảnh (18,72%)** mang cảnh báo chưa được người duyệt $\ge$ ngưỡng `10,00%` nên cổng giữ ở trạng thái Hold (chỉ xuất bản nháp `submission/export/clean_v1`).
- **Số ảnh vào / ra:** **224 ảnh vào**, **203 ảnh ra** dataset (loại **21 ảnh** ở bước tiếp nhận: `3 BAD_SIZE` cạnh ngắn `< 250px`, `2 CORRUPT_IMAGE` không mở được, `8 DUP_IMAGE_EXACT` trùng từng byte, `3 DUP_IMAGE_NEAR` trùng gần đúng theo pHash, và `5 LEAK_TEST` trùng ảnh kho `test/val`). Toàn bộ lỗi cú pháp còn lại được máy sửa và các ảnh thiếu nhãn đã được xử lý trong ngân sách 80 ảnh duyệt, nhưng 38 ảnh cảnh báo cuối hàng đợi chưa kịp duyệt khiến lô dừng ở Hold.

## 2. Lỗi và phân việc
Tổng hợp từ `submission/reports/02_error_list_v1.txt`:

| Mã lỗi | Số ảnh/dòng | Ai sửa (máy/người) | Vì sao |
|---|---:|---|---|
| `BAD_CLASS_ID` | 6 | máy | ID lớp nằm ngoài `0..3` là lỗi cú pháp rõ ràng, máy xóa dòng (`drop_line`) vì không tự đoán được lớp đúng. |
| `BAD_CLASS_NAME` | 2 | máy | Sửa tên lớp trong `data.yaml` về đúng danh sách chuẩn `cfg["classes"]` (`rename_classes`). |
| `BAD_FORMAT` | 3 | máy | Dòng thiếu cột hoặc chứa `nan/inf` gây crash khi đọc nhãn, máy xóa dòng (`drop_line`). |
| `BAD_SIZE` | 3 | máy | Ảnh có cạnh ngắn `< 250px` không đạt chuẩn đầu vào, máy loại ảnh + nhãn (`remove_image`). |
| `BOX_OUT_OF_IMAGE` | 8 | máy | Box tràn viền `[0, 1]`, máy cắt an toàn về đúng biên ảnh (`clip_box`) mà vẫn giữ nguyên lớp. |
| `BOX_ZERO` | 4 | máy | Box có `w <= 0` hoặc `h <= 0` (không có diện tích), máy xóa dòng (`drop_line`). |
| `CORRUPT_IMAGE` | 2 | máy | File ảnh hỏng không mở được, máy loại bỏ (`remove_image`). |
| `DUP_BOX` | 7 | máy | Hai box cùng lớp trùng lặp gần như hoàn toàn (`IoU > 0.9`), máy xóa box lặp ở dòng sau. |
| `DUP_IMAGE_EXACT` | 8 | máy | Ảnh trùng từng byte (MD5), máy xóa bản dư để tránh lặp dữ liệu train. |
| `DUP_IMAGE_NEAR` | 3 | máy | Ảnh trùng gần đúng theo pHash (`phash <= 6`), máy xóa bản dư. |
| `LEAK_TEST` | 5 | máy | Ảnh bị rò rỉ từ tập `test/val`, máy bắt buộc xóa để đảm bảo đánh giá công bằng. |
| `MISSING_LABEL_FILE` | 6 | người | Ảnh chưa có file `.txt`, máy không thể tự bịa nhãn (và không tạo file rỗng vì rỗng = ảnh nền). |
| `BOX_HUGE` | 3 | người | Cảnh báo box chiếm `> 95%` ảnh, cần người xem vật có thực sự lớn vậy hay kéo nhầm. |
| `BOX_TINY` | 6 | người | Cảnh báo box cạnh ngắn `< 12px`, cần người phân biệt vật ở xa hay nhiễu gán nhãn. |
| `CLASS_RARE` | 4 | máy (gián tiếp) | Cảnh báo thống kê cho các ID lớp lạ (`-1, 4, 7, 93`); tự biến mất sau khi máy xóa `BAD_CLASS_ID`. |
| `EMPTY_LABEL` | 12 | người | File nhãn rỗng, cần người xác nhận là ảnh nền sạch hay người gán bỏ sót. |
| `POSSIBLE_FALSE_POS` | 29 | người | Box nhãn không khớp dự đoán model, cần người kiểm tra là nhãn thừa hay model bỏ sót. |
| `POSSIBLE_LOOSE_BOX` | 28 | người | Box đúng lớp nhưng lệch/lỏng so với model, cần người căn chỉnh lại cho khít vật. |
| `POSSIBLE_MISSING` | 53 | người | Model phát hiện vật nhưng nhãn không có, model có thể đoán nhầm nên người phải xác nhận. |
| `POSSIBLE_WRONG_CLASS` | 18 | người | Bất đồng lớp giữa nhãn và model, cần người đọc ngữ nghĩa ảnh để chốt lớp đúng. |

- **Vì sao `05_review_queue.csv` xếp ảnh đầu hàng như vậy?** Hàng đợi sắp xếp giảm dần theo điểm ưu tiên `priority` (tính bằng tổng `weight × (1 + conf)` của các cảnh báo trên ảnh đó, cộng thêm điểm cho các lỗi máy vừa sửa như `FIXED_DROP_LINE = 2`, `FIXED_CLIP_BOX = 1` và `NEEDS_LABEL = 10`). Nhờ vậy, những ảnh đứng đầu hàng (như `img_0020` đạt `11.524` và 6 ảnh `NEEDS_LABEL` đạt `10.0`) là các ảnh có lỗi nặng hoặc nhiều nghi vấn ngữ nghĩa có trọng số cao được ưu tiên đưa vào top 80 để xử lý trước.
- **Với ngân sách 80 ảnh, người xem được bao nhiêu lỗi ngữ nghĩa?** Trong tổng số **125 ảnh** vào hàng đợi (chứa **123 lỗi ngữ nghĩa** `POSSIBLE_*` ở `04_error_list_v2.csv`), với ngân sách **80 ảnh**, người duyệt đã xử lý được **94 / 123 lỗi ngữ nghĩa (76,42%)**; còn 29 lỗi ngữ nghĩa ở phần cuối hàng đợi chưa kịp duyệt.

## 3. Calibration (2 ngưỡng)
| Tham số | Khởi đầu | Đã chọn | Precision / Recall (trước → sau) | Lý do (đánh đổi) |
|---|---|---|---|---|
| `duplicates.phash_dist` | 2 | 6 | `DUP_IMAGE_NEAR`: 1.00 / 0.50 → 1.00 / 0.67 (F1: 0.67 → 0.80) | Tăng từ 2 lên 6 giúp bắt thêm ảnh trùng gần đúng (F1 từ 0.67 lên 0.80, và trên lô thực tế bắt thêm 1 cặp `DUP_IMAGE_NEAR` + 1 ảnh `LEAK_TEST`) mà vẫn giữ biên an toàn, tránh đặt quá cao (16–20) dễ xóa nhầm ảnh thật cùng bối cảnh. |
| `second_opinion.conf` | 0.25 | 0.6 | `WRONG_CLASS`: 0.56/0.83 → 0.62/0.83; `MISSING`: 0.50/1.00 → 0.57/1.00 | Tăng lên 0.6 giúp lọc bớt cảnh báo giả (tăng Precision, giảm hàng đợi từ 145 xuống 125 ảnh để tiết kiệm ngân sách 80 ảnh duyệt) mà không làm tụt Recall của `MISSING` (vẫn 1.00) và `WRONG_CLASS` (0.83). |

- **Một chỗ calibration có thể đánh lừa bạn:** Tập `calib` chỉ có 39 ảnh và rất ít cặp ảnh khác nhau nhưng giống bố cục, nên khi tăng `duplicates.phash_dist` lên `16` thì trên `calib` thấy F1 của `DUP_IMAGE_NEAR` đạt rất cao (`0.91`, Precision `1.00`, Recall `0.83`), dễ tạo cảm giác cứ đặt `16` là tối ưu. Nhưng trên dữ liệu thật (224 ảnh, nhiều cảnh đường phố tương tự nhau), ngưỡng pHash quá rộng có thể gắn nhầm hai ảnh khác nhau thành trùng lặp và xóa mất dữ liệu train hợp lệ; ngoài ra nếu lên `20` thì ngay trên `calib` `DUP_IMAGE_EXACT` đã tụt Recall từ `1.00` xuống `0.33` do gom cụm sai.

## 4. Cửa chặn và điều pipeline KHÔNG bắt được
- **(a) Chứng minh gate chặn đúng:** Khi chạy `python -m pipeline.run --budget 0 --reports work/rep_nb --export-dir work/exp_nb`, vì không có người duyệt nên 6 ảnh `MISSING_LABEL_FILE` vẫn còn nguyên sau vòng 2. Ở bước 4/5, gate kết luận **REWORK** (`Còn 6 lỗi bắt buộc (ERROR) chưa xử lý -> trả về Rework`), trả về **mã thoát `20`** và ở bước 5/5 **không xuất** dataset (`work/exp_nb` không được tạo).
- **(b) ≥ 2 điểm mù có bằng chứng:**
  1. **Box lỏng nhẹ hoặc sót ở `POSSIBLE_LOOSE_BOX`:** Trên tập `calib`, ngay cả ở cấu hình tốt nhất, `POSSIBLE_LOOSE_BOX` chỉ đạt Recall `0.20–0.40` (ở `conf=0.25` chỉ bắt được 2/5 ca, `conf=0.6` chỉ bắt 1/5 ca). Các box lệch nhẹ nhưng vẫn có IoU $\ge$ `iou_loose` (`0.5`) với model lớn sẽ lọt qua hoàn toàn.
  2. **Ảnh trùng biến đổi mạnh (xoay/cắt/nén mạnh):** Trên `calib` có 6 ca `DUP_IMAGE_NEAR`, ở `phash_dist = 2` chỉ bắt được 3/6 (`recall = 0.50`), và ở `phash_dist = 6` vẫn sót 2/6 (`recall = 0.67`). Những biến đổi làm thay đổi cấu trúc pHash mạnh sẽ không bị phát hiện.
  3. **Lỗi gán nhầm lớp trên ca khó hoặc ảnh nền `EMPTY_LABEL`:** Nếu model lớn `yolo26l` cũng đoán nhầm cùng lớp với người gán (hoặc độ tự tin `< 0.6`), `second_opinion` sẽ im lặng; đồng thời 12 ảnh `EMPTY_LABEL` máy không thể tự phân biệt là ảnh nền sạch hay bị bỏ sót toàn bộ nhãn.

## 5. Train: raw vs clean (tùy chọn, chấm riêng)
*(Chạy trên Google Colab T4 với `yolo26n.pt`, 20 epoch, 2 seed; biến thể `clean` được xuất trước bước tinh chỉnh `phash_dist=6, conf=0.6` nên có 205 ảnh).*

| biến thể | #ảnh train | số seed | map50 (TB ± độ lệch) | map50_95 (TB ± độ lệch) | precision (TB ± độ lệch) | recall (TB ± độ lệch) |
|---|---|---|---|---|---|---|
| raw | 224 | 2 | 0.726 ± 0.000 | 0.512 ± 0.004 | 0.764 ± 0.061 | 0.649 ± 0.028 |
| clean | 205 | 2 | 0.711 ± 0.021 | 0.500 ± 0.009 | 0.753 ± 0.054 | 0.620 ± 0.016 |

Chênh mAP50 (clean − raw) = **-0.015**.

- **So sánh với độ lệch chuẩn & kết luận trung thực:**
  - `raw` (224 ảnh): `mAP50 = 0.7258 ± 0.0002` (seed 0: `0.7256`, seed 1: `0.7259`).
  - `clean` (205 ảnh): `mAP50 = 0.7107 ± 0.0211` (seed 0: `0.6958`, seed 1: `0.7256`).
  - Chênh lệch `mAP50(clean − raw) = -0.0151` (`-0.015`), **nhỏ hơn độ lệch chuẩn giữa các seed của `clean` (`± 0.0211`)**. Độ chênh nằm hoàn toàn trong khoảng nhiễu giữa các seed (ở seed 1, `clean` đạt `0.7256` gần bằng `raw` `0.7259`). Với chỉ 2 seed trên tập test 100 ảnh, **chưa đủ bằng chứng kết luận** `clean` tốt hơn hay kém hơn `raw`.
- **Giả thuyết giải thích & cách kiểm:**
  1. **Ảnh rò rỉ từ tập test và ảnh trùng lặp làm thổi phồng điểm `raw`:** `raw` chứa **5 ảnh `LEAK_TEST`** trùng với tập test (theo cấu hình sau calibrate; 4 ảnh ở ngưỡng cũ) và **11 ảnh trùng** (`8 DUP_IMAGE_EXACT`, `3 DUP_IMAGE_NEAR`), khiến `raw` được học trước một phần đề thi trong khi `clean` đã loại bỏ hoàn toàn các ảnh này.  
     *Cách kiểm:* Đánh giá lại model `raw` trên tập test đã bỏ các ảnh rò rỉ hoặc train thêm biến thể `raw_no_leak` (chỉ xóa `LEAK_TEST`) rồi so `mAP50` với `clean`.
  2. **Tập `clean` vẫn còn lỗi ngữ nghĩa chưa duyệt hết do giới hạn ngân sách:** Hàng đợi vượt ngân sách 80 ảnh nên `clean` vẫn còn nhiều ảnh mang cảnh báo chưa được duyệt (các lỗi ngữ nghĩa ở cuối hàng đợi), đồng thời số ảnh giảm khiến các lớp ít mẫu như `truck` dao động mạnh hơn.  
     *Cách kiểm:* Chạy lại pipeline với ngân sách đủ lớn (vd. `--budget 150`) để duyệt hết toàn bộ hàng đợi (đạt `Release`) rồi train lại `clean` và so sánh `mAP50`.
  3. **Nhiễu ngẫu nhiên do tập test nhỏ (100 ảnh) và chỉ chạy 2 seed:** Một vài ảnh khó ở seed 0 đủ kéo tụt trung bình `clean` xuống dưới `raw`.  
     *Cách kiểm:* Tăng số seed lên 5 (`--seeds 0 1 2 3 4`) để đo độ ổn định và khoảng tin cậy.

## 6. Quyết định và ghi chú AI
- **(a) Quyết định cuối:** **HOLD** (chưa phát hành chính thức, chỉ xuất bản nháp để thử nghiệm). Để chuyển từ **Hold → Release**, cần tăng ngân sách duyệt (hoặc chia thêm ca duyệt) để xử lý hết **38 ảnh còn cảnh báo** ở cuối hàng đợi (đưa tỉ lệ ảnh cảnh báo chưa duyệt xuống `< 10%`), sau đó chạy lại `python -m pipeline.run` và train lại biến thể `clean` cuối cùng.
- **(b) Ghi chú dùng AI:**
  1. **Prompt chính:** Tóm tắt yêu cầu repo, giải thích ý nghĩa các tệp file của 4 module cần làm (`label_format`, `gate`, `autofix`, `second_opinion`), và yêu cầu viết code giải quyết đúng đặc tả trong docstring + quy tắc của `GUIDE.md`.
  2. **Cách kiểm code AI:** Review lại từng dòng code theo các ca biên (dòng trống giữ số dòng gốc, dòng dính 2 lỗi, box tràn hẳn ngoài ảnh, thứ tự xuất issue ở `second_opinion`), chạy toàn bộ unit test (`python -m pytest -q` đạt 79 passed) và chạy thực tế trên dữ liệu bằng `pipeline.calibrate` + `pipeline.run`.
  3. **1 lần AI sai / cần chỉnh:** Ban đầu khi chưa cập nhật ngưỡng calibrate vào `configs/pipeline.yaml`, báo cáo `REPORT.md` và `submission/reports/` vẫn dùng số liệu của ngưỡng khởi đầu (`phash_dist=2, conf=0.25`); sau khi phát hiện qua `check_submission.py`, đã cập nhật lại `configs/pipeline.yaml` (`6` và `0.6`) và chạy lại `python -m pipeline.run` để đồng bộ toàn bộ số liệu.
