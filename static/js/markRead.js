// If the mark as read button is clicked
document.addEventListener("DOMContentLoaded", function() {
    const markReadButton = document.querySelectorAll(".markReadButton");

    markReadButton.forEach(button => {
        button.addEventListener("click", async () => {
            const response = await fetch(button.dataset.url, {
                method: "POST"
            });

            if (!response.ok) return;

            const isRead = button.classList.contains("mark-read");

            if (isRead) {
                button.classList.remove("mark-read");
                button.textContent = "Mark as Read";
            } else {
                button.classList.add("mark-read");
                button.textContent = "Marked as Read";
            }
        });
    });
});