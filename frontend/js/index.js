const txtArea = document.querySelector(".text-input");
const hug = document.querySelector(".hug");
const clearIcon = document.querySelector(".trash-icon");
const pasteButton = document.querySelector(".bi-clipboard");
const importButton = document.querySelector(".bi-box-arrow-in-down");
const importButtons = document.querySelectorAll(".import-bat");
const upload = document.querySelector(".upload");
const supportText = document.querySelector(".support-txt");
const fileInput = document.querySelector("#file-input");
const browse = upload.querySelector("a");
const maskButton = document.querySelector(".control-btn > button");
let selectedFile = null;
let fillingFilePreview = false;

function updateInputState() {
  const hasText = txtArea.value.trim() !== "";
  hug.classList.toggle("hidden", hasText);
  clearIcon.classList.toggle("hidden", !hasText);
  if (hasText && !fillingFilePreview) selectedFile = null;
}

function showUploadPanel(button, accept = ".csv,.txt") {
  const rect = button.getBoundingClientRect();
  upload.style.left = `${rect.left + rect.width / 2}px`;
  upload.style.top = `${rect.bottom}px`;
  fileInput.accept = accept;
  supportText.textContent = `Supports: ${accept.split(",").map((format) => format.slice(1)).join(", ")}`;
  upload.classList.remove("hidden");
}

function setMaskButtonLoading(loading) {
  maskButton.disabled = loading;
  maskButton.textContent = loading ? "กำลังประมวลผล..." : "Mask";
}

importButton.addEventListener("click", (event) => {
  event.stopPropagation();
  showUploadPanel(importButton);
});

importButtons.forEach((button) => button.addEventListener("click", (event) => {
  event.stopPropagation();
  showUploadPanel(button, button.classList.contains("import-csv") ? ".csv" : ".txt");
}));

document.addEventListener("click", (event) => {
  if (!upload.contains(event.target)) upload.classList.add("hidden");
});

browse.addEventListener("click", (event) => {
  event.preventDefault();
  fileInput.click();
});

fileInput.addEventListener("change", () => {
  const file = fileInput.files[0];
  const reader = new FileReader();
  if (!file) return;
  const extension = `.${file.name.split(".").pop().toLowerCase()}`;
  const allowedExtensions = fileInput.accept.split(",").map((item) => item.trim());
  if (!allowedExtensions.includes(extension)) {
    alert(`รองรับเฉพาะ: ${allowedExtensions.join(", ")}`);
    fileInput.value = "";
    return;
  }

  selectedFile = file;
  txtArea.value = "";
  txtArea.placeholder = `เลือกไฟล์ "${file.name}" แล้ว กด Mask เพื่อดำเนินการ`;
  updateInputState();
  upload.classList.add("hidden");

  reader.onload = (event) => {
    fillingFilePreview = true;
    txtArea.value = event.target.result;
    txtArea.placeholder = "To mask data for PDPA, enter, paste or import file here and press “Mask”.";
    txtArea.dispatchEvent(new Event("input"));
    fillingFilePreview = false;
  };

  reader.onerror = () => {
    selectedFile = null;
    fileInput.value = "";
    alert("ไม่สามารถอ่านไฟล์เพื่อแสดงตัวอย่างได้");
  };

  reader.readAsText(file, "UTF-8");
});

txtArea.addEventListener("input", () => {
  if (txtArea.value.trim()) txtArea.placeholder = "To mask data for PDPA, enter, paste or import file here and press “Mask”.";
  updateInputState();
});

pasteButton.addEventListener("click", async () => {
  try {
    txtArea.value = await navigator.clipboard.readText();
    txtArea.dispatchEvent(new Event("input"));
  } catch {
    alert("ไม่สามารถอ่านข้อมูลจากคลิปบอร์ดได้");
  }
});

clearIcon.addEventListener("click", () => {
  txtArea.value = "";
  selectedFile = null;
  fileInput.value = "";
  txtArea.placeholder = "To mask data for PDPA, enter, paste or import file here and press “Mask”.";
  txtArea.dispatchEvent(new Event("input"));
  txtArea.focus();
});

maskButton.addEventListener("click", async () => {
  const text = txtArea.value.trim();
  if (!text && !selectedFile) {
    alert("กรุณากรอกข้อความหรือเลือกไฟล์ก่อนกด Mask");
    return;
  }

  setMaskButtonLoading(true);
  try {
    const result = await requestMask({ text, file: selectedFile });
    saveMaskResult(result);
    window.location.href = "render.html";
  } catch (error) {
    alert(error.message);
  } finally {
    setMaskButtonLoading(false);
  }
});

["dragenter", "dragover", "dragleave", "drop"].forEach((eventName) => {
  upload.addEventListener(eventName, (event) => {
    event.preventDefault();
    event.stopPropagation();
  });
});

["dragenter", "dragover"].forEach((eventName) => upload.addEventListener(eventName, () => upload.classList.add("drag-over")));
["dragleave", "drop"].forEach((eventName) => upload.addEventListener(eventName, () => upload.classList.remove("drag-over")));

upload.addEventListener("drop", (event) => {
  const file = event.dataTransfer.files[0];
  if (!file) return;
  const transfer = new DataTransfer();
  transfer.items.add(file);
  fileInput.files = transfer.files;
  fileInput.dispatchEvent(new Event("change"));
});
