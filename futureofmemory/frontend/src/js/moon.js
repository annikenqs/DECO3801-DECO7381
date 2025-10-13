const params = new URLSearchParams(window.location.search);
const pin = params.get('pin');
if (pin) {
  const nextBtn = document.getElementById('next-btn');
  nextBtn.href = `./oneChance.html?pin=${encodeURIComponent(pin)}`;
}

const text = "It's 2100...\nYou are the last human alive...";
let index = 0;
const speed = 50;

function typeWriter() {
  if (index < text.length) {
    document.getElementById('story').innerHTML += text.charAt(index);
    index++;
    setTimeout(typeWriter, speed);
  } else {
    document.getElementById('next-btn').style.display = 'inline-block';
  }
}

window.onload = typeWriter;
