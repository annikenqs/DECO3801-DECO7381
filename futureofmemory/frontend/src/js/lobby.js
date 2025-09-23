// lobby.js

const playersList = document.getElementById('players-list');
const startButton = document.getElementById('start-game-btn');

// Example players
let players = ['Johanne', 'Anniken', 'Sam', 'Ihsan', 'Jiani', 'Zeyu'];

function renderPlayers() {
  playersList.innerHTML = '';
  players.forEach((player) => {
    const p = document.createElement('p');
    p.textContent = player;
    playersList.appendChild(p);
  });
}

// simulate players joining
setTimeout(renderPlayers, 1000);

startButton.addEventListener('click', () => {
  alert('Game starting...');
  // Redirect when ready
  // window.location.href = "game.html";
});
