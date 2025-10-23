// Get the 'pin' value from the URL query string
const params = new URLSearchParams(window.location.search);
const pin = params.get('pin');
// If a PIN exists, attach it to the "Next" button link leading to travel.html
if (pin) {
  const nextBtn = document.getElementById('next-btn');
  nextBtn.href = `./travel.html?pin=${encodeURIComponent(pin)}`;
}

// Text content for the story typing effect
const text = 'But you have one chance to go back...';
let index = 0;
const speed = 50; // typing speed

// Simulates typing animation by displaying one character at a time
function typeWriter() {
  if (index < text.length) {
    document.getElementById('story').innerHTML += text.charAt(index);
    index++;
    setTimeout(typeWriter, speed);
  } else {
    // Show the "Next" button once the text finishes typing
    document.getElementById('next-btn').style.display = 'inline-block'; // show NEXT button
  }
}

window.onload = typeWriter;
