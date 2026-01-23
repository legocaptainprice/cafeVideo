// If the notification button is clicked
document.addEventListener("DOMContentLoaded", function() {
    const subscribeButton = document.getElementById("subscribeButton");

    if (subscribeButton) {
        subscribeButton.addEventListener("click", async () => {
            const response = await fetch(subscribeButton.dataset.url, {
                method: "POST"
            });

            if (!response.ok) return;

            const isSubscribed = subscribeButton.textContent.includes("Subscribed");

            if (isSubscribed) {
                subscribeButton.textContent = "Subscribe";
            } else {
                subscribeButton.textContent = "Subscribed";
            }
        });
    }
});