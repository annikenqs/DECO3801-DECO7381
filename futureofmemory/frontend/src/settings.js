// Mute / Unmute toggle
const muteBtn = document.getElementById('mute-btn');
let isMuted = false;

muteBtn.addEventListener('click', () => {
  isMuted = !isMuted;
  muteBtn.textContent = isMuted ? 'UNMUTE' : 'MUTE';

  // Example audio handling (if you have bgm):
  // const bgm = document.getElementById("bgm");
  // bgm.muted = isMuted;
});

// Font size toggle
const fontBtn = document.getElementById('font-btn');
let fontSizes = ['SMALL', 'MEDIUM', 'LARGE'];
let currentSize = 1; // MEDIUM

fontBtn.addEventListener('click', () => {
  currentSize = (currentSize + 1) % fontSizes.length;
  fontBtn.textContent = `FONT SIZE: ${fontSizes[currentSize]}`;

  document.body.style.fontSize =
  fontSizes[currentSize] === "SMALL"
    ? "14px"
    : fontSizes[currentSize] === "MEDIUM"
    ? "18px"
    : "22px";
});

document.getElementById('backBtn').addEventListener('click', () => {
  window.location.href = '../index.html';
});
