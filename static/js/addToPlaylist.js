// If the playlist is clicked
document.addEventListener("DOMContentLoaded", function() {
    const addVideoToPlaylist = document.querySelectorAll(".addVideoToPlaylist");

    addVideoToPlaylist.forEach(button => {
        button.addEventListener("click", async () => {
            const response = await fetch(button.dataset.url, {
                method: "POST"
            });

            if (!response.ok) return;

        });
    });
});