const importButton = document.getElementById("import-button");
const uploadBox = document.getElementById("upload-box");

const browseButton = document.getElementById("browse-button");
const fileInput = document.getElementById("file-input");

const pasteButton = document.getElementById("paste-button");
const pasteText = document.getElementById("paste-text");
const dataInput = document.getElementById("data-input");
const pasteIcon = pasteButton.querySelector(".paste-icon");

const clearButton = document.getElementById("clear-button");


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

function updateClearButton() {
  if (dataInput.value.trim() !== "") {
    clearButton.style.display = "flex";
  } else {
    clearButton.style.display = "none";
  }
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
