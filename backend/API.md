# MaskData API

## รัน backend

```
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload
```

- อ่านไฟล์ `.png` ได้ต้องติดตั้งโปรแกรม Tesseract พร้อมภาษาไทยด้วย (แค่ `pip install` ไม่พอ)
  - Windows: ตัวติดตั้งจาก https://github.com/UB-Mannheim/tesseract/wiki ตอนติดตั้งให้ติ๊ก Thai ใน "Additional language data"
  - Linux (Debian/Ubuntu): `apt install tesseract-ocr tesseract-ocr-tha`
  - ถ้า `tesseract` ไม่อยู่ใน PATH ให้ตั้ง `TESSERACT_CMD` เป็น path เต็มของโปรแกรม
  - ถ้าไม่ได้ติดตั้ง ไฟล์ `.txt` / `.csv` ยังใช้ได้ปกติ แต่ `.png` จะตอบ 503
- Base URL ตอน dev: `http://127.0.0.1:8000`
- ลองยิง API ได้ที่ `http://127.0.0.1:8000/docs`
- CORS: ค่าเริ่มต้นอนุญาตทุก origin (`*`) สำหรับ dev; ตอน deploy ให้ตั้ง `CORS_ORIGINS="https://frontend.example.com"` (คั่นหลายค่าด้วย comma)

## Endpoints

| Method | Path | Body | ใช้กับ |
| --- | --- | --- | --- |
| POST | `/api/mask` | JSON `{"text": "...", "types": [...]}` | ข้อความที่พิมพ์/วาง |
| POST | `/api/mask/file` | `multipart/form-data`: `file` + `types` (ไม่บังคับ) | ไฟล์ที่อัปโหลด |
| GET | `/api/health` | – | เช็คว่า server ทำงาน |

`types` ไม่ใส่ = ตรวจครบทั้ง 5 ประเภท: `credit_card`, `email`, `phone`, `dob`, `address`
ส่ง `[]` = ไม่ตรวจอะไรเลย (ได้ข้อความเดิมกลับมา)

ไฟล์: รับ `.txt`, `.csv` และ `.png` ขนาดไม่เกิน 2 MB
- `.txt` / `.csv`: encoding UTF-8 (มี BOM ได้) หรือ Windows Thai (cp874) บรรทัดใหม่ทุกแบบถูกแปลงเป็น `\n` ก่อนตรวจ
- `.png`: อ่านข้อความจากรูปด้วย OCR (Tesseract, ภาษาไทย + อังกฤษ) แล้วตรวจเหมือนข้อความปกติ response จะมี `source.ocr = true`
  - รูปต้องไม่เกิน 25 ล้าน pixel (ประมาณ 5000 × 5000) และอ่านได้ภายใน 30 วินาที
  - OCR อ่านผิดได้ (เช่น `0` กับ `O`) ข้อมูลบางส่วนอาจไม่ถูกตรวจเจอ
  - หลัง OCR ระบบแก้ข้อผิดพลาดที่เจอบ่อยให้ก่อน: ขีดยาว (`–`, `—`) เป็น `-`, ช่องว่างรอบขีดระหว่างตัวเลข (`093 - 245`) และช่องว่างก่อน `:` (`DOB :`)
  - browser อ่านข้อความจากรูปเองไม่ได้ frontend ต้องเอา `original_text` จาก response ไปแสดงเป็นข้อความต้นฉบับ

ตำแหน่ง start/end ทั้งหมดอ้างอิงกับ `original_text` ที่ส่งกลับไป (ไม่ใช่ไฟล์ดิบหรือรูป)

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
  - ข้อยกเว้น: emoji และอักขระพิเศษบางตัว Python นับเป็น 1 ตัว แต่ JS นับเป็น 2 ตัว ถ้าข้อความมี emoji ตำแหน่งหลังจากนั้นใน JS จะเลื่อนไป 1 ต่อ emoji 1 ตัว (ภาษาไทยและภาษาอังกฤษปกติไม่มีปัญหา) ถ้าต้องการให้ตรงเสมอ ให้ใช้ `Array.from(text).slice(start, end).join("")` แทน `text.slice(start, end)`
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
| 400 | `INVALID_IMAGE` | ไฟล์ `.png` ไม่ใช่รูป PNG จริง หรือไฟล์เสีย |
| 400 | `NO_TEXT_FOUND` | OCR ไม่เจอข้อความในรูป |
| 413 | `TEXT_TOO_LARGE` | ข้อความยาวเกิน 2,097,152 ตัวอักษร |
| 413 | `FILE_TOO_LARGE` | ไฟล์ใหญ่เกิน 2 MB |
| 413 | `IMAGE_TOO_LARGE` | รูปเกิน 25 ล้าน pixel |
| 415 | `UNSUPPORTED_FILE_TYPE` | ไม่ใช่ `.txt` / `.csv` / `.png` |
| 500 | `OCR_FAILED` | Tesseract อ่านรูปไม่สำเร็จ |
| 503 | `OCR_UNAVAILABLE` | server ไม่ได้ติดตั้ง Tesseract หรือข้อมูลภาษาไทยของ Tesseract |
| 504 | `OCR_TIMEOUT` | อ่านรูปนานเกิน 30 วินาที |

แสดง `error.message` ให้ผู้ใช้ได้เลย หรือใช้ `error.code` เลือกข้อความภาษาไทยเอง 
