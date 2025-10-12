import { getPlayerCount } from '/src/api/futureMemoryApi.js';

// lobby.js

// Get Game PIN from URL
const urlParams = new URLSearchParams(window.location.search);
const pin = urlParams.get('pin') || '000024'; // fallback
document.getElementById('game-pin-display').textContent = `Game PIN: ${pin}`;

const playersInfo = document.getElementById('players-info');
const startButton = document.getElementById('start-game-btn');

// Start at 0 players
let playerCount = 0;
const maxPlayers = 5;

function updatePlayerCount() {
  playersInfo.innerHTML = `<p>${playerCount} / ${maxPlayers} players joined</p>`;
}

// Fetch player count
async function fetchPlayerCount() {
  try {
    const data = await getPlayerCount({ pin });
    playerCount = data.player_count ?? 0;
    updatePlayerCount();
  } catch (err) {
    console.error('Error fetching player count:', err);
    playersInfo.innerHTML = `<p class="error">Could not load player count</p>`;
  }
}

// Initial state
updatePlayerCount();
fetchPlayerCount();

setInterval(fetchPlayerCount, 20000);

startButton.addEventListener('click', () => {
  if (playerCount === 0) {
    alert('At least 1 player must join before starting.');
    return;
  }
  alert('Game starting...');
  // Redirect to actual game page later
  // window.location.href = "game.html";
});
