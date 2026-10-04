const importButton = document.getElementById("import-button");
const uploadBox = document.getElementById("upload-box");
const importArea = document.querySelector(".import-area");
const browseButton = document.getElementById("browse-button");
const fileInput = document.getElementById("file-input");
const pasteButton = document.getElementById("paste-button");
const pasteText = document.getElementById("paste-text");
const dataInput = document.getElementById("data-input");
const pasteIcon = pasteButton.querySelector(".paste-icon");
const clearButton = document.getElementById("clear-button");
const inputActions = document.querySelector(".input-actions");
const maskButton = document.querySelector(".mask-button");
const maskedOutput = document.getElementById("masked-output");
const maskSummary = document.getElementById("mask-summary");
const copyMaskedButton = document.getElementById("copy-masked-button");
const copyButton = document.getElementById("copy-button");
const downloadMaskedButton = document.getElementById("download-masked-button");
const downloadMenu = document.getElementById("download-menu");
const downloadGroup = document.querySelector(".download-group");
const downloadTxtButton = document.getElementById("download-txt");
const downloadCsvButton = document.getElementById("download-csv");
const errorTooltip = document.getElementById("error-tooltip");

let currentMaskedText = "";
let downloadedFileName = "masked-data.txt";
let selectedFile = null;
let fillingFilePreview = false;

["dragover", "drop"].forEach((eventName) => {
  window.addEventListener(eventName, (event) => {
    event.preventDefault();
  });
});

function autoResize(textarea) {
  const maxHeight = 450;

  textarea.style.height = "auto";

  const newHeight = Math.min(textarea.scrollHeight, maxHeight);
  textarea.style.height = `${newHeight}px`;

  textarea.style.overflowY =
    textarea.scrollHeight > maxHeight ? "auto" : "hidden";
}

function updateClearButton() {
  const hasText = dataInput.value.trim() !== "";
  clearButton.style.display = hasText ? "flex" : "none";
  inputActions.style.display = hasText ? "none" : "flex";
}

function setMaskButtonLoading(loading) {
  maskButton.disabled = loading;
  maskButton.textContent = loading ? "กำลังประมวลผล..." : "Mask";
}

function renderMaskedResult(result) {
  dataInput.value = result.original_text;
  autoResize(dataInput);
  updateClearButton();
  maskedOutput.replaceChildren();

  const labels = {
    dob: "DOB",
    email: "email",
    address: "Address",
    credit_card: "credit card number",
    phone: "telephone number",
  };

  const errorLabels = {
    email: "Invalid email format",
    phone: "Invalid telephone number format",
    credit_card: "Invalid credit card format",
    dob: "Invalid date format",
    address: "Invalid address format",
  };

  const highlights = [
    ...(result.detections || []).map((item) => ({
      start: item.masked.start,
      end: item.masked.end,
      className: "masked-detection",
    })),
    ...(result.errors || []).map((item) => ({
      start: item.original.start,
      end: item.original.end,
      className: "masked-error",
      tooltip: errorLabels[item.type] || item.message,
    })),
  ].sort((a, b) => a.start - b.start);

  let cursor = 0;
  for (const item of highlights) {
    if (item.start < cursor) continue;
    maskedOutput.append(
      document.createTextNode(result.masked_text.slice(cursor, item.start)),
    );
    const span = document.createElement("span");
    span.className = item.className;
    span.textContent = result.masked_text.slice(item.start, item.end);

    if (item.className === "masked-error") {
      span.dataset.errorMessage = item.tooltip;
    }

    maskedOutput.append(span);
    cursor = item.end;
  }
  maskedOutput.append(
    document.createTextNode(result.masked_text.slice(cursor)),
  );

  maskSummary.replaceChildren();

  for (const [type, label] of Object.entries(labels)) {
    const count = result.summary.by_type?.[type]?.count ?? 0;
    if (count === 0) continue;

    const item = document.createElement("p");
    item.textContent = `${count} ${label}`;
    maskSummary.append(item);
  }

  const totalErrors = result.summary.total_errors ?? 0;

  if (totalErrors > 0) {
    const errorItem = document.createElement("p");
    errorItem.className = "summary-error";
    errorItem.textContent = `${totalErrors} error${totalErrors > 1 ? "s" : ""} found`;
    maskSummary.append(errorItem);
  }

  if (!maskSummary.childElementCount) {
    maskSummary.textContent = "ไม่พบข้อมูลส่วนบุคคล";
  }

  currentMaskedText = result.masked_text;

  if (result.source?.filename) {
    const originalName = result.source.filename.replace(/\.[^/.]+$/, "");
    downloadedFileName = `${originalName}-masked.txt`;
  }

  copyMaskedButton.hidden = false;
  downloadMaskedButton.hidden = false;
}

async function submitMask() {
  const text = dataInput.value.trim();
  if (!text && !selectedFile) {
    alert("กรุณากรอกข้อความหรือเลือกไฟล์ก่อนกด Mask");
    return;
  }

  setMaskButtonLoading(true);
  try {
    const result = await requestMask({ text, file: selectedFile });
    saveMaskResult(result);
    selectedFile = null;
    fileInput.value = "";
    renderMaskedResult(result);
  } catch (error) {
    alert(error.message);
  } finally {
    setMaskButtonLoading(false);
  }
}

importButton.addEventListener("click", (event) => {
  event.stopPropagation();
  uploadBox.classList.toggle("show");
});

document.addEventListener("click", (event) => {
  if (!uploadBox.contains(event.target) && !importButton.contains(event.target))
    uploadBox.classList.remove("show");
});

browseButton.addEventListener("click", () => fileInput.click());

