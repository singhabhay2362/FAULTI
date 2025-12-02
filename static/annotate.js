// ---- Global Django variables loaded from annotate.html ----
const imageUrl = window.imageUrl;
const imageName = window.imageName;
const idx = window.idx;
const total = window.total;
const saveUrl = window.saveUrl;
const annotateBase = window.annotateBase;
const existingBoxes = window.existingBoxes || [];

// ---- Canvas ----
const canvas = document.getElementById("canvas");
const ctx = canvas.getContext("2d");
const img = new Image();
img.src = imageUrl;

canvas.style.cursor = "crosshair";

// ---- Data ----
let boxes = [];
let drawing = false;
let startX = 0, startY = 0;
let currentX = 0, currentY = 0;
let selectedIndex = -1;

// ---- Mouse Tracking for Crosshair ----
let mousePos = { x: null, y: null };

// ---- Drag + Resize state ----
let dragging = false;
let dragOffsetX = 0, dragOffsetY = 0;

let resizing = false;
let activeHandle = null;
const HANDLE_SIZE = 8;

// ---- Zoom & Pan ----
let zoom = 1;
let offsetX = 0;
let offsetY = 0;
let isPanning = false;
let panStartX = 0;
let panStartY = 0;
let panStartOffsetX = 0;
let panStartOffsetY = 0;


// ---- Accurate scaled mouse coordinates ----
function getMousePos(e) {
    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;

    const rawX = (e.clientX - rect.left) * scaleX;
    const rawY = (e.clientY - rect.top) * scaleY;

    return {
        x: (rawX - offsetX) / zoom,
        y: (rawY - offsetY) / zoom
    };
}


// ---- Load YOLO Boxes ----
function loadExistingBoxes() {
    if (!existingBoxes.length) return;

    const W = canvas.width, H = canvas.height;

    existingBoxes.forEach(b => {
        const x_center = b.x_center * W;
        const y_center = b.y_center * H;
        const width = b.width * W;
        const height = b.height * H;

        boxes.push({
            x1: x_center - width / 2,
            y1: y_center - height / 2,
            x2: x_center + width / 2,
            y2: y_center + height / 2,
            cls: b.cls
        });
    });

    refreshList();
}


// ---- Image loaded ----
img.onload = () => {
    canvas.width = img.width;
    canvas.height = img.height;
    loadExistingBoxes();
    draw();
};


// ---- Draw everything ----
function draw() {

    // Reset transform before clear
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Apply zoom + pan
    ctx.setTransform(zoom, 0, 0, zoom, offsetX, offsetY);

    ctx.drawImage(img, 0, 0, canvas.width, canvas.height);

    boxes.forEach((b, i) => {
        const w = b.x2 - b.x1;
        const h = b.y2 - b.y1;

        ctx.lineWidth = 2 / zoom;
        ctx.strokeStyle = i === selectedIndex ? "red" : "#00ff88";
        ctx.fillStyle = "rgba(0,255,136,0.2)";

        ctx.strokeRect(b.x1, b.y1, w, h);
        ctx.fillRect(b.x1, b.y1, w, h);

        if (i === selectedIndex) drawHandles(b);
    });

    // ---- CROSSHAIR ----
    if (mousePos.x !== null && mousePos.y !== null) {
        ctx.save();
        ctx.lineWidth = 1 / zoom;
        ctx.strokeStyle = "rgba(255,255,0,0.6)";
        ctx.setLineDash([12 / zoom, 8 / zoom]);

        // vertical line
        ctx.beginPath();
        ctx.moveTo(mousePos.x, 0);
        ctx.lineTo(mousePos.x, canvas.height);
        ctx.stroke();

        // horizontal line
        ctx.beginPath();
        ctx.moveTo(0, mousePos.y);
        ctx.lineTo(canvas.width, mousePos.y);
        ctx.stroke();

        ctx.restore();
    }
}


// ---- Handles ----
function drawHandles(b) {
    drawHandle(b.x1, b.y1);
    drawHandle(b.x2, b.y1);
    drawHandle(b.x1, b.y2);
    drawHandle(b.x2, b.y2);
}

