document.addEventListener("DOMContentLoaded", () => {

    // ---------- IMAGE PREVIEW MODAL ----------
    const imgModal = document.getElementById("imgModal");
    const fullImage = document.getElementById("fullImage");
    document.querySelectorAll(".zoomable").forEach(img => {
        img.addEventListener("click", () => {
            imgModal.style.display = "block";
            fullImage.src = img.src;
        });
    });
    imgModal.querySelector(".close").addEventListener("click", () => imgModal.style.display = "none");
    imgModal.addEventListener("click", e => { if (e.target === imgModal) imgModal.style.display = "none"; });


    // ---------- YES / NO BUTTON ----------
    document.querySelectorAll(".card").forEach(card => {
        const yesBtn = card.querySelector(".yes-btn");
        const noBtn = card.querySelector(".no-btn");
        const faultId = card.dataset.id;

        yesBtn.addEventListener("click", async () => {
            handleAction(yesBtn, noBtn, card, faultId, "yes");
        });

        noBtn.addEventListener("click", async () => {
            handleAction(noBtn, yesBtn, card, faultId, "no");
        });
    });


    // ---------- MAIN ACTION FUNCTION ----------
    async function handleAction(activeBtn, otherBtn, card, faultId, type) {

        activeBtn.disabled = true;
        otherBtn.disabled = true;

        try {
            const res = await fetch(`/api/faults/${faultId}/confirm/`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": getCSRFToken(),
                },
                body: JSON.stringify({ action: type }),
            });

            const data = await res.json();
            console.log("⚙️ Backend:", data);

            const ids = data.deleted_ids || data.copied_ids || [faultId];
            const count = ids.length;

            // 🟢 FIRST POPUP right after response (BEFORE LabelImg opens)
            if (type === "yes") {
                alert(`✔️ ${count} images sent for annotation!`);
            } else {
                alert(`🚫 ${count} images sent for training!`);
            }

            // Remove cards from UI
            ids.forEach(id => {
                const targetCard = document.querySelector(`.card[data-id="${id}"]`);
                if (targetCard) fadeOutCard(targetCard);
            });

        } catch (e) {
            alert("⚠️ Something went wrong!");
        }

        activeBtn.disabled = false;
        otherBtn.disabled = false;
    }


    // ---------- Fade card ----------
    function fadeOutCard(card) {
        card.style.transition = "opacity 0.6s ease";
        card.style.opacity = "0";
        setTimeout(() => card.remove(), 600);
    }


    // ---------- CSRF ----------
    function getCSRFToken() {
        return document.cookie.split("; ").find(row => row.startsWith("csrftoken="))
            ?.split("=")[1];
    }


    // ---------- Filters ----------
    const searchBox = document.getElementById("searchBox");
    const statusFilter = document.getElementById("statusFilter");
    const cards = Array.from(document.getElementsByClassName("card"));

    function applyFilters() {
        const search = searchBox.value.toLowerCase();
        const status = statusFilter.value.toLowerCase();

        cards.forEach(card => {
            const matches =
                (card.dataset.id.toLowerCase().includes(search) ||
                    card.dataset.time.toLowerCase().includes(search)) &&
                (!status || card.dataset.status.toLowerCase() === status);

            card.style.display = matches ? "block" : "none";
        });
    }

    searchBox.addEventListener("input", applyFilters);
    statusFilter.addEventListener("change", applyFilters);

});
