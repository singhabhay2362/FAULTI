// ---- Global Django variables loaded from annotate.html ----
const imageUrl = window.imageUrl;
const imageName = window.imageName;
const idx = window.idx;
const total = window.total;
const saveUrl = window.saveUrl;
const annotateBase = window.annotateBase;
const existingBoxes = window.existingBoxes || []; // existing saved YOLO boxes

// ---- Canvas setup ----
const canvas = document.getElementById("canvas");
const ctx = canvas.getContext("2d");
const img = new Image();
img.src = imageUrl;

// ---- Data structures ----
let boxes = [];  // Each box: {x1, y1, x2, y2, cls}
let drawing = false;
let startX = 0, startY = 0;
let selectedIndex = -1;


// ---- Load existing YOLO boxes and convert to pixels ----
function loadExistingBoxes() {
    if (!existingBoxes || existingBoxes.length === 0) return;

    const W = canvas.width;
    const H = canvas.height;

    existingBoxes.forEach(b => {
        const x_center = b.x_center * W;
        const y_center = b.y_center * H;
        const width = b.width * W;
        const height = b.height * H;

        const x1 = x_center - width / 2;
        const y1 = y_center - height / 2;
        const x2 = x_center + width / 2;
        const y2 = y_center + height / 2;

        boxes.push({
            x1, y1, x2, y2,
            cls: b.cls
        });
    });

    refreshBoxesList();
}


// ---- Load image and resize to fit window ----
img.onload = function () {
    const maxHeight = window.innerHeight - 40;
    const scale = Math.min(maxHeight / img.height, 1);

    canvas.width = img.width * scale;
    canvas.height = img.height * scale;

    loadExistingBoxes();
    draw();
};


// ---- Draw everything ----
function draw() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(img, 0, 0, canvas.width, canvas.height);

    ctx.lineWidth = 2;
    boxes.forEach((b, i) => {
        const w = b.x2 - b.x1;
        const h = b.y2 - b.y1;

        ctx.strokeStyle = (i === selectedIndex) ? "red" : "lime";
        ctx.strokeRect(b.x1, b.y1, w, h);
    });
}


// ---- Mouse Events ----
canvas.addEventListener("mousedown", (e) => {
    const rect = canvas.getBoundingClientRect();
    startX = e.clientX - rect.left;
    startY = e.clientY - rect.top;
    drawing = true;
});

canvas.addEventListener("mousemove", (e) => {
    if (!drawing) return;

    const rect = canvas.getBoundingClientRect();
    const currentX = e.clientX - rect.left;
    const currentY = e.clientY - rect.top;

    draw();
    ctx.strokeStyle = "yellow";
    ctx.lineWidth = 2;
    ctx.strokeRect(startX, startY, currentX - startX, currentY - startY);
});

canvas.addEventListener("mouseup", (e) => {
    if (!drawing) return;
    drawing = false;

    const rect = canvas.getBoundingClientRect();
    const endX = e.clientX - rect.left;
    const endY = e.clientY - rect.top;

    const cls = parseInt(document.getElementById("classSelect").value);

    const x1 = Math.min(startX, endX);
    const y1 = Math.min(startY, endY);
    const x2 = Math.max(startX, endX);
    const y2 = Math.max(startY, endY);

    if (Math.abs(x2 - x1) < 5 || Math.abs(y2 - y1) < 5) {
        draw();
        return;
    }

    boxes.push({ x1, y1, x2, y2, cls });
    selectedIndex = boxes.length - 1;

    refreshBoxesList();
    draw();
});


// ---- Box list UI ----
function refreshBoxesList() {
    const container = document.getElementById("boxesList");
    container.innerHTML = "";

    boxes.forEach((box, i) => {
        const div = document.createElement("div");
        div.className = "box-item" + (i === selectedIndex ? " selected" : "");
        div.textContent = `#${i} - Class ${box.cls} (${Math.round(box.x1)}, ${Math.round(box.y1)})`;

        div.onclick = () => {
            selectedIndex = i;
            refreshBoxesList();
            draw();
        };

        container.appendChild(div);
    });
}


// ---- Save Annotations ----
document.getElementById("saveBtn").onclick = function () {

    const payloadBoxes = boxes.map(b => {
        return {
            cls: b.cls,
            x_center: +(((b.x1 + b.x2) / 2 / canvas.width).toFixed(6)),
            y_center: +(((b.y1 + b.y2) / 2 / canvas.height).toFixed(6)),
            width: +((Math.abs(b.x2 - b.x1) / canvas.width).toFixed(6)),
            height: +((Math.abs(b.y2 - b.y1) / canvas.height).toFixed(6)),
        };
    });

    fetch(saveUrl, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCookie("csrftoken")
        },
        body: JSON.stringify({
            image_name: imageName,
            boxes: payloadBoxes
        })
    }).then(r => r.json()).then(data => {
        alert("Saved!");
    });
};


// ---- Delete Selected Box ----
document.getElementById("deleteBtn").onclick = function () {
    if (selectedIndex < 0) return;

    boxes.splice(selectedIndex, 1);
    selectedIndex = -1;

    refreshBoxesList();
    draw();
};


// ---- Navigation ----
document.getElementById("nextBtn").onclick = () => {
    const next = Math.min(idx + 1, total - 1);
    window.location = `${annotateBase}?idx=${next}`;
};

document.getElementById("prevBtn").onclick = () => {
    const prev = Math.max(idx - 1, 0);
    window.location = `${annotateBase}?idx=${prev}`;
};



// -----------------------------
// 🚀 Add new class dynamically
// -----------------------------
document.getElementById("addClassBtn").onclick = function () {
    const newClass = document.getElementById("newClassInput").value.trim();
    const statusMsg = document.getElementById("statusMsg");

    if (!newClass) {
        statusMsg.innerText = "⚠ Enter class name";
        return;
    }

    fetch("/add-class/", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCookie("csrftoken")
        },
        body: JSON.stringify({ class_name: newClass })
    })
        .then(res => res.json())
        .then(data => {
            if (data.status === "exists") {
                statusMsg.innerText = "⚠ Class already exists!";
            } else if (data.status === "added") {
                statusMsg.innerText = "✔ Class added!";
                updateClassDropdown(data.classes);
            }
        });
};


// ---- Refresh Dropdown dynamically ----
function updateClassDropdown(classes) {
    const select = document.getElementById("classSelect");
    select.innerHTML = "";

    classes.forEach((c, i) => {
        const option = document.createElement("option");
        option.value = i;
        option.textContent = c;
        select.appendChild(option);
    });

    select.value = classes.length - 1; // auto select newly added class
}



// ---- CSRF Token Helper ----
function getCookie(name) {
    let value = null;
    const cookies = document.cookie?.split(";") || [];
    cookies.forEach(cookie => {
        cookie = cookie.trim();
        if (cookie.startsWith(name + "=")) {
            value = decodeURIComponent(cookie.substring(name.length + 1));
        }
    });
    return value;
}

// -----------------------------
// CLOSE BUTTON FEATURE
// -----------------------------
document.getElementById("closeBtn").onclick = () => {
    if (confirm("Are you sure? Unsaved annotations will be lost.")) {
        window.location.href = "/"; // Change if your URL is different
    }
};
