// If the like button is clicked
document.addEventListener("DOMContentLoaded", function() {
    const likeCommentButton = document.querySelectorAll(".likeCommentButton");

    likeCommentButton.forEach(button => {
        button.addEventListener("click", async () => {
            const response = await fetch(button.dataset.url, {
                method: "POST"
            });

            if (!response.ok) return;

            const isLiked = button.classList.contains("cafe-comment-button-liked");

            if (isLiked) {
                button.classList.remove("cafe-comment-button-liked");
                button.classList.add("cafe-comment-button");
                button.textContent = "Like";
            } else {
                button.classList.add("cafe-comment-button-liked");
                button.classList.remove("cafe-comment-button");
                button.textContent = "Liked";
            }
        });
    });
});