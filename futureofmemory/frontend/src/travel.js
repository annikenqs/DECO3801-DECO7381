// Jump to the target (2075 starting page)
const TARGET_URL = 'index-2075.html';

// Countdown seconds
const TOTAL_SECONDS = 3;

// Briefly flash the 2075 background before the jump
const FINAL_BG = './Earth.jpg'; 

// —— elements —— 
const countEl = document.getElementById('count');
const lineEl  = document.getElementById('line');
const bgEl    = document.getElementById('bg');
const skipEl  = document.getElementById('skip');

// —— text ——
const lines = [
  'Initializing temporal rift…',
  'Calibration locked: Earth-year 2075.',
  'Brace for re-entry.'
];

let idx = 0;
function nextLine(){
  if (idx >= lines.length) return;
  lineEl.textContent = lines[idx++];
  // Each draft is switched at regular intervals
  setTimeout(nextLine, 900);
}

// —— Countdown & jump—— 
let left = TOTAL_SECONDS;
countEl.textContent = String(left).padStart(2,'0');

const timer = setInterval(() => {
  left--;
  if (left <= 0){
    clearInterval(timer);
    // Optional (undetermined, creating a sense of landing point?)
    if (FINAL_BG){
      bgEl.style.filter = 'contrast(1.08) brightness(1.05)';
      bgEl.style.backgroundImage = `url('${FINAL_BG}')`;
    }
    
    setTimeout(() => { window.location.href = TARGET_URL; }, 300);
  } else {
    countEl.textContent = String(left).padStart(2,'0');
    
    bgEl.style.filter = left % 2 ? 'contrast(1.05) brightness(.98)' : 'contrast(1.08) brightness(1.02)';
  }
}, 1000);

// —— Skip —— 
skipEl.addEventListener('click', () => {
  window.location.href = TARGET_URL;
});

// Start the copywriting carousel
nextLine();
