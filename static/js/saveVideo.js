// If the save button is clicked
document.addEventListener("DOMContentLoaded", function() {
    const saveButton = document.getElementById("Save");

    if (saveButton) {
        saveButton.addEventListener("click", async () => {
            const response = await fetch(saveButton.dataset.url, {
                method: "POST"
            });

            if (!response.ok) return;

            const isSaved = saveButton.classList.contains("cafe-comment-button-liked");

            if (isSaved) {
                saveButton.classList.remove("cafe-comment-button-liked");
                saveButton.classList.add("cafe-comment-button");
                saveButton.textContent = "Save";
            } else {
                saveButton.classList.add("cafe-comment-button-liked");
                saveButton.classList.remove("cafe-comment-button");
                saveButton.textContent = "Saved";
            }
        });
    }
});