function drawHandle(x, y) {
    const size = HANDLE_SIZE / zoom;
    ctx.fillStyle = "#ffeb3b";
    ctx.fillRect(x - size, y - size, size * 2, size * 2);
}


// ---- Mouse Move ----
canvas.addEventListener("mousemove", e => {
    mousePos = getMousePos(e);

    // Panning
    if (isPanning) {
        const rect = canvas.getBoundingClientRect();
        const scaleX = canvas.width / rect.width;
        const scaleY = canvas.height / rect.height;
        const rawX = (e.clientX - rect.left) * scaleX;
        const rawY = (e.clientY - rect.top) * scaleY;

        offsetX = panStartOffsetX + (rawX - panStartX);
        offsetY = panStartOffsetY + (rawY - panStartY);
        draw();
        return;
    }

    // Drag box
    if (dragging && selectedIndex >= 0) {
        const b = boxes[selectedIndex];
        const w = b.x2 - b.x1;
        const h = b.y2 - b.y1;
        b.x1 = mousePos.x - dragOffsetX;
        b.y1 = mousePos.y - dragOffsetY;
        b.x2 = b.x1 + w;
        b.y2 = b.y1 + h;
        draw();
        return;
    }

    // Resize box
    if (resizing && selectedIndex >= 0) {
        const b = boxes[selectedIndex];

        if (activeHandle.includes('t')) b.y1 = mousePos.y;
        if (activeHandle.includes('b')) b.y2 = mousePos.y;
        if (activeHandle.includes('l')) b.x1 = mousePos.x;
        if (activeHandle.includes('r')) b.x2 = mousePos.x;

        if (b.x1 > b.x2) [b.x1, b.x2] = [b.x2, b.x1];
        if (b.y1 > b.y2) [b.y1, b.y2] = [b.y2, b.y1];

        draw();
        return;
    }

    if (drawing) {
        currentX = mousePos.x;
        currentY = mousePos.y;
        draw();
        drawTemp();
        return;
    }

    draw(); // redraw crosshair while idle
});


// ---- Mouse Down ----
canvas.addEventListener("mousedown", e => {

    const pos = getMousePos(e);

    // Right click → pan
    if (e.button === 2) {
        isPanning = true;
        const rect = canvas.getBoundingClientRect();
        const scaleX = canvas.width / rect.width;
        const scaleY = canvas.height / rect.height;
        panStartX = (e.clientX - rect.left) * scaleX;
        panStartY = (e.clientY - rect.top) * scaleY;
        panStartOffsetX = offsetX;
        panStartOffsetY = offsetY;
        return;
    }

    // Resize detection
    if (selectedIndex >= 0) {
        const h = getHandleUnderMouse(pos.x, pos.y, boxes[selectedIndex]);
        if (h) {
            resizing = true;
            activeHandle = h;
            return;
        }
    }

    // Drag box
    for (let i = boxes.length - 1; i >= 0; i--) {
        const b = boxes[i];
        if (pos.x > b.x1 && pos.x < b.x2 && pos.y > b.y1 && pos.y < b.y2) {
            selectedIndex = i;
            dragging = true;
            dragOffsetX = pos.x - b.x1;
            dragOffsetY = pos.y - b.y1;
            refreshList();
            draw();
            return;
        }
    }

    // Start drawing new box
    startX = currentX = pos.x;
    startY = currentY = pos.y;
    drawing = true;
});


// ---- Mouse Up ----
canvas.addEventListener("mouseup", () => {
    if (isPanning) return isPanning = false;
    if (dragging) return dragging = false;
    if (resizing) { resizing = false; activeHandle = null; draw(); return; }

    if (!drawing) return;
    drawing = false;

    const clsVal = document.getElementById("classSelect").value;
    if (!clsVal) return alert("⚠ Select a class first!");

    const x1 = Math.min(startX, currentX);
    const y1 = Math.min(startY, currentY);
    const x2 = Math.max(startX, currentX);
    const y2 = Math.max(startY, currentY);

    if ((x2 - x1) < 10 || (y2 - y1) < 10) return;

    boxes.push({ x1, y1, x2, y2, cls: parseInt(clsVal) });
    selectedIndex = boxes.length - 1;
    refreshList();
    draw();
});


