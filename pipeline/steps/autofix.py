"""BƯỚC 2/4 — Sửa tự động những lỗi bắt buộc mà máy sửa được AN TOÀN.   ★★

Test:  pytest tests/test_autofix.py -q

`fix(ds, issues, cfg) -> list[dict]`: duyệt `issues` (chỉ lỗi severity ERROR), sửa thẳng vào thư mục `ds`,
và trả về danh sách thay đổi; mỗi phần tử có khoá: image, line, action, before, after
(đây chính là file `03_fixes.csv` — bằng chứng pipeline đã làm gì, người có thể kiểm lại).

| code lỗi                                       | cách sửa                                    | action           |
|------------------------------------------------|---------------------------------------------|------------------|
| BAD_FORMAT, BAD_CLASS_ID, BOX_ZERO, DUP_BOX    | xoá dòng đó khỏi file nhãn                  | "drop_line"      |
| BOX_OUT_OF_IMAGE                               | cắt box về trong [0,1] (giữ nguyên lớp)     | "clip_box"       |
| MISSING_LABEL_FILE                             | KHÔNG sửa file (máy không thể bịa nhãn): ghi 1 dòng fix, before="(không có file)", after="chuyển người gán" | "needs_label" |
| BAD_CLASS_NAME                                 | ghi lại `names` trong data.yaml đúng `cfg["classes"]` | "rename_classes" |
| DUP_IMAGE_*, LEAK_TEST, CORRUPT_IMAGE, BAD_SIZE| xoá ảnh + nhãn khỏi `ds`                    | "remove_image"   |

Bẫy cần nghĩ tới (có test cho từng cái)
- Một file có NHIỀU dòng lỗi: số dòng trong `issues` là số dòng GỐC. Nếu xoá từng dòng một thì số dòng lệch.
  Gom theo file, rồi ghi lại MỘT lần.
- Sau khi cắt, box có thể không còn diện tích (nằm hẳn ngoài ảnh): lúc đó xoá dòng thay vì ghi box rỗng.
- Một dòng có 2 lỗi (vd. BOX_OUT_OF_IMAGE + DUP_BOX): xoá dòng thắng, chỉ ghi 1 fix `drop_line`, không ghi thêm `clip_box`. Dòng trống ở giữa file vẫn đếm vào số dòng gốc.
- Ảnh vừa bị xoá (DUP_IMAGE_*...) mà còn issue dòng của chính nó: bỏ qua êm, không được báo lỗi/chết.
- Không động tới lỗi WARN (cảnh báo là việc của người). Không sửa file ở `data/raw/` — chỉ sửa `ds`.
- Chạy lần 2 trên dữ liệu đã sửa phải không làm gì thêm (idempotent) — NGOẠI LỆ duy nhất: `needs_label` được ghi lại mỗi lần còn lỗi `MISSING_LABEL_FILE` (vì ảnh vẫn chưa có nhãn).

- `needs_label` KHÔNG tạo file nhãn rỗng (rỗng = "ảnh nền", khác với "chưa gán"). `review_queue` sẽ đẩy ảnh này lên đầu hàng đợi cho người.

Gợi ý: `yaml.safe_load / safe_dump`.
"""
from collections import defaultdict  # noqa: F401

import yaml  # noqa: F401

from ..common import ERROR, parse_yolo_line  # noqa: F401


DROP_CODES = {"BAD_FORMAT", "BAD_CLASS_ID", "BOX_ZERO", "DUP_BOX"}
REMOVE_IMAGE_CODES = {"LEAK_TEST", "CORRUPT_IMAGE", "BAD_SIZE"}


def fix(ds, issues, cfg):
    fixes = []
    removed_images = set()
    drop_by_file = defaultdict(set)
    clip_by_file = defaultdict(set)

    for iss in issues:
        if iss.severity != ERROR:
            continue

        code = iss.code
        stem = iss.image

        if code.startswith("DUP_IMAGE_") or code in REMOVE_IMAGE_CODES:
            if stem in removed_images:
                continue
            img_p = ds.image_path(stem)
            if img_p is not None and img_p.exists():
                img_p.unlink()
            lbl_p = ds.label_path(stem)
            if lbl_p.exists():
                lbl_p.unlink()
            removed_images.add(stem)
            fixes.append({
                "image": stem,
                "line": "",
                "action": "remove_image",
                "before": code,
                "after": "đã xoá ảnh và nhãn",
            })

        elif code == "BAD_CLASS_NAME":
            if ds.yaml_path.exists():
                data = yaml.safe_load(ds.yaml_path.read_text(encoding="utf-8")) or {}
                old_names = data.get("names")
                data["names"] = list(cfg["classes"])
                data["nc"] = len(cfg["classes"])
                ds.yaml_path.write_text(
                    yaml.safe_dump(data, sort_keys=False, allow_unicode=True),
                    encoding="utf-8",
                )
                fixes.append({
                    "image": stem,
                    "line": "",
                    "action": "rename_classes",
                    "before": str(old_names),
                    "after": str(data["names"]),
                })

        elif code == "MISSING_LABEL_FILE":
            fixes.append({
                "image": stem,
                "line": "",
                "action": "needs_label",
                "before": "(không có file)",
                "after": "chuyển người gán",
            })

        elif code in DROP_CODES and iss.line is not None:
            drop_by_file[stem].add(iss.line)

        elif code == "BOX_OUT_OF_IMAGE" and iss.line is not None:
            clip_by_file[stem].add(iss.line)

    all_stems = sorted(set(drop_by_file) | set(clip_by_file))
    for stem in all_stems:
        if stem in removed_images:
            continue
        lbl_p = ds.label_path(stem)
        if not lbl_p.exists():
            continue

        raw_lines = lbl_p.read_text(encoding="utf-8", errors="replace").splitlines()
        drops = drop_by_file[stem]
        clips = clip_by_file[stem]
        new_lines = []

        for line_no, text in enumerate(raw_lines, 1):
            if line_no in drops:
                fixes.append({
                    "image": stem,
                    "line": line_no,
                    "action": "drop_line",
                    "before": text,
                    "after": "",
                })
                continue

            if line_no in clips:
                try:
                    cls_id, cx, cy, w, h = parse_yolo_line(text)
                except ValueError:
                    fixes.append({
                        "image": stem,
                        "line": line_no,
                        "action": "drop_line",
                        "before": text,
                        "after": "",
                    })
                    continue

                x1 = max(0.0, cx - w / 2)
                y1 = max(0.0, cy - h / 2)
                x2 = min(1.0, cx + w / 2)
                y2 = min(1.0, cy + h / 2)
                if x2 <= x1 or y2 <= y1:
                    fixes.append({
                        "image": stem,
                        "line": line_no,
                        "action": "drop_line",
                        "before": text,
                        "after": "",
                    })
                    continue

                ncx = (x1 + x2) / 2
                ncy = (y1 + y2) / 2
                nw = x2 - x1
                nh = y2 - y1
                after = f"{cls_id} {ncx:.6f} {ncy:.6f} {nw:.6f} {nh:.6f}"
                new_lines.append(after)
                fixes.append({
                    "image": stem,
                    "line": line_no,
                    "action": "clip_box",
                    "before": text,
                    "after": after,
                })
                continue

            new_lines.append(text)

        lbl_p.write_text("\n".join(new_lines) + ("\n" if new_lines else ""), encoding="utf-8")

    return fixes
