// —— 基本参数 ——
// 跳转目标（2075 起点页）：
const TARGET_URL = 'index-2075.html';

// 倒计时秒数
const TOTAL_SECONDS = 3;

// 在跳转前短暂闪一下 2075 背景
const FINAL_BG = './Earth.jpg'; // 如果没有这张图，可留空字符串 ''

// —— 元素 —— 
const countEl = document.getElementById('count');
const lineEl  = document.getElementById('line');
const bgEl    = document.getElementById('bg');
const skipEl  = document.getElementById('skip');

// —— 打字/提示文案（可自定义） ——
const lines = [
  'Initializing temporal rift…',
  'Calibration locked: Earth-year 2075.',
  'Brace for re-entry.'
];

let idx = 0;
function nextLine(){
  if (idx >= lines.length) return;
  lineEl.textContent = lines[idx++];
  // 每条文案隔一段时间切换
  setTimeout(nextLine, 900);
}

// —— 倒计时 & 跳转 —— 
let left = TOTAL_SECONDS;
countEl.textContent = String(left).padStart(2,'0');

const timer = setInterval(() => {
  left--;
  if (left <= 0){
    clearInterval(timer);
    // 可选：在跳转前瞬间切换到 2075 背景，制造“落点”感
    if (FINAL_BG){
      bgEl.style.filter = 'contrast(1.08) brightness(1.05)';
      bgEl.style.backgroundImage = `url('${FINAL_BG}')`;
    }
    // 稍微延迟 300ms，再跳
    setTimeout(() => { window.location.href = TARGET_URL; }, 300);
  } else {
    countEl.textContent = String(left).padStart(2,'0');
    // 小的闪烁感
    bgEl.style.filter = left % 2 ? 'contrast(1.05) brightness(.98)' : 'contrast(1.08) brightness(1.02)';
  }
}, 1000);

// —— Skip 手动跳转 —— 
skipEl.addEventListener('click', () => {
  window.location.href = TARGET_URL;
});

// 启动文案轮播
nextLine();
