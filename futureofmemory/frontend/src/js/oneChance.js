const params = new URLSearchParams(window.location.search);
const pin = params.get('pin');
if (pin) {
  const nextBtn = document.getElementById('next-btn');
  nextBtn.href = `./travel.html?pin=${encodeURIComponent(pin)}`;
}

const text = 'But you have one chance to go back...';
let index = 0;
const speed = 50; // typing speed

function typeWriter() {
  if (index < text.length) {
    document.getElementById('story').innerHTML += text.charAt(index);
    index++;
    setTimeout(typeWriter, speed);
  } else {
    document.getElementById('next-btn').style.display = 'inline-block'; // show NEXT button
  }
}

window.onload = typeWriter;
