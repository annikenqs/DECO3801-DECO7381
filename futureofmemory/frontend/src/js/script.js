// ========== Lighthouse interaction ==========
// Handles light/dim visual effect when hovering over the lighthouse
const scene = document.getElementById('scene');
const hotspot = document.getElementById('lighthouseHotspot');

const goBright = () => scene && scene.classList.add('is-bright');
const goDim = () => scene && scene.classList.remove('is-bright');

// Toggle brightness when lighthouse hotspot is hovered or focused
if (hotspot) {
  hotspot.addEventListener('mouseenter', goBright);
  hotspot.addEventListener('mouseleave', goDim);
  hotspot.addEventListener('focus', goBright);
  hotspot.addEventListener('blur', goDim);
}

// ========== Snow ==========
// Creates a continuous falling snow animation using canvas
(function initSnow() {
  const canvas = document.getElementById('snowCanvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d', {alpha: true});

  const FLAKE_COUNT = 140;
  const SIZE_MIN = 1,
    SIZE_MAX = 3;
  const SPEED_MIN = 0.3,
    SPEED_MAX = 0.7;
  const DRIFT = 0.35,
    SWAY = 0.45;
  let flakes = [];

  // Adjust canvas resolution for different screen sizes and pixel ratios
  function fitCanvas() {
    const dpr = Math.max(1, Math.floor(window.devicePixelRatio || 1));
    const cssW = window.innerWidth;
    const cssH = window.innerHeight;
    canvas.width = cssW * dpr;
    canvas.height = cssH * dpr;
    canvas.style.width = `${cssW}px`;
    canvas.style.height = `${cssH}px`;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.imageSmoothingEnabled = false;
  }

  // Generate random number within a range
  const rand = (min, max) => Math.random() * (max - min) + min;

  // Create snowflake objects with random positions and speeds
  function spawnFlakes() {
    flakes.length = 0;
    for (let i = 0; i < FLAKE_COUNT; i++) {
      flakes.push({
        x: Math.random() * canvas.clientWidth,
        y: Math.random() * canvas.clientHeight,
        size: Math.floor(rand(SIZE_MIN, SIZE_MAX + 1)),
        vy: rand(SPEED_MIN, SPEED_MAX),
        drift: rand(-DRIFT, DRIFT),
        phase: Math.random() * Math.PI * 2,
      });
    }
  }

  // Draw and animate snowflakes on screen
  function draw() {
    ctx.clearRect(0, 0, canvas.clientWidth, canvas.clientHeight);
    ctx.fillStyle = '#FFFFFF';
    const t = performance.now() / 1000;

    for (const f of flakes) {
      const sway = Math.sin(t + f.phase) * SWAY;
      const px = Math.floor(f.x + sway);
      const py = Math.floor(f.y);
      ctx.fillRect(px, py, f.size, f.size);

      f.y += f.vy;
      f.x += f.drift * 0.2;

      // Recycle flakes when they move off-screen
      if (f.y > canvas.clientHeight + 2) {
        f.y = -4;
        f.x = Math.random() * canvas.clientWidth;
      }
      if (f.x < -4) f.x = canvas.clientWidth + 4;
      if (f.x > canvas.clientWidth + 4) f.x = -4;
    }
  }
  // Main animation loop
  function loop() {
    draw();
    requestAnimationFrame(loop);
  }

  fitCanvas();
  spawnFlakes();
  loop();

  // Recreate flakes and resize canvas on window resize
  let resizeTimer = null;
  window.addEventListener('resize', () => {
    fitCanvas();
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(spawnFlakes, 120);
  });
})();

// ========== Session creation ==========
import {createSession, joinSession} from '../api/futureMemoryApi.js';

// Wait until page content is loaded before activating "New Game" button
window.addEventListener('DOMContentLoaded', () => {
  const newGameBtn = document.querySelector('a.btn[href="src/html/lobby.html"]');
  if (!newGameBtn) return;

  // When clicked, create a new session and redirect player to lobby with PIN
  newGameBtn.addEventListener('click', async (e) => {
    e.preventDefault();

    try {
      // Request a new game session from backend
      const session = await createSession({faction: 'Unknown', year: 2075});
      // Extract session PIN and join the same session
      const pin = session?.pin;
      if (!pin) throw new Error("No 'pin' returned from backend");

      await joinSession({pin});

      // Redirect to lobby page with PIN in URL
      const targetUrl = `src/html/lobby.html?pin=${encodeURIComponent(pin)}`;
      window.location.href = targetUrl;
    } catch (err) {
      alert(`Failed to start new game: ${err.message}`);
    }
  });
});
