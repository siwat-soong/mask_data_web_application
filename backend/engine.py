"""
รับ `text: str` เป็นข้อความที่ต้องการตรวจและ mask; รับ `types: list[str] | None` เป็น
รายชื่อประเภทที่ต้องการตรวจ (`credit_card`, `email`, `phone`, `dob`, `address`). ถ้า
`types` เป็น None จะใช้ทุกประเภท; ถ้าระบุ list จะใช้เฉพาะประเภทใน list.

คืน dict ตามรูปแบบนี้:
- `ok`: สถานะการทำงาน
- `original_text`, `masked_text`: ข้อความก่อนและหลัง mask
- `detections`: list ของ `{id, type, original, masked, chars_masked}`; `original` และ
  `masked` มี `{start, end, text}`
- `errors`: list ของ `{type, code, message, original}`; `original` มี `{start, end, text}`
- `summary`: `{total_detections, total_chars_masked, total_errors, by_type}`; `by_type`
  มี `{count, chars_masked, errors}` ครบทั้งห้าประเภท แม้ไม่มีข้อมูลที่พบ

ตำแหน่งเป็นช่วง [start, end) ตาม index ของ string ใน Python. Response นี้ไม่มี `source`;
"""
from backend.rules import RULES

SUPPORTED_TYPES = ("credit_card", "email", "phone", "dob", "address")


def mask_text(text: str, types: list[str] | None = None) -> dict:
    if types is None:
        active_rules = RULES
    else:
        active_rules = []
        for rule in RULES:
            if rule.type in types:
                active_rules.append(rule)
    matches = []
    for rule in active_rules:
        for match in rule.pattern.finditer(text):
            matches.append((rule, match))

    matches.sort(key=lambda pair: pair[0].priority, reverse=True)
    selected_matches = []

    for rule, match in matches:
        overlap = False
        for selected_rule, selected_match in selected_matches:
            if selected_match.start() < match.end() and match.start() < selected_match.end():
                overlap = True
                break

        if not overlap:
            selected_matches.append((rule, match))

    selected_matches.sort(key=lambda pair: pair[1].start())

    masked_parts = []
    detections = []
    cursor = 0
    masked_cursor = 0
    for rule, match in selected_matches:
        start = match.start()
        end = match.end()
        original = match.group()

        unchanged = text[cursor:start]
        masked_parts.append(unchanged)
        masked_cursor += len(unchanged)

        replacement, chars_masked = rule.mask(match)
        masked_start = masked_cursor
        masked_end = masked_start + len(replacement)

        masked_parts.append(replacement)
        detection = {
            "id": len(detections),
            "type": rule.type,
            "original": {
                "start": start,
                "end": end,
                "text": original,
            },
            "masked": {
                "start": masked_start,
                "end": masked_end,
                "text": replacement,
            },
            "chars_masked": chars_masked,
        }
        detections.append(detection)

        cursor = end
        masked_cursor = masked_end

    masked_parts.append(text[cursor:])
    masked_text = "".join(masked_parts)

    errors = []
    for rule in active_rules:
        if rule.near_miss is not None:
            for near_match in rule.near_miss.finditer(text):
                overlap = False

                for detection in detections:
                    original_start = detection["original"]["start"]
                    original_end = detection["original"]["end"]

                    if original_start < near_match.end() and near_match.start() < original_end:
                        overlap = True
                        break

                if not overlap:
                    error = {
                        "type": rule.type,
                        "code": "INVALID_FORMAT",
                        "message": f"Possible {rule.type} has an invalid format.",
                        "original": {
                            "start": near_match.start(),
                            "end": near_match.end(),
                            "text": near_match.group(),
                        },
                    }
                    errors.append(error)

    summary = {
        "total_detections": len(detections),
        "total_chars_masked": 0,
        "total_errors": len(errors),
        "by_type": {},
    }

    for type_name in SUPPORTED_TYPES:
        summary["by_type"][type_name] = {
            "count": 0,
            "chars_masked": 0,
            "errors": 0,
        }

    for detection in detections:
        type_name = detection["type"]

        summary["total_chars_masked"] += detection["chars_masked"]
        summary["by_type"][type_name]["count"] += 1
        summary["by_type"][type_name]["chars_masked"] += detection["chars_masked"]

    for error in errors:
        type_name = error["type"]
        summary["by_type"][type_name]["errors"] += 1

    return {
        "ok": True,
        "original_text": text,
        "masked_text": masked_text,
        "detections": detections,
        "errors": errors,
        "summary": summary,
    }
