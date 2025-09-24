// lobby.js

// Get Game PIN from URL
const urlParams = new URLSearchParams(window.location.search);
const pin = urlParams.get("pin") || "123456"; // fallback
document.getElementById("game-pin-display").textContent = `Game PIN: ${pin}`;

const playersInfo = document.getElementById("players-info");
const startButton = document.getElementById("start-game-btn");

// Start at 0 players
let playerCount = 0;
const maxPlayers = 5;

function updatePlayerCount() {
  playersInfo.innerHTML = `<p>${playerCount} / ${maxPlayers} players joined</p>`;
}

// Initial state
updatePlayerCount();

// Simulate you joining after 1 second
setTimeout(() => {
  playerCount = 1;
  updatePlayerCount();
}, 1000);

startButton.addEventListener("click", () => {
  if (playerCount === 0) {
    alert("At least 1 player must join before starting.");
    return;
  }
  alert("Game starting...");
  // Redirect to actual game page later
  // window.location.href = "game.html";
});
