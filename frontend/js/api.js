const MASK_API_URL = "http://127.0.0.1:8000";

async function requestMask({ text, file }) {
  const url = file ? `${MASK_API_URL}/api/mask/file` : `${MASK_API_URL}/api/mask`;
  const options = { method: "POST" };

  if (file) {
    const formData = new FormData();
    formData.append("file", file);
    options.body = formData;
  } else {
    options.headers = { "Content-Type": "application/json" };
    options.body = JSON.stringify({ text });
  }

  try {
    const response = await fetch(url, options);
    const payload = await response.json();
    if (!response.ok || !payload.ok) {
      throw new Error(payload?.error?.message || "ไม่สามารถประมวลผลข้อมูลได้");
    }
    return payload;
  } catch (error) {
    if (error instanceof SyntaxError) throw new Error("ได้รับข้อมูลตอบกลับจากระบบไม่ถูกต้อง");
    if (error instanceof TypeError) throw new Error("ไม่สามารถเชื่อมต่อระบบได้ กรุณาตรวจสอบว่า backend ทำงานอยู่");
    throw error;
  }
}

function saveMaskResult(result) {
  sessionStorage.setItem("maskResult", JSON.stringify(result));
}

function loadMaskResult() {
  const saved = sessionStorage.getItem("maskResult");
  if (!saved) return null;
  try {
    return JSON.parse(saved);
  } catch {
    sessionStorage.removeItem("maskResult");
    return null;
  }
}
