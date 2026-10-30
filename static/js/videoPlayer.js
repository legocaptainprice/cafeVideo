const video = document.querySelector("#video");
const playButton = document.querySelector("#play");
const progress = document.querySelector("#video-progress");
const timeDisplay = document.querySelector("#time");
const muteButton = document.querySelector("#mute");
const volumeSlider = document.querySelector("#video-volume");
const fullscreenButton = document.querySelector("#fullscreen");
const player = document.querySelector(".cafe-video-player");

video.addEventListener("click", () => {
    if (video.paused) {
        video.play();
    } else {
        video.pause();
    }
});

if (video && playButton && progress && timeDisplay &&
    muteButton && volumeSlider && fullscreenButton && player) {
    playButton.addEventListener("click", () => {
        if (video.paused) video.play();
        else video.pause();
    });

    video.addEventListener("play", () => playButton.textContent = "❚❚");
    video.addEventListener("pause", () => playButton.textContent = "▶");

    video.addEventListener("timeupdate", () => {
        if (video.duration) {
            progress.value = (video.currentTime / video.duration) * 100;

            const formatTime = seconds => {
                const minutes = Math.floor(seconds / 60);
                const remaining = Math.floor(seconds % 60);
                return `${minutes}:${String(remaining).padStart(2, "0")}`;
            };

            timeDisplay.textContent =
                `${formatTime(video.currentTime)} / ${formatTime(video.duration)}`;
        }
    });

    progress.addEventListener("input", () => {
        if (video.duration) {
            video.currentTime = (progress.value / 100) * video.duration;
        }
    });

    volumeSlider.addEventListener("input", () => {
        video.volume = Number(volumeSlider.value);
        video.muted = video.volume === 0;
        muteButton.textContent = video.muted ? "🔈︎" : "🔊︎";
    });

    muteButton.addEventListener("click", () => {
        video.muted = !video.muted;
        muteButton.textContent = video.muted ? "🔈︎" : "🔊︎";
    });

    fullscreenButton.addEventListener("click", () => {
        if (!document.fullscreenElement) {
            player.requestFullscreen();
        } else {
            document.exitFullscreen();
        }
    });
}