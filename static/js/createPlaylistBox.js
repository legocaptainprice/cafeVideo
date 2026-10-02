// If the create button is clicked
document.addEventListener("DOMContentLoaded", function() {
    const cafePlaylistCreateButton = document.getElementById("cafePlaylistCreateButton");
    const cafePlaylistCreatePanel = document.getElementById("cafePlaylistCreate");
    const cafeBackgroundFocus = document.getElementById("focus-screen");

    cafePlaylistCreateButton.addEventListener("click", () => {
        event.stopPropagation();
        cafePlaylistCreatePanel.classList.toggle("hidden");
        cafeBackgroundFocus.classList.toggle("hidden");
    });

    // If the cursor clicks anywhere outside the create playlist area
    document.addEventListener("click", (event) => {
        if (!cafePlaylistCreatePanel.contains(event.target) && !cafePlaylistCreateButton.contains(event.target)) {
            cafePlaylistCreatePanel.classList.add("hidden");
            cafeBackgroundFocus.classList.add("hidden");
        }
    });
});