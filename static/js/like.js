document.addEventListener("DOMContentLoaded", () => {
    const likeButtons = document.querySelectorAll(".like-btn");

    likeButtons.forEach((likeBtn) => {
        likeBtn.addEventListener("click", async (e) => {
            e.preventDefault();

            const blogId = likeBtn.dataset.blogId;

            try {
                const response = await fetch(`/toggle_like/${blogId}`, {
                    method: "POST",
                    headers: {
                        "X-Requested-With": "XMLHttpRequest"
                    },
                    credentials: "same-origin"
                });

                // Handle logged-out users trying to like a post
                if (response.status === 401) {
                    showToast("Please log in to like or unlike blogs.");
                    return;
                }

                if (!response.ok) {
                    const text = await response.text();
                    throw new Error(`Error ${response.status}: ${text}`);
                }

                const data = await response.json();

                if (data.success) {
                    const icon = likeBtn.querySelector(".like-icon");
                    const count = likeBtn.querySelector(".like-count");

                    // Toggle the UI based on the backend action
                    if (data.action === "liked") {
                        icon.textContent = "❤️";
                        likeBtn.classList.replace("btn-outline-secondary", "btn-secondary");
                    } else if (data.action === "unliked") {
                        icon.textContent = "♡";
                        likeBtn.classList.replace("btn-secondary", "btn-outline-secondary");
                    }

                    // Update the count number
                    count.textContent = data.like_count;
                } else {
                    alert(data.message || "Something went wrong.");
                }
            } catch (error) {
                console.error("Fetch error:", error);
                alert("An error occurred while updating your like.");
            }
        });
    });
});

// Triggers the Bootstrap Toast notification
function showToast(message) {
    const toastEl = document.getElementById("like-toast");
    const toastMessage = document.getElementById("like-toast-message");

    if (toastEl && toastMessage) {
        toastMessage.textContent = message;
        const toast = new bootstrap.Toast(toastEl);
        toast.show();
    }
}