import {checkFactionVoting, voteForFaction} from '../api/futureMemoryApi.js';

// Handles the display and hiding of the loading overlay during votes or fetches
const FMLoading = (() => {
  const root = () => document.getElementById('fm-loading');
  const text = () => document.getElementById('fm-loading-text');
  let n = 0,
    timer = null;

  // Show loading overlay with optional message
  function show(msg) {
    n++;
    const el = root();
    if (!el) return;
    el.hidden = false;
    if (msg && text()) text().innerHTML = msg;
    clearTimeout(timer);
    timer = setTimeout(forceHide, 25000);
  }
  // Change text while overlay is visible
  function setText(msg) {
    const el = text();
    if (el && msg != null) el.innerHTML = msg;
  }
  // Hide one instance of overlay
  function hide() {
    n = Math.max(0, n - 1);
    if (n === 0) forceHide();
  }
  // Force hide the overlay and reset state
  function forceHide() {
    const el = root();
    if (el) el.hidden = true;
    clearTimeout(timer);
    timer = null;
    n = 0;
  }
  return {show, hide, setText, forceHide};
})();
// Time delay before moving to next scene
const FINAL_HOLD_MS = 4000; // The "Final Camp" section in Loading displays the dwell time
// Get the session PIN from the URL query string
function getPinFromUrl() {
  const params = new URLSearchParams(window.location.search);
  return params.get('pin');
}

// Poll backend to check if all players have voted
async function pollVotingStatus(pin) {
  try {
    const status = await checkFactionVoting({pin});
    console.log('[Polling] Faction vote status:', status);

    const votes = status?.total_votes ?? status?.votesIn ?? null;
    const players = status?.number_of_players ?? status?.totalPlayers ?? null;
    if (votes != null && players != null) {
      FMLoading.setText(`Waiting… ${votes}/${players} votes in`);
    }

    if (status.allVoted && status.faction) {
      const factionKey = String(status.faction || '').toLowerCase();
      const finalTextLoading = `Final faction: <span class="final-faction ${factionKey}">${formatFaction(status.faction)}</span>`;
      FMLoading.setText(finalTextLoading);

      showMessage(`Final faction: ${formatFaction(status.faction)}`);

      await sleep(FINAL_HOLD_MS);
      FMLoading.setText('Branching the timeline…');
      goToNextPage(pin);
    }
  } catch (err) {
    console.warn('[Polling] Failed to check faction voting:', err?.message || err);
  }
}

// Hide all voting choice buttons
function hideChoices() {
  document.querySelectorAll('.choice').forEach((btn) => (btn.style.display = 'none'));
}
// Show all voting choice buttons
function showChoices() {
  document.querySelectorAll('.choice').forEach((btn) => (btn.style.display = 'grid'));
}
// Display a status or result message in the center of the page
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

// Format faction names for display
function formatFaction(f) {
  const map = {
    rightists: 'Rightists',
    responsibilists: 'Responsibilists',
    resourceists: 'Resourceists',
  };
  return map[f] ?? String(f);
}

// Navigate to next page (GeneralScenario.html) with same PIN
function goToNextPage(pin) {
  const url = new URL('GeneralScenario.html', window.location.href);
  url.searchParams.set('pin', pin);
  setTimeout(() => {
    location.href = url.toString();
  }, 300);
}

// Delay helper function
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// --- main ---
document.addEventListener('DOMContentLoaded', () => {
  const choices = document.querySelectorAll('.choice');
  const pin = getPinFromUrl();

  // Stop if no valid session PIN found
  if (!pin) {
    showMessage('Error: no PIN found in URL.');
    return;
  }

  // Handle vote button click
  choices.forEach((btn) => {
    btn.addEventListener('click', async () => {
      const faction = btn.dataset.mode;
      choices.forEach((b) => b.classList.remove('selected'));
      btn.classList.add('selected');

      hideChoices();
      showMessage('Submitting your vote...');
      FMLoading.show('Submitting your vote…');

      try {
        // Send vote to backend
        const data = await voteForFaction({pin, faction});
        console.log('Vote successful:', data);

        // Update waiting message after voting
        const votes = data?.total_votes ?? data?.votesIn ?? null;
        const players = data?.number_of_players ?? data?.totalPlayers ?? null;
        if (votes != null && players != null) {
          const msg = `Waiting… ${votes}/${players} votes in`;
          showMessage(msg);
          FMLoading.setText(msg);
        } else {
          showMessage('Waiting for other people to vote...');
          FMLoading.setText('Waiting for others to vote…');
        }

        // The result has already been produced at the backend
        if (data.allVoted && data.faction) {
          const factionKey = String(data.faction || '').toLowerCase();
          const finalTextLoading = `Final faction: <span class="final-faction ${factionKey}">${formatFaction(data.faction)}</span>`;
          showMessage(`Final faction: ${formatFaction(data.faction)}`);
          FMLoading.setText(finalTextLoading);
          await sleep(FINAL_HOLD_MS);
          FMLoading.setText('Branching the timeline…');
          goToNextPage(pin);
          return;
        }
      } catch (err) {
        console.error('Vote failed:', err);
        FMLoading.forceHide();
        showMessage('An error occurred. Please try again.');
        showChoices();
        return;
      }
    });
  });

  // Re-check voting status every 5 seconds
  setInterval(() => pin && pollVotingStatus(pin), 5000);
});
