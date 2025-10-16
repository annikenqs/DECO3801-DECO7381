import {checkFactionVoting, voteForFaction} from '../api/futureMemoryApi.js';

const FINAL_SHOW_MS = 3000; // how long to show the final faction before navigating

function getPinFromUrl() {
  const params = new URLSearchParams(window.location.search);
  return params.get('pin');
}

/* ===================== Loading Overlay ===================== */
function ensureOverlay() {
  let overlay = document.getElementById('loading-overlay');
  if (!overlay) {
    overlay = document.createElement('div');
    overlay.id = 'loading-overlay';
    overlay.className = 'loading is-hidden';
    overlay.setAttribute('role', 'status');
    overlay.setAttribute('aria-live', 'polite');
    overlay.innerHTML = `
      <div class="loading-box">
        <div class="spinner" aria-hidden="true"></div>
        <p id="loading-text">Submitting your vote...</p>
      </div>`;
    document.body.appendChild(overlay);
  }
  return overlay;
}

function setLoading(text = 'Loading…') {
  const overlay = ensureOverlay();
  const textEl = overlay.querySelector('#loading-text');
  if (textEl) textEl.textContent = text;
  overlay.classList.remove('is-hidden');
  document.body.classList.add('is-loading');
  document.body.setAttribute('aria-busy', 'true');
}

function clearLoading() {
  const overlay = document.getElementById('loading-overlay');
  if (overlay) overlay.classList.add('is-hidden');
  document.body.classList.remove('is-loading');
  document.body.removeAttribute('aria-busy');
}
/* =========================================================== */

function formatFaction(f) {
  if (!f) return '';
  const map = {
    rightists: 'Rightists',
    responsibilists: 'Responsibilists',
    resourceists: 'Resourceists',
  };
  return map[f.toLowerCase()] || f;
}

function showFinalAndNavigate(pin, faction) {
  const nice = formatFaction(faction);
  setLoading(`Final faction: ${nice}`);
  showMessage(`Final faction: ${nice}`);
  setTimeout(() => {
    goToNextPage(pin);
  }, FINAL_SHOW_MS);
}

/* ----------------- Poll vote status ----------------- */
async function pollVotingStatus(pin) {
  try {
    const status = await checkFactionVoting({pin});
    console.log('[Polling] Faction vote status:', status);

    if (status.allVoted && status.faction) {
      showFinalAndNavigate(pin, status.faction);
    }
  } catch (err) {
    console.warn('[Polling] Failed to check faction voting:', err?.message || err);
  }
}

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

function goToNextPage(pin) {
  const url = new URL('GeneralScenario.html', window.location.href);
  url.searchParams.set('pin', pin);
  location.href = url.toString();
}

/* ----------------------- main ----------------------- */
document.addEventListener('DOMContentLoaded', () => {
  const choices = document.querySelectorAll('.choice');
  const pin = getPinFromUrl();

  ensureOverlay();

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
      setLoading('Submitting your vote...');

      try {
        const data = await voteForFaction({pin, faction});
        console.log('Vote successful:', data);

        if (data?.allVoted && data?.faction) {
          // Everyone already finished
          showFinalAndNavigate(pin, data.faction);
        } else {
          showMessage('Waiting for other people to vote...');
          setLoading('Waiting for other people to vote...');
        }
      } catch (err) {
        console.error('Vote failed:', err);
        clearLoading();
        showMessage('An error occurred. Please try again.');
        showChoices();
      }
    });
  });

  // Poll every 5 seconds
  setInterval(() => pollVotingStatus(pin), 5000);
});
