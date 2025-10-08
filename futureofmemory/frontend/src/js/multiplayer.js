const newGameBtn = document.getElementById('new-game-btn');
const joinBtn = document.getElementById('join-btn');

newGameBtn.addEventListener('click', () => {
  const pin = Math.floor(100000 + Math.random() * 900000);
  window.location.href = `lobby.html?pin=${pin}`;
});

joinBtn.addEventListener('click', () => {
  const pin = document.getElementById('game-pin').value.trim();

  if (!pin) {
    alert('Please enter a Game PIN');
    return;
  }

  window.location.href = `lobby.html?pin=${pin}`;
});
