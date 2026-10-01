"""โครงงาน Role B: engine สำหรับประมวลผลข้อความตาม rules ของ Role C.

ไฟล์นี้ยังไม่มี logic ที่ใช้งานจริง ฟังก์ชันจะ raise NotImplementedError
จนกว่าจะเติม TODO แต่ละส่วน จึงไม่คืนผลสำเร็จที่ยังไม่ได้ประมวลผล

ข้อตกลงที่ต้องยืนยันกับทีม:
- ช่วงตำแหน่งใช้ [start, end) และต้องตกลงหน่วยตำแหน่งกับ frontend
- priority ค่าสูงหรือต่ำชนะ และกรณีเท่ากันเลือกอย่างไร
- ความหมายของ types=[] และการรับชื่อประเภทที่ไม่รู้จัก
- code/message ของ near-miss และวิธีตัด errors ที่ทับกับ valid matches

Rule ของ C ต้องมี type, pattern, mask, near_miss และ priority ตามแผน
ไม่ประกาศ Rule ซ้ำในไฟล์นี้ เพื่อให้ทีมใช้ interface เดียวกัน
"""


SUPPORTED_TYPES = ("credit_card", "email", "phone", "dob", "address")


def select_rules(rules: list, types: list[str] | None = None) -> list:
    """เลือก rules ที่จะรัน; types=None หมายถึงใช้ครบทุกประเภท.

    TODO: กรองด้วย rule.type และใช้ข้อตกลงของทีมสำหรับ []/ชื่อที่ไม่รู้จัก
    ไม่แก้ไขรายการ rules หรือ types ที่ผู้เรียกส่งมา
    """
    raise NotImplementedError("TODO: เลือก rules ตาม types")


def find_matches(text: str, rules: list) -> list[dict]:
    """รวบรวม candidate matches จาก rule.pattern.finditer(text).

    Candidate แต่ละรายการ:
        {"rule": rule, "match": match, "start": int, "end": int}

    เก็บ re.Match ไว้ เพราะต้องส่งให้ rule.mask(match) ภายหลัง
    TODO: รันทุก rule และรวบรวมผล โดยยังไม่ mask หรือตัดผลทับกัน
    """
    raise NotImplementedError("TODO: ค้นหา candidate matches")


def ranges_overlap(a_start: int, a_end: int, b_start: int, b_end: int) -> bool:
    """ตรวจช่วง [start, end) สองช่วง; ช่วงที่ติดกันไม่ถือว่าทับกัน.

    TODO: ใช้เงื่อนไข a_start < b_end and b_start < a_end
    """
    raise NotImplementedError("TODO: ตรวจช่วงที่ทับกัน")


def resolve_overlaps(candidates: list[dict]) -> list[dict]:
    """เลือก candidates ที่ไม่ทับกันตาม priority และเกณฑ์เสมอของทีม.

    TODO: จัดลำดับผู้ชนะแล้วใช้ ranges_overlap ตรวจเทียบผลที่เลือกไว้
    คืนรายการที่เรียงตาม start เพื่อให้ประกอบข้อความจากซ้ายไปขวาได้
    ห้ามนับ candidate ที่ถูกตัดออกเป็น detection
    """
    raise NotImplementedError("TODO: เลือก matches เมื่อช่วงทับกัน")


def build_masked_text(text: str, matches: list[dict]) -> tuple[str, list[dict]]:
    """คืน (masked_text, detections) จาก matches ที่เลือกและเรียงแล้ว.

    TODO สำหรับแต่ละ match:
    1. ต่อข้อความต้นฉบับจาก cursor ถึง match.start()
    2. เรียก replacement, chars_masked = rule.mask(match)
    3. เก็บตำแหน่งเริ่มในผลลัพธ์จากความยาวที่ประกอบไปแล้ว
    4. ต่อ replacement และสร้าง detection ตาม schema ด้านล่าง
    5. เลื่อน cursor ของต้นฉบับไป match.end()
    เมื่อครบแล้วต่อข้อความท้ายสุด; กรณีไม่มี match ต้องคืนข้อความเดิม

    Detection:
        {
            "id": int, "type": str,
            "original": {"start": int, "end": int, "text": str},
            "masked": {"start": int, "end": int, "text": str},
            "chars_masked": int,
        }

    จำนวน chars_masked มาจาก C ไม่ใช่ความยาว replacement
    ตรวจว่าตัดข้อความด้วยตำแหน่งแต่ละชุดแล้วได้ text ใน detection จริง
    """
    raise NotImplementedError("TODO: ประกอบข้อความและเก็บตำแหน่งสองชุด")


def find_errors(text: str, rules: list, valid_matches: list[dict]) -> list[dict]:
    """หา near-miss ของ rules ที่เปิดใช้ และกรองรายการซ้ำตามข้อตกลง.

    TODO: ข้าม rule ที่ near_miss=None; รัน finditer กับข้อความต้นฉบับ
    ตรวจ valid_matches เพื่อไม่รายงานข้อมูลถูกต้องเป็น error ซ้ำ
    ตกลงการตัด errors ซ้ำกัน รวมถึงแหล่ง code/message กับ C ก่อนเขียน
    errors ไม่เปลี่ยนข้อความและไม่เพิ่มจำนวน detections

    Error:
        {
            "type": str, "code": str, "message": str,
            "original": {"start": int, "end": int, "text": str},
        }

    ต้องยืนยันว่า valid_matches ใช้ candidates ทั้งหมดหรือเฉพาะผู้ชนะ
    """
    raise NotImplementedError("TODO: รวบรวมและกรอง near-miss errors")


def build_summary(detections: list[dict], errors: list[dict]) -> dict:
    """รวมตัวเลขจากผลที่ใช้จริง และสร้าง by_type ครบ SUPPORTED_TYPES.

    TODO: เริ่มทุกประเภทด้วย count=0, chars_masked=0, errors=0
    จากนั้นรวม detections และ errors แยกตาม type

    คืน:
        {
            "total_detections": int,
            "total_chars_masked": int,
            "total_errors": int,
            "by_type": {
                type_name: {"count": int, "chars_masked": int, "errors": int}
            },
        }
    """
    raise NotImplementedError("TODO: สรุปจำนวนรวมและแยกประเภท")


def mask_text(text: str, types: list[str] | None = None) -> dict:
    """จุดเข้า engine ที่ A เรียก; คืน response dict โดยยังไม่มี source.

    TODO: เมื่อ C สร้าง rules/__init__.py แล้ว import RULES จาก .rules
    ตกลงชนิดของ RULES ให้ตรงกับ select_rules

    ลำดับเรียก:
        selected_rules = select_rules(RULES, types)
        candidates = find_matches(text, selected_rules)
        matches = resolve_overlaps(candidates)
        masked_text, detections = build_masked_text(text, matches)
        errors = find_errors(text, selected_rules, valid_matches=...)
        summary = build_summary(detections, errors)

    คืน:
        {
            "ok": True,
            "original_text": text,
            "masked_text": masked_text,
            "detections": detections,
            "errors": errors,
            "summary": summary,
        }

    A รับผิดชอบ source, ตรวจ request/ไฟล์ และ HTTP response
    """
    raise NotImplementedError("TODO: เชื่อมขั้นตอนของ engine")
