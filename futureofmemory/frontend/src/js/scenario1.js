// scenario1.js
import {checkFactionVoting} from '../api/futureMemoryApi.js';

const STORAGE_KEY = 'worldMode';
const API_BASE = '/api';

function getPinFromUrl() {
  const params = new URLSearchParams(window.location.search);
  return params.get('pin');
}

// --- send vote to backend ---
async function voteForFaction(pin, faction) {
  try {
    const res = await fetch(`${API_BASE}/session/${pin}/faction/vote/`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({faction}),
    });

    const data = await res.json();

    if (!res.ok) {
      showMessage(`Error: ${data.error || 'Unable to submit vote'}`);
      showChoices();
      return;
    }

    console.log('Vote successful:', data);
    hideChoices();
    showMessage('Waiting for other people to vote...');

    if (data.allVoted) {
      showMessage(`All players have voted! Final faction: ${data.faction}`);
      goToNextPage(data.faction);
    }
  } catch (err) {
    console.error('Vote failed:', err);
    showMessage('An error occurred. Please try again.');
    showChoices();
  }
}

// --- poll status ---
async function pollVotingStatus(pin) {
  try {
    const status = await checkFactionVoting({pin});
    console.log('[Polling] Faction vote status:', status);

    if (status.allVoted && status.faction) {
      showMessage(`All players have voted! Final faction: ${status.faction}`);
      goToNextPage(status.faction);
    }
  } catch (err) {
    console.warn('[Polling] Failed to check faction voting:', err.message);
  }
}

// --- UI helpers ---
function hideChoices() {
  document.querySelectorAll('.choice').forEach((btn) => (btn.style.display = 'none'));
}
function showChoices() {
  document.querySelectorAll('.choice').forEach((btn) => (btn.style.display = 'grid'));
}
function showMessage(msg) {
  let msgEl = document.getElementById('vote-message');
  if (!msgEl) {
    msgEl = document.createElement('p');
    msgEl.id = 'vote-message';
    msgEl.style.marginTop = '1.5rem';
    msgEl.style.fontSize = '1.2rem';
    msgEl.style.textAlign = 'center';
    document.querySelector('.wrap').appendChild(msgEl);
  }
  msgEl.textContent = msg;
}
function goToNextPage() {
  const nextUrl = 'GeneralScenario.html';
  setTimeout(() => (location.href = nextUrl), 4000);
}

// --- main ---
document.addEventListener('DOMContentLoaded', () => {
  const choices = document.querySelectorAll('.choice');
  const pin = getPinFromUrl();

  if (!pin) {
    showMessage('Error: no PIN found in URL.');
    return;
  }

  choices.forEach((btn) => {
    btn.addEventListener('click', async () => {
      const faction = btn.dataset.mode;
      choices.forEach((b) => b.classList.remove('selected'));
      btn.classList.add('selected');

      localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({faction, decidedAt: new Date().toISOString()})
      );

      await voteForFaction(pin, faction);
    });
  });

  // Poll every 5 seconds
  setInterval(() => pollVotingStatus(pin), 5000);
});
