import { joinSession } from '/src/api/futureMemoryApi.js';


const joinBtn = document.getElementById('join-btn');

joinBtn.addEventListener('click', async () => {
  const pin = document.getElementById('game-pin').value.trim();

  if (!pin) {
    alert('Please enter a Game PIN');
    return;
  }

    try {
    const response = await joinSession({ pin });

    if (response?.success || response?.status === 'ok') {
      window.location.href = `lobby.html?pin=${pin}`;
    } else {
      alert('Invalid or expired game PIN. Please check and try again.');
    }

  } catch (error) {
    console.error('Error joining session:', error);
    alert('Could not join game, the PIN might be invalid or the server is unavailable.');
  }
});
