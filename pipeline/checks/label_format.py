"""CHECK 2 — Dòng nhãn YOLO: sai định dạng, ID lớp lạ, box tràn ảnh, box rỗng, box lặp.   (Script 2 trong slide)   ★★

Test:  pytest tests/test_label_format.py -q

Mỗi dòng nhãn: `id cx cy w h` (5 số, toạ độ 0–1). Trả về list[Issue]; `Issue.line` = số dòng (đếm từ 1).

| code             | severity | khi nào                                                                  |
|------------------|----------|--------------------------------------------------------------------------|
| BAD_FORMAT       | ERROR    | không đúng 5 cột số (dùng `parse_yolo_line`, bắt `ValueError`)           |
| BAD_CLASS_ID     | ERROR    | id lớp ngoài 0..len(ds.classes)-1                                        |
| BOX_ZERO         | ERROR    | w <= 0 hoặc h <= 0                                                       |
| BOX_OUT_OF_IMAGE | ERROR    | mép box vượt [0,1] quá `cfg["label_format"]["overflow_tol"]`; extra={"overflow": mức tràn} |
| DUP_BOX          | ERROR    | cùng lớp với một dòng TRƯỚC ĐÓ và IoU > `dup_box_iou`; báo ở dòng SAU    |
| BOX_TINY         | WARN     | cạnh ngắn của box (px) < `min_box_px`  (cần `ds.image_size(stem)`)       |
| BOX_HUGE         | WARN     | w*h > `max_box_frac`                                                     |

Gợi ý
- Mép trái = x - w/2, mép phải = x + w/2 (xem câu hỏi "dòng YOLO nào lỗi?" trong slide).
- Một dòng hỏng (BAD_FORMAT, BAD_CLASS_ID, BOX_ZERO) thì `continue`, đừng kiểm tiếp hình học của dòng đó.
- Dòng thiếu cột làm script của slide dừng giữa chừng: đây là lý do phải `try/except`.
- `iou_xywh(a, b)` có sẵn trong common.py.
- Ngưỡng nằm trong `cfg["label_format"]` — đừng viết cứng số vào code.
"""
from ..common import ERROR, WARN, Issue, iou_xywh, parse_yolo_line  # noqa: F401


def run(ds, cfg):
    c = cfg["label_format"]
    issues = []
    n_classes = len(ds.classes)

    for lp in ds.label_files():
        stem = lp.stem
        lines = ds.read_label_lines(stem)
        if not lines:
            continue

        size = ds.image_size(stem)
        prev_boxes = []

        for line_no, text in lines:
            try:
                cls_id, cx, cy, w, h = parse_yolo_line(text)
            except ValueError as e:
                issues.append(Issue("label_format", ERROR, "BAD_FORMAT", stem, f"sai định dạng YOLO: {e}", line=line_no))
                continue

            if cls_id < 0 or cls_id >= n_classes:
                issues.append(Issue("label_format", ERROR, "BAD_CLASS_ID", stem, f"id lớp {cls_id} ngoài 0..{n_classes - 1}", line=line_no))
                continue

            if w <= 0 or h <= 0:
                issues.append(Issue("label_format", ERROR, "BOX_ZERO", stem, "box có kích thước <= 0", line=line_no))
                continue

            x1, y1 = cx - w / 2, cy - h / 2
            x2, y2 = cx + w / 2, cy + h / 2
            overflow = max(0.0, -x1, -y1, x2 - 1.0, y2 - 1.0)
            if overflow > c["overflow_tol"]:
                issues.append(
                    Issue(
                        "label_format",
                        ERROR,
                        "BOX_OUT_OF_IMAGE",
                        stem,
                        f"box tràn khỏi ảnh {overflow:.4f}",
                        line=line_no,
                        extra={"overflow": overflow},
                    )
                )

            cur_box = (cx, cy, w, h)
            if any(p_cls == cls_id and iou_xywh(cur_box, p_box) > c["dup_box_iou"] for p_cls, p_box in prev_boxes):
                issues.append(Issue("label_format", ERROR, "DUP_BOX", stem, "box trùng với dòng trước đó", line=line_no))
            prev_boxes.append((cls_id, cur_box))

            if size is not None:
                img_w, img_h = size
                if min(w * img_w, h * img_h) < c["min_box_px"]:
                    issues.append(Issue("label_format", WARN, "BOX_TINY", stem, "box quá nhỏ", line=line_no))

            if w * h > c["max_box_frac"]:
                issues.append(Issue("label_format", WARN, "BOX_HUGE", stem, "box quá lớn", line=line_no))

    return issues