// ---- Disable right-click ----
canvas.addEventListener("contextmenu", e => e.preventDefault());


// ---- Zoom Centered at Mouse ----
canvas.addEventListener("wheel", e => {
    e.preventDefault();

    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;
    const rawX = (e.clientX - rect.left) * scaleX;
    const rawY = (e.clientY - rect.top) * scaleY;

    const imgX = (rawX - offsetX) / zoom;
    const imgY = (rawY - offsetY) / zoom;

    const zoomFactor = e.deltaY < 0 ? 1.15 : 0.85;
    const newZoom = Math.min(Math.max(zoom * zoomFactor, 0.2), 15);

    offsetX = rawX - imgX * newZoom;
    offsetY = rawY - imgY * newZoom;
    zoom = newZoom;

    draw();
}, { passive: false });


// ---- Box List UI ----
function refreshList() {
    const list = document.getElementById("boxesList");
    list.innerHTML = "";

    boxes.forEach((b, i) => {
        const div = document.createElement("div");
        div.className = "box-item" + (i === selectedIndex ? " selected" : "");
        div.textContent = `#${i} Class:${b.cls}`;
        div.onclick = () => { selectedIndex = i; refreshList(); draw(); };
        list.appendChild(div);
    });
}


// ---- Save ----
document.getElementById("saveBtn").onclick = () => {
    const p = boxes.map(b => ({
        cls: b.cls,
        x_center: +(((b.x1 + b.x2) / 2 / canvas.width).toFixed(6)),
        y_center: +(((b.y1 + b.y2) / 2 / canvas.height).toFixed(6)),
        width: +(((b.x2 - b.x1) / canvas.width).toFixed(6)),
        height: +(((b.y2 - b.y1) / canvas.height).toFixed(6))
    }));

    fetch(saveUrl, {
        method: "POST",
        headers: {"Content-Type": "application/json", "X-CSRFToken": getCookie("csrftoken")},
        body: JSON.stringify({ image_name: imageName, boxes: p })
    }).then(r => r.json()).then(() => alert("✔ Saved"));
};


// ---- Delete ----
document.getElementById("deleteBtn").onclick = () => {
    if (selectedIndex < 0) return;
    boxes.splice(selectedIndex, 1);
    selectedIndex = -1;
    refreshList();
    draw();
};


// ---- Navigation ----
document.getElementById("nextBtn").onclick = () =>
    window.location = `${annotateBase}?idx=${Math.min(idx + 1, total - 1)}`;

document.getElementById("prevBtn").onclick = () =>
    window.location = `${annotateBase}?idx=${Math.max(idx - 1, 0)}`;


// ---- Class Add ----
document.getElementById("addClassBtn").onclick = function () {
    const newClass = document.getElementById("newClassInput").value.trim();
    const statusMsg = document.getElementById("statusMsg");
    const select = document.getElementById("classSelect");

    if (!newClass) return statusMsg.innerText = "⚠ Enter class name";

    fetch("/add-class/", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCookie("csrftoken")
        },
        body: JSON.stringify({ class_name: newClass })
    }).then(res => res.json())
    .then(data => {
        if (data.status === "exists") return statusMsg.innerText = "⚠ Class already exists!";

        statusMsg.innerText = "✔ Class added!";
        const option = document.createElement("option");
        option.value = data.classes.length - 1;
        option.textContent = newClass;
        select.appendChild(option);
        select.value = option.value;
        document.getElementById("newClassInput").value = "";
    });
};


// ---- CSRF ----
function getCookie(name){
    return document.cookie.split("; ").find(c=>c.startsWith(name+"="))?.split("=")[1]||null;
}


// ---- Close ----
document.getElementById("closeBtn").onclick = () => {
    if(confirm("Exit? Unsaved work will be lost.")) window.location="/";
};
