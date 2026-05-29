// If the add to playlist button is clicked
document.addEventListener("DOMContentLoaded", function() {
    const cafeAddToPlaylistButton = document.getElementById("showPlaylists");
    const cafeAddToPlaylistPanel = document.getElementById("addToPlaylist");

    cafeAddToPlaylistButton.addEventListener("click", () => {
        event.stopPropagation();
        cafeAddToPlaylistPanel.classList.toggle("hidden");
    });

    // If the cursor clicks anywhere outside the create playlist area
    document.addEventListener("click", (event) => {
        if (!cafeAddToPlaylistPanel.contains(event.target) && !cafeAddToPlaylistButton.contains(event.target)) {
            cafeAddToPlaylistPanel.classList.add("hidden");
        }
    });
});