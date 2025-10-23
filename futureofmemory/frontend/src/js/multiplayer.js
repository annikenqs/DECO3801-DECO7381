// Import function to join an existing game session from the backend API
import {joinSession} from '/src/api/futureMemoryApi.js';

// Get the "Join Game" button element
const joinBtn = document.getElementById('join-btn');

// Listen for button click to attempt joining a session
joinBtn.addEventListener('click', async () => {
  // Retrieve and trim the game PIN entered by the user
  const pin = document.getElementById('game-pin').value.trim();

  // Show alert if no PIN is entered
  if (!pin) {
    alert('Please enter a Game PIN');
    return;
  }

  try {
    // Send request to backend to join the session with the given PIN
    const response = await joinSession({pin});

    // If backend confirms success, redirect to lobby with same PIN
    if (response?.success || response?.status === 'ok') {
      window.location.href = `lobby.html?pin=${pin}`;
      // Otherwise, show an error message for invalid or expired PIN
    } else {
      alert('Invalid or expired game PIN. Please check and try again.');
    }
    // Catch and display network or server errors
  } catch (error) {
    console.error('Error joining session:', error);
    alert('Could not join game, the PIN might be invalid or the server is unavailable.');
  }
});
