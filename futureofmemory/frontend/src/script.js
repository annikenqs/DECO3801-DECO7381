// ========== 灯塔交互（只控制亮/暗；雪花始终独立运行） ==========
const scene   = document.getElementById('scene');
const hotspot = document.getElementById('lighthouseHotspot');

const goBright = () => scene && scene.classList.add('is-bright');
const goDim    = () => scene && scene.classList.remove('is-bright');

// 鼠标/键盘可达性
if (hotspot) {
  hotspot.addEventListener('mouseenter', goBright);
  hotspot.addEventListener('mouseleave', goDim);
  hotspot.addEventListener('focus',      goBright);
  hotspot.addEventListener('blur',       goDim);
  
}

// ========== 像素风雪花（始终运行）Snow ==========
//According https://b23.tv/fagmbiZ
(function initSnow(){
  const canvas = document.getElementById('snowCanvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d', { alpha: true });

  // 配置
  const FLAKE_COUNT = 140;
  const SIZE_MIN = 1, SIZE_MAX = 3;
  const SPEED_MIN = 0.3, SPEED_MAX = 0.7;
  const DRIFT = 0.35; // 左右漂移幅度
  const SWAY  = 0.45; // 正弦摆动幅度

  let flakes = [];

  // 适配高 DPI，确保像素
  function fitCanvas(){
    const dpr = Math.max(1, Math.floor(window.devicePixelRatio || 1));
    const cssW = canvas.clientWidth = window.innerWidth;
    const cssH = canvas.clientHeight = window.innerHeight;
    canvas.width  = cssW * dpr;
    canvas.height = cssH * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.imageSmoothingEnabled = false;
  }

  const rand = (min, max) => Math.random() * (max - min) + min;

  function spawnFlakes(){
    flakes.length = 0;
    for (let i = 0; i < FLAKE_COUNT; i++){
      flakes.push({
        x: Math.random() * canvas.clientWidth,
        y: Math.random() * canvas.clientHeight,
        size: Math.floor(rand(SIZE_MIN, SIZE_MAX + 1)), // 1~3 像素
        vy: rand(SPEED_MIN, SPEED_MAX),
        drift: rand(-DRIFT, DRIFT),
        phase: Math.random() * Math.PI * 2
      });
    }
  }

  function draw(){
    ctx.clearRect(0, 0, canvas.clientWidth, canvas.clientHeight);
    ctx.fillStyle = '#FFFFFF';
    const t = performance.now() / 1000;

    for (const f of flakes){
      // 正弦摆动 + 轻微漂移
      const sway = Math.sin(t + f.phase) * SWAY;
      const px = Math.floor(f.x + sway);
      const py = Math.floor(f.y);
      ctx.fillRect(px, py, f.size, f.size);

      // 更新位置
      f.y += f.vy;
      f.x += f.drift * 0.2;

      // 出界循环
      if (f.y > canvas.clientHeight + 2){
        f.y = -4;
        f.x = Math.random() * canvas.clientWidth;
      }
      if (f.x < -4) f.x = canvas.clientWidth + 4;
      if (f.x > canvas.clientWidth + 4) f.x = -4;
    }
  }

  function loop(){
    draw();
    requestAnimationFrame(loop);
  }

  // 初始化并常驻运行
  fitCanvas();
  spawnFlakes();
  loop();

  // 调整尺寸时，重设像素比例与雪花
  let resizeTimer = null;
  window.addEventListener('resize', () => {
    fitCanvas();
    // 轻微防抖，防止频繁重算
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(spawnFlakes, 120);
  });
})();
