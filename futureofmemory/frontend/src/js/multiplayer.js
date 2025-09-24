// multiplayer.js

const newGameBtn = document.getElementById("new-game-btn");
const joinBtn = document.getElementById("join-btn");

// Start a new multiplayer game
newGameBtn.addEventListener("click", () => {
  // Generate random 6-digit PIN
  const pin = Math.floor(100000 + Math.random() * 900000);
  // Redirect to lobby with pin
  window.location.href = `lobby.html?pin=${pin}`;
});

// Join existing game
joinBtn.addEventListener("click", () => {
  const pin = document.getElementById("game-pin").value.trim();

  if (!pin) {
    alert("Please enter a Game PIN");
    return;
  }

  // Redirect to lobby with entered pin
  window.location.href = `lobby.html?pin=${pin}`;
});
