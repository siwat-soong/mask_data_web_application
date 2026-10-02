"""Hard-coded stand-in for backend.engine until Role B's engine is merged.

It ignores the input and always returns the same example, so the frontend can
build the results page against the real response shape.
"""
from backend.schemas import SUPPORTED_TYPES

_PIECES = [
    ("Customer: card ", None),
    ("1234-5678-9012-3456", ("credit_card", "XXXX-XXXX-XXXX-3456", 12)),
    (" email ", None),
    ("somchai.d@company.com", ("email", "s*******d@company.com", 7)),
    (" phone ", None),
    ("093-245-7894", ("phone", "XXX-XXX-7894", 6)),
    (" bad phone 0932457894", None),
]
_BAD_PHONE = "0932457894"


def mask_text(text: str, types: list[str] | None = None) -> dict:
    original_text = ""
    masked_text = ""
    detections = []
    for piece, mask in _PIECES:
        if mask is None:
            original_text += piece
            masked_text += piece
            continue
        type_name, replacement, chars_masked = mask
        detections.append({
            "id": len(detections),
            "type": type_name,
            "original": {"start": len(original_text), "end": len(original_text) + len(piece), "text": piece},
            "masked": {"start": len(masked_text), "end": len(masked_text) + len(replacement), "text": replacement},
            "chars_masked": chars_masked,
        })
        original_text += piece
        masked_text += replacement

    bad_start = original_text.index(_BAD_PHONE)
    errors = [{
        "type": "phone",
        "code": "INVALID_FORMAT",
        "message": "Possible phone has an invalid format.",
        "original": {"start": bad_start, "end": bad_start + len(_BAD_PHONE), "text": _BAD_PHONE},
    }]

    by_type = {t: {"count": 0, "chars_masked": 0, "errors": 0} for t in SUPPORTED_TYPES}
    for d in detections:
        by_type[d["type"]]["count"] += 1
        by_type[d["type"]]["chars_masked"] += d["chars_masked"]
    for e in errors:
        by_type[e["type"]]["errors"] += 1

    return {
        "ok": True,
        "original_text": original_text,
        "masked_text": masked_text,
        "detections": detections,
        "errors": errors,
        "summary": {
            "total_detections": len(detections),
            "total_chars_masked": sum(d["chars_masked"] for d in detections),
            "total_errors": len(errors),
            "by_type": by_type,
        },
    }
