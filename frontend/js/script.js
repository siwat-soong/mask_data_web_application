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



importButton.addEventListener("click", (event) => {
    event.stopPropagation();
    uploadBox.classList.toggle("show");
});


document.addEventListener("click", (event) => {
  if (
    !uploadBox.contains(event.target) &&
    !importButton.contains(event.target)
  ) {
    uploadBox.classList.remove("show");
  }
});


browseButton.addEventListener("click", () => {
  fileInput.click();
});

fileInput.addEventListener("change", () => {
  const file = fileInput.files[0];

  if (!file) {
    return;
  }

  const extension = "." + file.name.split(".").pop().toLowerCase();

  if (extension !== ".txt" && extension !== ".csv") {
    alert("ขณะนี้รองรับการแสดงข้อความจากไฟล์ .txt และ .csv เท่านั้น");
    fileInput.value = "";
    return;
  }

  const reader = new FileReader();

  reader.onload = (event) => {
    dataInput.value = event.target.result;
    dataInput.dispatchEvent(new Event("input"));
    uploadBox.classList.remove("show");
    fileInput.value = "";
  };

  reader.onerror = () => {
    alert("ไม่สามารถอ่านไฟล์ได้");
    fileInput.value = "";
  };

  reader.readAsText(file, "UTF-8");
});

["dragenter", "dragover"].forEach((eventName) => {
  importArea.addEventListener(eventName, (event) => {
    event.preventDefault();
    importArea.classList.add("drag-over");
  });
});

["dragleave", "drop"].forEach((eventName) => {
  importArea.addEventListener(eventName, (event) => {
    event.preventDefault();
    importArea.classList.remove("drag-over");
  });
});

importArea.addEventListener("drop", (event) => {
  const file = event.dataTransfer.files[0];

  if (!file) {
    return;
  }

  const transfer = new DataTransfer();
  transfer.items.add(file);
  fileInput.files = transfer.files;
  fileInput.dispatchEvent(new Event("change"));
});

function updateClearButton() {
  const hasText = dataInput.value.trim() !== "";

  clearButton.style.display = hasText ? "flex" : "none";
  inputActions.style.display = hasText ? "none" : "flex";
}

pasteButton.addEventListener("click", async () => {
  try {
    const text = await navigator.clipboard.readText();

    dataInput.value = text;

    autoResize(dataInput);
    updateClearButton();

    pasteIcon.src = "img/clipboard-check.svg";

    pasteText.textContent = "Pasted";

    setTimeout(() => {
      pasteIcon.src = "img/clipboard.svg";
      pasteText.textContent = "Paste";
    }, 1000);
  } catch (error) {
    console.error("Clipboard error:", error);

    pasteIcon.src = "img/clipboard-x.svg";

    pasteText.textContent = "Failed";

    setTimeout(() => {
      pasteIcon.src = "img/clipboard.svg";

      pasteText.textContent = "Paste";
    }, 1000);
  }
});

function autoResize(textarea) {
  textarea.style.height = "auto";

  textarea.style.height = textarea.scrollHeight + "px";
}

dataInput.addEventListener("input", () => {
  autoResize(dataInput);
  updateClearButton();
});

clearButton.addEventListener("click", () => {
  dataInput.value = "";

  autoResize(dataInput);
  updateClearButton();

  dataInput.focus();
});

const savedText = sessionStorage.getItem("maskInputText");

if (savedText !== null) {
  dataInput.value = savedText;
  dataInput.dispatchEvent(new Event("input"));
  sessionStorage.removeItem("maskInputText");
}
