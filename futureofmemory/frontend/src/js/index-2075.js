document.addEventListener("DOMContentLoaded", () => {
  const video = document.getElementById("introVideo");
  const replayBtn = document.getElementById("replayBtn");
  const unmuteBtn = document.getElementById("unmuteBtn");

  // Replay button: restart video
  replayBtn.addEventListener("click", () => {
    video.currentTime = 0;
    video.play();
  });

  // Unmute button: enable sound
  unmuteBtn.addEventListener("click", () => {
    video.muted = false;
    video.play();
    unmuteBtn.style.display = "none"; // hide after enabling
  });

  // Keyboard shortcuts (optional)
  document.addEventListener("keydown", (e) => {
    if (e.key.toLowerCase() === "r") replayBtn.click();
    if (e.key.toLowerCase() === "s") window.location.href = "./scenario1.html";
    if (e.key.toLowerCase() === "m") unmuteBtn.click();
  });
});
