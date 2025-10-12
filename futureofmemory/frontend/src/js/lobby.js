import {getPlayerCount, updateGameStatus, getGameState} from '/src/api/futureMemoryApi.js';

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
    const data = await getPlayerCount({pin});
    playerCount = data.player_count ?? 0;
    updatePlayerCount();
  } catch (err) {
    console.error('Error fetching player count:', err);
    playersInfo.innerHTML = `<p class="error">Could not load player count</p>`;
  }
}

// Check game status
async function checkGameStatus() {
  try {
    const data = await getGameState({pin});
    if (data?.status === 'in-progress') {
      window.location.href = `moon.html?pin=${encodeURIComponent(pin)}`;
    }
  } catch (err) {
    console.warn('Could not fetch game status:', err);
  }
}

// Initial state
updatePlayerCount();
fetchPlayerCount();

setInterval(fetchPlayerCount, 3000);
setInterval(checkGameStatus, 3000);

// Redirect players to moon.html when starting a game
startButton.addEventListener('click', async () => {
  if (playerCount === 0) {
    alert('At least 1 player must join before starting.');
    return;
  }
  try {
    await updateGameStatus({pin, status: 'in-progress'});
    window.location.href = `moon.html?pin=${encodeURIComponent(pin)}`;
  } catch (err) {
    console.error('Failed to start game:', err);
    alert('Failed to start game.');
  }
});
