// Get the 'pin' value from the current page URL
const params = new URLSearchParams(window.location.search);
const pin = params.get('pin');
// If a valid PIN exists, attach it to the "Next" button link
if (pin) {
  const nextBtn = document.getElementById('next-btn');
  nextBtn.href = `./oneChance.html?pin=${encodeURIComponent(pin)}`;
}

// Text content for the story typing effect
const text = "It's 2100...\nYou are the last human alive...";
let index = 0;
const speed = 50;

// Simulates a typewriter effect by adding one character at a time
function typeWriter() {
  if (index < text.length) {
    document.getElementById('story').innerHTML += text.charAt(index);
    index++;
    setTimeout(typeWriter, speed);
  } else {
    // Show the "Next" button once the text is fully displayed
    document.getElementById('next-btn').style.display = 'inline-block';
  }
}
// Start the typing effect when the page loads
window.onload = typeWriter;
