// If the like button is clicked
document.addEventListener("DOMContentLoaded", function() {
    const likeButton = document.getElementById("likeButton");

    if (likeButton) {
        likeButton.addEventListener("click", async () => {
            const response = await fetch(likeButton.dataset.url, {
                method: "POST"
            });

            if (!response.ok) return;

            const isLiked = likeButton.classList.contains("cafe-comment-button-liked");

            if (isLiked) {
                likeButton.classList.remove("cafe-comment-button-liked");
                likeButton.classList.add("cafe-comment-button");
                likeButton.textContent = "Like";
            } else {
                likeButton.classList.add("cafe-comment-button-liked");
                likeButton.classList.remove("cafe-comment-button");
                likeButton.textContent = "Liked";
            }
        });
    }
});