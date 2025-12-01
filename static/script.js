document.addEventListener("DOMContentLoaded", () => {

    // --------------------------------------
    // IMAGE PREVIEW MODAL
    // --------------------------------------
    const imgModal = document.getElementById("imgModal");
    const fullImage = document.getElementById("fullImage");

    document.querySelectorAll(".zoomable").forEach(img => {
        img.addEventListener("click", () => {
            imgModal.style.display = "block";
            fullImage.src = img.src;
        });
    });

    imgModal.querySelector(".close").addEventListener("click", () => {
        imgModal.style.display = "none";
    });

    imgModal.addEventListener("click", e => {
        if (e.target === imgModal) imgModal.style.display = "none";
    });



    // --------------------------------------
    // YES / NO BUTTON HANDLERS
    // --------------------------------------
    document.querySelectorAll(".card").forEach(card => {
        const yesBtn = card.querySelector(".yes-btn");
        const noBtn = card.querySelector(".no-btn");
        const faultId = card.dataset.id;

        yesBtn.addEventListener("click", () => {
            handleAction(yesBtn, noBtn, card, faultId, "yes");
        });

        noBtn.addEventListener("click", () => {
            handleAction(noBtn, yesBtn, card, faultId, "no");
        });
    });



    // --------------------------------------
    // MAIN ACTION FUNCTION
    // --------------------------------------
    async function handleAction(activeBtn, otherBtn, card, faultId, type) {

        // ORIGINAL button text save
        const originalText = activeBtn.textContent;

        // Set processing state
        activeBtn.textContent = "Processing...";
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
            console.log("⚙️ Backend Response:", data);

            const count = data.count || 1;

            if (type === "yes") {
                alert(`✔️ ${count} images sent for annotation!`);

                // 👇 Redirect handled here
                if (data.redirect) {
                    console.log("➡ Redirecting to:", data.redirect);
                    setTimeout(() => {
                        window.location.href = data.redirect;
                    }, 500);
                    return; // stop further execution
                }
            } else {
                alert(`🚫 ${count} images saved with labels!`);
            }

            // REMOVE all duplicated cards
            if (data.copied_ids && Array.isArray(data.copied_ids)) {
                data.copied_ids.forEach(id => {
                    const removeCard = document.querySelector(`.card[data-id="${id}"]`);
                    if (removeCard) fadeOutCard(removeCard);
                });
            } else {
                fadeOutCard(card);
            }

        } catch (error) {
            alert("⚠️ Something went wrong!");
            console.error(error);

        } finally {
            // Restore original button text
            activeBtn.textContent = originalText;

            // Re-enable buttons
            activeBtn.disabled = false;
            otherBtn.disabled = false;
        }
    }



    // --------------------------------------
    // Fade-out animation
    // --------------------------------------
    function fadeOutCard(card) {
        card.style.transition = "opacity 0.5s ease";
        card.style.opacity = "0";
        setTimeout(() => card.remove(), 500);
    }



    // --------------------------------------
    // CSRF TOKEN
    // --------------------------------------
    function getCSRFToken() {
        return document.cookie.split("; ").find(row => row.startsWith("csrftoken="))
            ?.split("=")[1];
    }



    // --------------------------------------
    // FILTERS
    // --------------------------------------
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
