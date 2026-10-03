// Define the profile sections
document.addEventListener("DOMContentLoaded", () => {
    const cafeProfileVideosButton = document.getElementById("profileVideosButton");
    const cafeProfilePlaylistsButton = document.getElementById("profilePlaylistsButton");
    const cafeProfileRecommendedButton = document.getElementById("profileRecommendedButton");
    const cafeProfileRatingsButton = document.getElementById("profileRatingsButton");
    const cafeProfileCommentsButton = document.getElementById("profileCommentsButton");

    const cafeProfileVideos = document.getElementById("profileVideos");
    const cafeProfilePlaylists = document.getElementById("profilePlaylists");
    const cafeProfileRecommended = document.getElementById("profileRecommended");
    const cafeProfileRatings = document.getElementById("profileRatings");
    const cafeProfileComments = document.getElementById("profileComments");

    function showProfileSection(sectionToDisplay) {
        if (!sectionToDisplay.classList.contains("hidden")) {
            return;
        }

        const profileSections = [
            cafeProfileVideos,
            cafeProfilePlaylists,
            cafeProfileRecommended,
            cafeProfileRatings,
            cafeProfileComments
        ];

        profileSections.forEach(section => {
            section.classList.toggle("hidden", section !== sectionToDisplay);
        });
}

    cafeProfileVideosButton.addEventListener("click", () => {
        showProfileSection(cafeProfileVideos);
    });

    cafeProfilePlaylistsButton.addEventListener("click", () => {
        showProfileSection(cafeProfilePlaylists);
    });

    cafeProfileRecommendedButton.addEventListener("click", () => {
        showProfileSection(cafeProfileRecommended);
    });

    cafeProfileRatingsButton.addEventListener("click", () => {
        showProfileSection(cafeProfileRatings);
    });

    cafeProfileCommentsButton.addEventListener("click", () => {
        showProfileSection(cafeProfileComments);
    });

});

