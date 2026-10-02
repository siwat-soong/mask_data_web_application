# MaskData API

## รัน backend

```
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload
```

- Base URL ตอน dev: `http://127.0.0.1:8000`
- ลองยิง API ได้ที่ `http://127.0.0.1:8000/docs`
- CORS: ค่าเริ่มต้นอนุญาตทุก origin (`*`) สำหรับ dev; ตอน deploy ให้ตั้ง `CORS_ORIGINS="https://frontend.example.com"` (คั่นหลายค่าด้วย comma)

> ตอนนี้ถ้ายังไม่มี `backend/engine.py` (ของ Role B) API จะตอบ **ตัวอย่างแบบ hard-code** เสมอ ไม่ว่าส่งอะไรไป
> โครงสร้าง JSON เหมือนของจริงทุกอย่าง ใช้ทำหน้าแสดงผลได้เลย

## Endpoints

| Method | Path | Body | ใช้กับ |
| --- | --- | --- | --- |
| POST | `/api/mask` | JSON `{"text": "...", "types": [...]}` | ข้อความที่พิมพ์/วาง |
| POST | `/api/mask/file` | `multipart/form-data`: `file` + `types` (ไม่บังคับ) | ไฟล์ที่อัปโหลด |
| GET | `/api/health` | – | เช็คว่า server ทำงาน |

`types` ไม่ใส่ = ตรวจครบทั้ง 5 ประเภท: `credit_card`, `email`, `phone`, `dob`, `address`
ส่ง `[]` = ไม่ตรวจอะไรเลย (ได้ข้อความเดิมกลับมา)

ไฟล์: รับ `.txt` และ `.csv` ขนาดไม่เกิน 2 MB, encoding UTF-8 (มี BOM ได้) หรือ Windows Thai (cp874)
บรรทัดใหม่ทุกแบบถูกแปลงเป็น `\n` ก่อนตรวจ ดังนั้นตำแหน่ง start/end อ้างอิงกับ `original_text` ที่ส่งกลับไป (ไม่ใช่ไฟล์ดิบ)
`.png` ยังไม่รองรับ (ตอบ 415)

### ตัวอย่างการเรียกจาก JS

```js
// ข้อความ
const res = await fetch("http://127.0.0.1:8000/api/mask", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ text, types: ["credit_card", "phone"] }),
});
const data = await res.json();
if (!data.ok) alert(data.error.message);

// ไฟล์
const form = new FormData();
form.append("file", fileInput.files[0]);
form.append("types", "credit_card");   // append ซ้ำได้หลายครั้ง หรือส่ง "credit_card,phone"
const res2 = await fetch("http://127.0.0.1:8000/api/mask/file", { method: "POST", body: form });
```

## Response สำเร็จ (HTTP 200)

```json
{
  "ok": true,
  "source": { "kind": "file", "filename": "bank_log.csv", "file_type": "csv", "ocr": false },
  "original_text": "card 1234-5678-9012-3456 bad 0932457894",
  "masked_text":   "card XXXX-XXXX-XXXX-3456 bad 0932457894",
  "detections": [
    {
      "id": 0,
      "type": "credit_card",
      "original": { "start": 5, "end": 24, "text": "1234-5678-9012-3456" },
      "masked":   { "start": 5, "end": 24, "text": "XXXX-XXXX-XXXX-3456" },
      "chars_masked": 12
    }
  ],
  "errors": [
    { "type": "phone", "code": "INVALID_FORMAT", "message": "Possible phone has an invalid format.",
      "original": { "start": 29, "end": 39, "text": "0932457894" } }
  ],
  "summary": {
    "total_detections": 1, "total_chars_masked": 12, "total_errors": 1,
    "by_type": {
      "credit_card": { "count": 1, "chars_masked": 12, "errors": 0 },
      "email":       { "count": 0, "chars_masked": 0,  "errors": 0 },
      "phone":       { "count": 0, "chars_masked": 0,  "errors": 1 },
      "dob":         { "count": 0, "chars_masked": 0,  "errors": 0 },
      "address":     { "count": 0, "chars_masked": 0,  "errors": 0 }
    }
  }
}
```

- `source.kind` เป็น `"text"` สำหรับ `/api/mask` (`filename`, `file_type` เป็น `null`)
- `start`/`end` เป็นช่วง `[start, end)` ตาม index ของตัวอักษร ใช้ `str.slice(start, end)` ใน JS ได้ตรงๆ
  - `original.*` ชี้ใน `original_text`, `masked.*` ชี้ใน `masked_text`
  - การ mask ทุกแบบให้ความยาวเท่าเดิม (เช่น `093-245-7894` → `XXX-XXX-7894`) ดังนั้น `original_text` กับ `masked_text` ยาวเท่ากัน และตำแหน่งตรงกันทุกตัวอักษร
- `errors` = ข้อมูลที่ดูเหมือนข้อมูลส่วนบุคคลแต่รูปแบบผิด **ไม่ถูก mask** แค่แจ้งตำแหน่ง
  - ใช้ `errors[].original.start` / `end` ไฮไลท์ได้ทั้งบน `original_text` และ `masked_text` (เพราะตำแหน่งตรงกัน)
  - `errors` ไม่ทับกับ `detections` เลย ไฮไลท์สองชุดพร้อมกันได้โดยไม่ซ้อนกัน

```js
// ไฮไลท์ errors (ใช้ได้กับ original_text หรือ masked_text)
function highlight(text, errors) {
  let html = "", cursor = 0;
  for (const e of [...errors].sort((a, b) => a.original.start - b.original.start)) {
    const { start, end } = e.original;
    if (start < cursor) continue;  // กันกรณี error สองอันทับกัน
    html += escapeHtml(text.slice(cursor, start))
         + `<mark title="${escapeHtml(e.message)}">${escapeHtml(text.slice(start, end))}</mark>`;
    cursor = end;
  }
  return html + escapeHtml(text.slice(cursor));
}
```
- `by_type` มีครบทั้ง 5 key เสมอ แม้จะเป็น 0

## Response ผิดพลาด

```json
{ "ok": false, "error": { "code": "EMPTY_TEXT", "message": "Text is empty." } }
```

| HTTP | `code` | เมื่อไหร่ |
| --- | --- | --- |
| 400 | `EMPTY_TEXT` | ข้อความหรือไฟล์ว่าง (หรือมีแต่ช่องว่าง) |
| 400 | `INVALID_TYPES` | `types` มีชื่อที่ไม่รู้จัก |
| 400 | `INVALID_REQUEST` | body ผิดรูปแบบ, ไม่มี `text`, ไม่มี `file` |
| 400 | `DECODE_FAILED` | ไฟล์อ่านเป็นข้อความไม่ได้ |
| 413 | `TEXT_TOO_LARGE` | ข้อความยาวเกิน 2,097,152 ตัวอักษร |
| 413 | `FILE_TOO_LARGE` | ไฟล์ใหญ่เกิน 2 MB |
| 415 | `UNSUPPORTED_FILE_TYPE` | ไม่ใช่ `.txt` / `.csv` |

แสดง `error.message` ให้ผู้ใช้ได้เลย หรือใช้ `error.code` เลือกข้อความภาษาไทยเอง
