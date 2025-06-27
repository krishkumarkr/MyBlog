document.addEventListener("DOMContentLoaded", function () {
    const likeButtons = document.querySelectorAll(".like-btn");

    likeButtons.forEach((likeBtn) => {
        likeBtn.addEventListener("click", function (e) {
            e.preventDefault();

            const blogId = likeBtn.dataset.blogId;

            fetch(`/toggle_like/${blogId}`, {
                method: "POST",
                headers: {
                    "X-Requested-With": "XMLHttpRequest"
                },
                credentials: "same-origin"
            })
            .then(async response => {

                if (response.status === 401) {
                    showToast("Please log in to like or unlike blogs.");
                    return null;
                }

                const contentType = response.headers.get("content-type");

                if (!response.ok) {
                    const text = await response.text();
                    throw new Error(`Error ${response.status}: ${text}`);
                }

                if (contentType && contentType.includes("application/json")) {
                    return response.json();
                } else {
                    const text = await response.text();
                    throw new Error("Expected JSON, got: " + text.slice(0, 100));
                }
            })
            .then(data => {
                if (!data) return;

                if (data.success) {
                    const icon = likeBtn.querySelector(".like-icon");
                    const count = likeBtn.querySelector(".like-count");

                    if (data.action === "liked") {
                        icon.textContent = "❤️";
                        count.style.color = "white";
                        likeBtn.classList.remove("btn-outline-secondary");
                        likeBtn.classList.add("btn-secondary");
                    } else if (data.action === "unliked") {
                        icon.textContent = "♡";
                        count.style.color = "white";
                        likeBtn.classList.remove("btn-secondary");
                        likeBtn.classList.add("btn-outline-secondary");
                    }

                    count.textContent = data.like_count;
                } else {
                    alert(data.message || "Something went wrong.");
                }
            })
            .catch(error => {
                console.error("Fetch error:", error);
                alert("Error: " + error.message);
            });
        });
    });
});

function showToast(message) {
    const toastEl = document.getElementById("like-toast");
    const toastMessage = document.getElementById("like-toast-message");

    if (toastEl && toastMessage) {
        toastMessage.textContent = message;
        const toast = new bootstrap.Toast(toastEl);
        toast.show();
    }
}

