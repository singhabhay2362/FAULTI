document.addEventListener("DOMContentLoaded", () => {
    // ---------- IMAGE PREVIEW MODAL ----------
    const imgModal = document.getElementById("imgModal");
    const fullImage = document.getElementById("fullImage");
    const closeBtns = document.querySelectorAll("#imgModal .close");

    document.querySelectorAll(".zoomable").forEach(img => {
        img.addEventListener("click", () => {
            imgModal.style.display = "block";
            fullImage.src = img.src;
        });
    });

    closeBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            imgModal.style.display = "none";
        });
    });

    imgModal.addEventListener("click", e => {
        if (e.target === imgModal) imgModal.style.display = "none";
    });

    // ---------- YES / NO BUTTON HANDLING ----------
    document.querySelectorAll(".card").forEach(card => {
        const yesBtn = card.querySelector(".yes-btn");
        const noBtn = card.querySelector(".no-btn");
        const faultId = card.dataset.id;

        // ✅ YES button click → send request → move + open LabelImg
        yesBtn.addEventListener("click", async () => {
            yesBtn.disabled = true;
            noBtn.disabled = true;
            yesBtn.innerHTML = "⏳ Processing...";

            try {
                const res = await fetch(`/api/faults/${faultId}/confirm/`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": getCSRFToken(),
                    },
                    body: JSON.stringify({ action: "yes" }),
                });

                if (!res.ok) throw new Error(`HTTP ${res.status}`);
                const data = await res.json();
                console.log("✅ Fault confirmed:", data);

                // ✅ Smooth fade out all deleted cards (including duplicates)
                if (data.deleted_ids || data.copied_ids) {
                    const allIds = data.deleted_ids || data.copied_ids;
                    allIds.forEach(id => {
                        const cardToRemove = document.querySelector(`.card[data-id="${id}"]`);
                        if (cardToRemove) {
                            cardToRemove.style.transition = "opacity 0.5s ease";
                            cardToRemove.style.opacity = "0";
                            setTimeout(() => cardToRemove.remove(), 500);
                        }
                    });
                } else {
                    // fallback
                    card.style.transition = "opacity 0.5s ease";
                    card.style.opacity = "0";
                    setTimeout(() => card.remove(), 500);
                }


                // ⚙️ Automatically open LabelImg (no popup)
                if (data.labelImgStarted) {
                    console.log("🚀 LabelImg launched successfully.");
                } else {
                    console.warn("⚠️ LabelImg did not start automatically.");
                }

            } catch (err) {
                console.error("❌ Error confirming fault:", err);
            } finally {
                yesBtn.innerHTML = "YES";
                yesBtn.disabled = false;
                noBtn.disabled = false;
            }
        });

        // ❌ NO button click → copy + blank label + delete duplicates
        noBtn.addEventListener("click", async () => {
            noBtn.disabled = true;
            yesBtn.disabled = true;
            noBtn.innerHTML = "⏳ Processing...";

            try {
                const res = await fetch(`/api/faults/${faultId}/confirm/`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": getCSRFToken(),
                    },
                    body: JSON.stringify({ action: "no" }),
                });

                if (!res.ok) throw new Error(`HTTP ${res.status}`);
                const data = await res.json();
                console.log("🚫 Fault rejected:", data);

                // ✅ Instantly fade-out all duplicate cards (cross-page)
                if (data.deleted_ids && Array.isArray(data.deleted_ids)) {
                    data.deleted_ids.forEach(id => {
                        const cardToRemove = document.querySelector(`.card[data-id="${id}"]`);
                        if (cardToRemove) {
                            fadeOutCard(cardToRemove);
                        }
                    });
                } else {
                    fadeOutCard(card);
                }

                showToast(data.message || "🚫 Faults removed successfully!", "red");

            } catch (err) {
                console.error("❌ Error rejecting fault:", err);
                showToast("Error rejecting fault!", "red");
            } finally {
                noBtn.innerHTML = "NO";
                yesBtn.disabled = false;
                noBtn.disabled = false;
            }
        });
    });

    // ---------- 🧩 Fade Out Helper ----------
    function fadeOutCard(card) {
        card.style.transition = "opacity 0.5s ease";
        card.style.opacity = "0";
        setTimeout(() => card.remove(), 500);
    }

    // ---------- Helper to get CSRF token ----------
    function getCSRFToken() {
        let cookieValue = null;
        const cookies = document.cookie ? document.cookie.split(";") : [];
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.startsWith("csrftoken=")) {
                cookieValue = cookie.substring("csrftoken=".length);
                break;
            }
        }
        return cookieValue;
    }

    // ---------- 💬 TOAST MESSAGE ----------
    function showToast(message, color = "black") {
        const toast = document.createElement("div");
        toast.textContent = message;
        toast.style.position = "fixed";
        toast.style.bottom = "20px";
        toast.style.right = "20px";
        toast.style.background = color === "red" ? "#e74c3c" : "#27ae60";
        toast.style.color = "white";
        toast.style.padding = "10px 15px";
        toast.style.borderRadius = "8px";
        toast.style.boxShadow = "0 4px 12px rgba(0,0,0,0.2)";
        toast.style.fontSize = "14px";
        toast.style.zIndex = "9999";
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 3000);
    }

    // ---------- 🔍 SEARCH & STATUS FILTER ----------
    const searchBox = document.getElementById("searchBox");
    const statusFilter = document.getElementById("statusFilter");
    const faultGrid = document.getElementById("faultGrid");
    const cards = Array.from(faultGrid.getElementsByClassName("card"));

    function applyFilters() {
        const query = searchBox.value.toLowerCase().trim();
        const selectedStatus = statusFilter.value.toLowerCase();

        cards.forEach(card => {
            const faultId = card.dataset.id.toLowerCase();
            const time = card.dataset.time.toLowerCase();
            const status = card.dataset.status.toLowerCase();

            const matchesSearch =
                faultId.includes(query) ||
                time.includes(query);

            const matchesStatus =
                selectedStatus === "" || status === selectedStatus;

            card.style.display = (matchesSearch && matchesStatus) ? "block" : "none";
        });
    }

    searchBox.addEventListener("input", applyFilters);
    statusFilter.addEventListener("change", applyFilters);
});
