// futureofmemory/frontend/src/js/index-2075.js
document.addEventListener('DOMContentLoaded', () => {
  const video = document.getElementById('introVideo');
  const replayBtn = document.getElementById('replayBtn');
  const unmuteBtn = document.getElementById('unmuteBtn'); 
  const skipBtn = document.getElementById('skipBtn'); 

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
      window.location.href = './scenario1.html';
    }
    // m = mute toggle
    if (e.key === 'm' && video) {
      video.muted = !video.muted;
      if (video.paused) video.play();
    }
  });
});
