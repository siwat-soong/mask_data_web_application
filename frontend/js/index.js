const txt_area = document.querySelector("textarea");

const hug = document.querySelector(".hug");
const clr = document.querySelector(".trash-icon");

const paste_btn = document.querySelector(".bi-clipboard");
const import_btn = document.querySelector(".bi-box-arrow-in-down");

const import_buttons = document.querySelectorAll(".import-bat");

const upload = document.querySelector(".upload");
const support_text = document.querySelector(".support-txt");

const file_input = document.querySelector("#file-input");
const browse = upload.querySelector("a");


// ========================================
// Upload Panel
// ========================================

function upload_panel(button, accept = ".csv,.txt,.png") {

    const rect = button.getBoundingClientRect();

    // Position panel under clicked button
    upload.style.left = `${rect.left + rect.width / 2}px`;
    upload.style.top = `${rect.bottom}px`;

    // Set accepted file types
    file_input.accept = accept;

    // Update support text
    const formats = accept
        .split(",")
        .map(format => format.replace(".", ""));

    support_text.textContent = `Supports: ${formats.join(", ")}`;

    // Show panel
    upload.classList.remove("hidden");
}


// ========================================
// Main Import Icon
// ========================================

import_btn.addEventListener("click", (event) => {

    // Prevent document click from immediately hiding panel
    event.stopPropagation();

    // Allow CSV, TXT and PNG
    upload_panel(import_btn, ".csv,.txt,.png");

});


// ========================================
// Individual Import Buttons
// ========================================

import_buttons.forEach(button => {

    button.addEventListener("click", (event) => {

        // Prevent document click from hiding panel
        event.stopPropagation();

        let accept;

        if (button.classList.contains("import-csv")) {

            accept = ".csv";

        }
        else if (button.classList.contains("import-txt")) {

            accept = ".txt";

        }
        else if (button.classList.contains("import-img")) {

            accept = ".png";

        }

        upload_panel(button, accept);

    });

});


// ========================================
// Click Outside Upload Panel
// ========================================

document.addEventListener("click", (event) => {

    // If click is inside upload panel, do nothing
    if (upload.contains(event.target)) {
        return;
    }

    // Otherwise hide panel
    upload.classList.add("hidden");

});


// ========================================
// Browse
// ========================================

browse.addEventListener("click", (event) => {

    event.preventDefault();

    file_input.click();

});


// ========================================
// File Selected & Validation
// ========================================

file_input.addEventListener("change", () => {
    const file = file_input.files[0];

    if (!file) {
        return;
    }

    // 1. ดึงนามสกุลไฟล์ที่เลือก
    const fileExtension = "." + file.name.split(".").pop().toLowerCase();

    // 2. ดึงประเภทไฟล์ที่ยอมรับจาก accept
    const allowedExtensions = file_input.accept
        ? file_input.accept.split(",").map(ext => ext.trim().toLowerCase())
        : [];

    // 3. ตรวจสอบประเภทไฟล์
    if (allowedExtensions.length > 0 && !allowedExtensions.includes(fileExtension)) {

        // ❌ แจ้งเตือนไฟล์ผิดประเภท
        alert(`❌ นามสกุลไฟล์ไม่ถูกต้อง!\nรองรับเฉพาะ: ${allowedExtensions.join(", ")}`);

        // ล้างค่าไฟล์ที่ไม่ถูกต้องออก
        file_input.value = "";
        return;
    }

    // ✅ แจ้งเตือนอัปโหลดสำเร็จ
    alert(`✅ อัปโหลดไฟล์ "${file.name}" เรียบร้อยแล้ว!`);

    console.log("Selected file:", file.name);
    console.log("File type:", file.type);

    // ซ่อน upload panel เมื่อเลือกไฟล์สำเร็จ
    upload.classList.add("hidden");

    // Process file here later
});


// ========================================
// Textarea
// ========================================

txt_area.addEventListener("input", () => {

    if (txt_area.value.trim() !== "") {

        hug.classList.add("hidden");

        import_btn.classList.add("hidden");

        clr.classList.remove("hidden");

    }
    else {

        clr.classList.add("hidden");

        hug.classList.remove("hidden");

        import_btn.classList.remove("hidden");

    }

});


// ========================================
// Paste
// ========================================

paste_btn.addEventListener("click", async () => {

    const text = await navigator.clipboard.readText();

    txt_area.value = text;

    // Trigger textarea UI update
    txt_area.dispatchEvent(new Event("input"));

});


// ========================================
// Clear
// ========================================

clr.addEventListener("click", () => {

    txt_area.value = "";

    // Trigger textarea UI update
    txt_area.dispatchEvent(new Event("input"));

});

// ========================================
// Drag and Drop
// ========================================

// 1. ป้องกันไม่ให้ Browser เปิดไฟล์ขึ้นมาเองเมื่อมี Event เกี่ยวกับการลากวาง
["dragenter", "dragover", "dragleave", "drop"].forEach(eventName => {
    upload.addEventListener(eventName, (event) => {
        event.preventDefault();
        event.stopPropagation();
    });
});

// 2. ใส่/เอา Class ออกเมื่อลากไฟล์มาอยู่เหนือกล่อง (สำหรับทำ UI ให้รู้ว่ากำลังลากใส่)
["dragenter", "dragover"].forEach(eventName => {
    upload.addEventListener(eventName, () => {
        upload.classList.add("drag-over");
    });
});

["dragleave", "drop"].forEach(eventName => {
    upload.addEventListener(eventName, () => {
        upload.classList.remove("drag-over");
    });
});

// 3. เมื่อปล่อยไฟล์ (Drop)
upload.addEventListener("drop", (event) => {
    const files = event.dataTransfer.files;

    if (files.length === 0) return;

    // อัปเดตไฟล์ที่ได้เข้าไปใน 
    const dataTransfer = new DataTransfer();
    dataTransfer.items.add(files[0]);
    file_input.files = dataTransfer.files;

    // สั่งยิง Event 'change' เพื่อให้โค้ด File Selected เดิมทำงานต่อ
    file_input.dispatchEvent(new Event("change"));

    upload.classList.add("hidden");
});