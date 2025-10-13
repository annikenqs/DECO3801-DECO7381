// futureofmemory/frontend/src/js/index-2075.js
document.addEventListener('DOMContentLoaded', () => {
  const video = document.getElementById('introVideo');
  const replayBtn = document.getElementById('replayBtn');
  const unmuteBtn = document.getElementById('unmuteBtn');
  const skipLink = document.getElementById('skipLink');

  const params = new URLSearchParams(window.location.search);
  const pin = params.get('pin');
  let nextUrl = './scenario1.html';
  if (pin) {
    nextUrl += `?pin=${encodeURIComponent(pin)}`;
    console.log('[Index-2075] Pin detected:', pin);
  }

  if (skipLink) skipLink.href = nextUrl;

  // Replay button
  if (replayBtn) {
    replayBtn.addEventListener('click', () => {
      if (video) {
        video.currentTime = 0;
        video.play();
      }
    });
  }

  // Unmute / Mute toggle
  if (unmuteBtn && video) {
    unmuteBtn.addEventListener('click', () => {
      video.muted = !video.muted;
      // unmuteBtn.textContent = video.muted ? 'Unmute' : 'Mute';
      if (video.paused) video.play();
    });
  }

  // Skip button
  if (skipBtn) {
    skipBtn.addEventListener('click', () => {
      window.location.href = './scenario1.html';
    });
  }

  // Keyboard shortcuts
  document.addEventListener('keydown', (e) => {
    // r = replay
    if (e.key === 'r') {
      if (video) {
        video.currentTime = 0;
        video.play();
      }
    }
    // s = skip
    if (e.key === 's') {
      window.location.href = nextUrl;
    }
    // m = mute toggle
    if (e.key === 'm' && video) {
      video.muted = !video.muted;
      if (video.paused) video.play();
    }
  });
});
