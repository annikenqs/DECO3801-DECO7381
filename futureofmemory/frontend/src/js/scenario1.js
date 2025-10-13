// scenario1.js
import {checkFactionVoting, voteForFaction} from '../api/futureMemoryApi.js';

function getPinFromUrl() {
  const params = new URLSearchParams(window.location.search);
  return params.get('pin');
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

      hideChoices();
      showMessage('Submitting your vote...');

      try {
        const data = await voteForFaction({pin, faction});
        console.log('Vote successful:', data);

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
    });
  });

  // Poll every 5 seconds
  setInterval(() => pollVotingStatus(pin), 5000);
});
