"""Engine ของ Role B: ใช้ rules จาก Role C แล้วคืนผลตามที่ Role A ใช้.

ข้อตกลงที่ต้องตรงกับทีม:
- C ส่ง RULES มา โดยแต่ละ rule มี type, pattern, mask, near_miss, priority
- A เรียก mask_text(text, types=None); ผลลัพธ์ไม่มี source เพราะ A เติมเอง
- ตำแหน่งใช้ช่วง [start, end) และ detection มีตำแหน่งทั้งข้อความเดิมกับหลัง mask
"""
from backend.rules import RULES
# from rules import RULES

SUPPORTED_TYPES = ("credit_card", "email", "phone", "dob", "address")


def mask_text(text: str, types: list[str] | None = None) -> dict:
    """ฟังก์ชันหลักที่ Role A เรียก.

    รับ text และ types (ไม่ใส่ types หมายถึงใช้ทุกประเภท) แล้วคืน dict ที่มี:
    ok, original_text, masked_text, detections, errors, summary

    detection มี id, type, original/masked {start, end, text}, chars_masked
    error มี type, code, message และ original {start, end, text}
    summary มี total_detections, total_chars_masked, total_errors และ by_type
    ที่มี count, chars_masked, errors ครบทุกประเภท
    """

    # ใช้ RULES จาก C; ถ้า types เป็น None ให้ใช้ทั้งหมด
    if types is None:
        active_rules = RULES
    else:
        active_rules = []
        for rule in RULES:
            if rule.type in types:
                active_rules.append(rule)
    # print([rule.type for rule in active_rules])

    # หา matches และเลือกกรณีทับกันโดยใช้ priority
    matches = []
    for rule in active_rules:
        for match in rule.pattern.finditer(text):
            matches.append((rule, match))
            # print(f"{rule.type} {match.group()} {match.start()} {match.end()}")

    matches.sort(key=lambda pair: pair[0].priority, reverse=True) # เรียง priority มากไปน้อบ
    selected_matches = []

    for rule, match in matches:
        # เช็กตรงนี้ว่า match ทับกับตัวที่เลือกไว้แล้วหรือไม่
        overlap = False
        for selected_rule, selected_match in selected_matches:
            if selected_match.start() < match.end() and match.start() < selected_match.end():
                overlap = True
                break

        if not overlap:
            selected_matches.append((rule, match))
            # print(f"{rule.type} {match.group()} {match.start()} {match.end()}")

    selected_matches.sort(key=lambda pair: pair[1].start())

    # สร้าง masked_text และ detections พร้อมตำแหน่งทั้งสองชุด
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
        # print(detection)
        detections.append(detection)

        cursor = end
        masked_cursor = masked_end

    masked_parts.append(text[cursor:])
    masked_text = "".join(masked_parts)
    # print(masked_text)

    # หา near-miss errors และสร้าง summary
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

    # สร้าง summary
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

# text = """
#             Customer 001
#             Email: somchai@example.com
#             Backup email: pimchanok.s@example.org
#             Phone: 000-111-2222
#             Alternate phone: 000-333-4444
#             Card: 1111-2222-3333-4444
#             Backup card: 9999-8888-7777-6666
#             DOB: 25/12/2540
#             DOB: 03/04/2538
#             Address: 123/45 ถนนสุขุมวิท 17 แขวงทดสอบ
#             Address: 678 ถนนตัวอย่าง เขตทดสอบ

#             Near-miss examples
#             Phone: 0812345678
#             Card: 1234567890123456
#             Email: user@example
#             DOB: 31/13/2540
#             Address: ถนนสุขุมวิท
#             Customer: Somchai
#             Credit Card: 1234-5678-9012-3456
#             Email: somchai.d@company.com
#             Phone: 093-245-7894
#             DOB:25/12/2549
#             Address: 689 ซอยลาดกระบัง 19 ถนนลาดกระบัง แขวงลาดกระบัง เขตลาดกระบัง กรุงเทพฯ

#             Customer: Ananda
#             Credit Card: 9876-5432-1098-7654
#             Email: ananda.s@kmitl.ac.th
#             Phone: 081-234-5678
#             DOB:03/01/2548
#             Address: 42 ถนนฉลองกรุง แขวงลำปลาทิว เขตลาดกระบัง กรุงเทพฯ

#             Customer: Mali
#             Credit Card: 1111-2222-3333-4444
#             Email: mali_123@example.co.th
#             Phone: 099-888-7766
#             DOB:17/08/2550
#             Address: 12/45 ซอยพหลโยธิน 34 ถนนพหลโยธิน แขวงเสนานิคม เขตจตุจักร กรุงเทพฯ

#             Customer: Test User
#             Credit Card: 5555-6666-7777-8888
#             Email: test.user@mail.example.com
#             Phone: 062-111-2233
#             DOB:09/04/2547
#             Address: 7 ถนนสุขุมวิท แขวงคลองตันเหนือ เขตวัฒนา กรุงเทพฯ
#         """

# print(mask_text(text))
