"""BƯỚC 4 — Cửa chặn: quyết định Release / Hold / Rework.   ★

Test:  pytest tests/test_gate.py -q

Cây quyết định Day 07 (slide Day 09: "Lỗi bắt buộc chặn pipeline; lỗi cảnh báo chuyển người xem"):

  còn ≥ 1 lỗi bắt buộc (severity ERROR)                          -> "Rework"
  không còn lỗi bắt buộc, nhưng tỉ lệ ẢNH còn cảnh báo
      >= cfg["gate"]["warn_ratio_hold"]                          -> "Hold"
  còn lại                                                        -> "Release"

Tỉ lệ cảnh báo = (số ẢNH khác nhau có ≥ 1 cảnh báo) / (tổng số ảnh).  Chú ý:
- chỉ đếm issue có `image` nằm trong `image_stems` (bỏ "<dataset>", "data.yaml");
- bỏ qua ảnh nằm trong `reviewed` (người đã xem, cảnh báo của ảnh đó coi như đã xử lý) — nhưng LỖI BẮT BUỘC thì không bao giờ được bỏ qua;
- mẫu số là số ảnh, không phải số issue.

Trả về dict: decision, n_errors, n_warn_images, n_images, warn_ratio (làm tròn 4 chữ số), reasons (list[str], giải thích bằng tiếng Việt, có số liệu).
"""
from ..common import ERROR, WARN  # noqa: F401


def decide(issues, image_stems, cfg, reviewed=frozenset()):
    stems = set(image_stems)
    reviewed_set = set(reviewed)
    hold_thresh = cfg["gate"]["warn_ratio_hold"]

    n_errors = sum(1 for iss in issues if iss.severity == ERROR)
    warn_images = {
        iss.image
        for iss in issues
        if iss.severity == WARN and iss.image in stems and iss.image not in reviewed_set
    }
    n_warn_images = len(warn_images)
    n_images = len(image_stems)
    warn_ratio = round(n_warn_images / n_images, 4) if n_images else 0.0

    reasons = []
    if n_errors >= 1:
        decision = "Rework"
        reasons.append(f"Còn {n_errors} lỗi bắt buộc (ERROR) chưa xử lý -> trả về Rework.")
    elif warn_ratio >= hold_thresh:
        decision = "Hold"
        reasons.append(
            f"Không còn lỗi bắt buộc, nhưng có {n_warn_images}/{n_images} ảnh "
            f"({warn_ratio:.2%}) còn cảnh báo chưa duyệt >= ngưỡng {hold_thresh:.2%} -> Hold."
        )
    else:
        decision = "Release"
        reasons.append(
            f"Không còn lỗi bắt buộc và chỉ {n_warn_images}/{n_images} ảnh "
            f"({warn_ratio:.2%}) còn cảnh báo chưa duyệt < {hold_thresh:.2%} -> Release."
        )

    return {
        "decision": decision,
        "n_errors": n_errors,
        "n_warn_images": n_warn_images,
        "n_images": n_images,
        "warn_ratio": warn_ratio,
        "reasons": reasons,
    }