fileInput.addEventListener("change", () => {
  const file = fileInput.files[0];
  const reader = new FileReader();

  if (!file) return;
  const extension = `.${file.name.split(".").pop().toLowerCase()}`;
  if (![".txt", ".csv", ".png"].includes(extension)) {
    alert("ขณะนี้รองรับไฟล์ .txt, .csv และ .png เท่านั้น");
    fileInput.value = "";
    return;
  }
  selectedFile = file;
  dataInput.value = "";
  dataInput.placeholder = `เลือกไฟล์ "${file.name}" แล้ว กด Mask เพื่อดำเนินการ`;
  autoResize(dataInput);
  updateClearButton();
  uploadBox.classList.remove("show");

  reader.onload = (event) => {
    fillingFilePreview = true;
    dataInput.value = event.target.result;
    dataInput.placeholder =
      "To mask data for PDPA, enter, paste or import file here and press “Mask”.";
    dataInput.dispatchEvent(new Event("input"));
    fillingFilePreview = false;
  };

  reader.onerror = () => {
    selectedFile = null;
    fileInput.value = "";
    alert("ไม่สามารถอ่านไฟล์เพื่อแสดงตัวอย่างได้");
  };

  if (extension === ".png") {
    dataInput.value = "";
    dataInput.placeholder = `เลือกไฟล์ภาพ "${file.name}" แล้ว กด Mask เพื่ออ่านข้อความจากรูป`;

    dataInput.classList.add("png-selected");

    autoResize(dataInput);
    updateClearButton();
    return;
  }

  reader.readAsText(file, "UTF-8");
});

["dragenter", "dragover"].forEach((eventName) =>
  importArea.addEventListener(eventName, (event) => {
    event.preventDefault();
    importArea.classList.add("drag-over");
  }),
);

["dragleave", "drop"].forEach((eventName) =>
  importArea.addEventListener(eventName, (event) => {
    event.preventDefault();
    importArea.classList.remove("drag-over");
  }),
);

importArea.addEventListener("drop", (event) => {
  const file = event.dataTransfer.files[0];
  if (!file) return;
  const transfer = new DataTransfer();
  transfer.items.add(file);
  fileInput.files = transfer.files;
  fileInput.dispatchEvent(new Event("change"));
});

pasteButton.addEventListener("click", async () => {
  try {
    dataInput.value = await navigator.clipboard.readText();
    dataInput.dispatchEvent(new Event("input"));
    pasteIcon.src = "img/clipboard-check.svg";
    pasteText.textContent = "Pasted";
  } catch {
    pasteIcon.src = "img/clipboard-x.svg";
    pasteText.textContent = "Failed";
  }
  setTimeout(() => {
    pasteIcon.src = "img/clipboard.svg";
    pasteText.textContent = "Paste";
  }, 1000);
});

dataInput.addEventListener("input", () => {
  dataInput.classList.remove("png-selected");
  if (dataInput.value.trim() && !fillingFilePreview) {
    selectedFile = null;
    dataInput.placeholder =
      "To mask data for PDPA, enter, paste or import file here and press “Mask”.";
  }
  autoResize(dataInput);
  updateClearButton();
});

clearButton.addEventListener("click", () => {
  dataInput.classList.remove("png-selected");
  dataInput.value = "";
  selectedFile = null;
  fileInput.value = "";
  dataInput.placeholder =
    "To mask data for PDPA, enter, paste or import file here and press “Mask”.";
  dataInput.dispatchEvent(new Event("input"));
  dataInput.focus();
});

maskButton.addEventListener("click", submitMask);

const savedInputText = sessionStorage.getItem("maskInputText");

if (savedInputText !== null) {
  dataInput.value = savedInputText;
  dataInput.dispatchEvent(new Event("input"));
  sessionStorage.removeItem("maskInputText");
}

const savedResult = loadMaskResult();
if (savedResult) renderMaskedResult(savedResult);

copyMaskedButton.addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText(currentMaskedText);

    copyButton.className = "bi bi-check-lg";
    setTimeout(() => {
      copyButton.className = "bi bi-copy";
    }, 1200);
  } catch {
    alert("ไม่สามารถคัดลอกข้อความได้");
  }
});

downloadMaskedButton.addEventListener("click", (event) => {
  event.stopPropagation();

  downloadMenu.hidden = !downloadMenu.hidden;
});

document.addEventListener("click", (event) => {
  if (!downloadGroup.contains(event.target)) {
    downloadMenu.hidden = true;
  }
});

function downloadMaskedFile(extension, mimeType) {
  if (!currentMaskedText) return;

  const file = new Blob([currentMaskedText], {
    type: `${mimeType};charset=utf-8`,
  });

  const url = URL.createObjectURL(file);
  const link = document.createElement("a");

  link.href = url;
  link.download = downloadedFileName.replace(".txt", `.${extension}`);

  document.body.append(link);
  link.click();
  link.remove();

  URL.revokeObjectURL(url);
  downloadMenu.hidden = true;
}

downloadTxtButton.addEventListener("click", () => {
  downloadMaskedFile("txt", "text/plain");
});

downloadCsvButton.addEventListener("click", () => {
  downloadMaskedFile("csv", "text/csv");
});

maskedOutput.addEventListener("mouseover", (event) => {
  const errorElement = event.target.closest(".masked-error");
  if (!errorElement) return;

  errorTooltip.textContent = errorElement.dataset.errorMessage;
  errorTooltip.hidden = false;
});

maskedOutput.addEventListener("mousemove", (event) => {
  if (errorTooltip.hidden) return;

  errorTooltip.style.left = `${event.clientX}px`;
  errorTooltip.style.top = `${event.clientY - 16}px`;
});

maskedOutput.addEventListener("mouseout", (event) => {
  if (event.target.closest(".masked-error")) {
    errorTooltip.hidden = true;
  }
});
