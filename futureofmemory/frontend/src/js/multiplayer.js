// multiplayer.js

const newGameBtn = document.getElementById('new-game-btn');
const joinBtn = document.getElementById('join-btn');

newGameBtn.addEventListener('click', () => {
  // For now, just redirect to lobby with a placeholder PIN
  window.location.href = 'lobby.html';
});

joinBtn.addEventListener('click', () => {
  const pin = document.getElementById('game-pin').value.trim();
  const nickname = document.getElementById('nickname').value.trim();

  if (!pin || !nickname) {
    alert('Please enter both a Game PIN and a Nickname');
    return;
  }

  // For now, just redirect to lobby (you can add backend logic later)
  window.location.href = 'lobby.html';
});
