// ========== Lighthouse interaction ==========
const scene = document.getElementById('scene');
const hotspot = document.getElementById('lighthouseHotspot');

const goBright = () => scene && scene.classList.add('is-bright');
const goDim = () => scene && scene.classList.remove('is-bright');

if (hotspot) {
  hotspot.addEventListener('mouseenter', goBright);
  hotspot.addEventListener('mouseleave', goDim);
  hotspot.addEventListener('focus', goBright);
  hotspot.addEventListener('blur', goDim);
}

// ========== Snow ==========
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

  const rand = (min, max) => Math.random() * (max - min) + min;

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

      if (f.y > canvas.clientHeight + 2) {
        f.y = -4;
        f.x = Math.random() * canvas.clientWidth;
      }
      if (f.x < -4) f.x = canvas.clientWidth + 4;
      if (f.x > canvas.clientWidth + 4) f.x = -4;
    }
  }

  function loop() {
    draw();
    requestAnimationFrame(loop);
  }

  fitCanvas();
  spawnFlakes();
  loop();

  let resizeTimer = null;
  window.addEventListener('resize', () => {
    fitCanvas();
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(spawnFlakes, 120);
  });
})();

import {createSession} from '../api/futureMemoryApi.js';

window.addEventListener('DOMContentLoaded', () => {
  const newGameBtn = document.querySelector('a.btn[href="src/html/lobby.html"]');

  if (!newGameBtn) {
    return;
  }

  console.log('✅ Script loaded, button found');

  newGameBtn.addEventListener('click', async (e) => {
    e.preventDefault();

    try {
      const session = await createSession({faction: 'Unknown', year: 2075});

      const pin = session?.pin;
      if (!pin) throw new Error("No 'pin' returned from backend");

      const targetUrl = `src/html/lobby.html?pin=${encodeURIComponent(pin)}`;
      window.location.href = targetUrl;
    } catch (err) {
      alert(`Failed to start new game: ${err.message}`);
    }
  });
});
