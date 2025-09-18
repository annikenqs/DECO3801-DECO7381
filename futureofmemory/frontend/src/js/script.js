// ========== Lighthouse interaction ==========
const scene = document.getElementById('scene');
const hotspot = document.getElementById('lighthouseHotspot');

const goBright = () => scene && scene.classList.add('is-bright');
const goDim = () => scene && scene.classList.remove('is-bright');

// hotspot
if (hotspot) {
  hotspot.addEventListener('mouseenter', goBright);
  hotspot.addEventListener('mouseleave', goDim);
  hotspot.addEventListener('focus', goBright);
  hotspot.addEventListener('blur', goDim);
}

// ========== Snow ==========
//According https://b23.tv/fagmbiZ
(function initSnow() {
  const canvas = document.getElementById('snowCanvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d', {alpha: true});

  // Configuration
  const FLAKE_COUNT = 140;
  const SIZE_MIN = 1,
    SIZE_MAX = 3;
  const SPEED_MIN = 0.3,
    SPEED_MAX = 0.7;
  const DRIFT = 0.35; // Left and right drift amplitude
  const SWAY = 0.45; // Sinusoidal swing amplitude

  let flakes = [];

  // Adapt to high DPI to ensure pixel count
  function fitCanvas() {
    const dpr = Math.max(1, Math.floor(window.devicePixelRatio || 1));
    const cssW = (canvas.clientWidth = window.innerWidth);
    const cssH = (canvas.clientHeight = window.innerHeight);
    canvas.width = cssW * dpr;
    canvas.height = cssH * dpr;
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
        size: Math.floor(rand(SIZE_MIN, SIZE_MAX + 1)), // 1~3 size
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
      // Sinusoidal swing + slight drift
      const sway = Math.sin(t + f.phase) * SWAY;
      const px = Math.floor(f.x + sway);
      const py = Math.floor(f.y);
      ctx.fillRect(px, py, f.size, f.size);

      // Update location
      f.y += f.vy;
      f.x += f.drift * 0.2;

      // Out-of-bounds loop
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

  // Initialize and run
  fitCanvas();
  spawnFlakes();
  loop();

  // When adjusting the size, reset the pixel ratio and snowflakes
  let resizeTimer = null;
  window.addEventListener('resize', () => {
    fitCanvas();
    // Slight anti-shake to prevent frequent recalculation
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(spawnFlakes, 120);
  });
})();
