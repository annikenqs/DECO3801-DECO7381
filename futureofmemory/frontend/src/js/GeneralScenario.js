import {
  getScenario,
  castScenarioVote,
  getVoteStatus,
  getNextScenario,
  getCurrentScenario,
} from '../api/futureMemoryApi.js';

const START_YEAR = 2075;
const TOTAL_STEPS = 10;
const letters = ['A', 'B', 'C'];

const progressEl = document.getElementById('progress');
const scenarioEl = document.getElementById('scenarioText');
const optionsUl = document.getElementById('options');

// --- Fullscreen overlay refs ---
const overlayEl = document.getElementById('loadingOverlay');
const overlayText = overlayEl?.querySelector('.loading-text');

function showOverlay(msg = 'Loading…') {
  if (overlayText) overlayText.textContent = msg;
  if (overlayEl) overlayEl.hidden = false;
  document.body.classList.add('loading-locked');
}

function hideOverlay() {
  if (overlayEl) overlayEl.hidden = true;
  document.body.classList.remove('loading-locked');
}

let pin = null;
let stepIndex = 0;
let scenarioId = null;

// year & progress
const yearOf = (i) => START_YEAR + i;
const setProgress = (iOrYear) => {
  if (typeof iOrYear === 'number' && iOrYear >= 1900) {
    progressEl.textContent = `YEAR ${iOrYear}`;
  } else {
    progressEl.textContent = `YEAR ${yearOf(iOrYear)}`;
  }
};

// ---------- Voting & polling ----------
async function submitVoteAndPoll({pin, scenarioId, choice, onTick, onDone}) {
  try {
    await castScenarioVote({pin, scenarioId, choice});
  } catch (e) {
    console.error('vote failed', e);
    onTick?.({error: e.message || String(e)});
    return;
  }
  const intervalMs = 1500;
  const t = setInterval(async () => {
    try {
      const s = await getVoteStatus({pin, scenarioId});
      onTick?.(s);
      if (s.persisted) {
        clearInterval(t);
        onDone?.(s);
      }
    } catch (e) {
      console.warn('status poll failed', e);
      // keep polling
    }
  }, intervalMs);
}

// ---------- Rendering ----------
function renderOptions(choices) {
  optionsUl.innerHTML = '';
  (choices || []).slice(0, 3).forEach((c, idx) => {
    const letter = c?.id ?? letters[idx] ?? 'A';
    const label = c?.label ?? `Option ${letter}`;
    const li = document.createElement('li');
    const btn = document.createElement('button');
    btn.className = 'option';
    btn.dataset.id = letter;
    btn.textContent = label.startsWith(`${letter}:`)
      ? label
      : `${letter}: ${label.replace(/^Option\s+[ABC]\s*[-—:]\s*/i, '')}`;
    li.appendChild(btn);
    optionsUl.appendChild(li);
  });
}

function getPinFromUrl() {
  const qsPin = new URLSearchParams(window.location.search).get('pin');
  if (!qsPin) throw new Error('No PIN in URL (?pin=...).');
  return qsPin;
}

function renderScenarioAndChoices(s) {
  scenarioId = s?.id ?? s?.scenarioId ?? null;
  const text = s?.text ?? s?.content ?? 'No scenario text.';
  scenarioEl.textContent = text;

  if (typeof s?.year === 'number') setProgress(s.year);
  else setProgress(stepIndex);

  const choices = Array.isArray(s?.choices) ? s.choices.slice(0, 3) : [];
  optionsUl.innerHTML = '';

  choices.forEach((c, idx) => {
    const li = document.createElement('li');
    const btn = document.createElement('button');
    btn.className = 'option';
    btn.dataset.choiceId = c.id;
    const letter = letters[idx] || 'A';
    const label = c.text ?? c.label ?? `Option ${letter}`;
    btn.textContent = `${letter}: ${label}`.replace(/^([ABC]):\s*/, '$1: ');
    li.appendChild(btn);
    optionsUl.appendChild(li);
  });

  return {hasChoices: choices.length > 0};
}

// When choices is empty, short polling is conducted until ready
async function pollUntilChoicesReady({pin, maxMs = 20000, intervalMs = 1200}) {
  const start = Date.now();
  while (Date.now() - start < maxMs) {
    try {
      const s = await getCurrentScenario({pin});
      const has = Array.isArray(s?.choices) && s.choices.length > 0;
      if (has) {
        renderScenarioAndChoices(s);
        return true;
      }
    } catch {
      /* silent */
    }
    await new Promise((r) => setTimeout(r, intervalMs));
  }
  return false;
}

async function loadStep(i) {
  stepIndex = i;

  if (stepIndex >= TOTAL_STEPS) {
    setProgress(TOTAL_STEPS - 1);
    scenarioEl.textContent = 'The decade concludes. (End)';
    renderOptions([]);
    hideOverlay();
    return;
  }

  // Enter the generation stage: Display a full-screen mask
  showOverlay('Fate is not given — it is constructed…');
  scenarioEl.textContent = 'Fetching scenario from server...';
  renderOptions([
    {id: 'A', label: 'A: Fetching option from server...'},
    {id: 'B', label: 'B: Fetching option from server...'},
    {id: 'C', label: 'C: Fetching option from server...'},
  ]);
  setProgress(stepIndex);

  try {
    // 1. Read the existing scene first
    const s = await getCurrentScenario({pin});
    const {hasChoices} = renderScenarioAndChoices(s);

    if (!hasChoices) {
      showOverlay('Generating choices…');
      const ok = await pollUntilChoicesReady({pin});
      if (!ok) {
        scenarioEl.textContent = 'Choices are still being prepared. Please try again shortly.';
      }
    }
    hideOverlay();
  } catch (err) {
    if (err && err.status === 404) {
      // 2. If it does not exist, create it
      try {
        showOverlay('Fate is not given — it is constructed…');
        const created = await getScenario({pin});
        const {hasChoices} = renderScenarioAndChoices(created);

        if (!hasChoices) {
          showOverlay('Generating choices…');
          await pollUntilChoicesReady({pin});
        }
        hideOverlay();
      } catch (inner) {
        console.error('[loadStep] POST /scenario failed', inner);
        scenarioEl.textContent = 'Backend unavailable; showing placeholder.';
        renderOptions([
          {id: 'A', label: 'A'},
          {id: 'B', label: 'B'},
          {id: 'C', label: 'C'},
        ]);
        hideOverlay();
      }
    } else {
      console.warn('[loadStep] current scenario GET failed', err);
      scenarioEl.textContent = 'Backend unavailable; showing placeholder.';
      renderOptions([
        {id: 'A', label: 'A'},
        {id: 'B', label: 'B'},
        {id: 'C', label: 'C'},
      ]);
      hideOverlay();
    }
  }
}

optionsUl.addEventListener('click', (ev) => {
  const btn = ev.target.closest('button.option');
  if (!btn) return;
  if (scenarioId == null) return;

  const choice = btn.dataset.choiceId;
  if (choice == null) return;

  //  Voting awaits
  optionsUl.querySelectorAll('button.option').forEach((b) => (b.disabled = true));
  scenarioEl.textContent = 'Waiting for others to vote…';

  submitVoteAndPoll({
    pin,
    scenarioId,
    choice,
    onTick: (s) => {
      if (!s || s.error) return;
      if (typeof s.total_votes === 'number' && typeof s.number_of_players === 'number') {
        scenarioEl.textContent = `Waiting… ${s.total_votes}/${s.number_of_players} votes in`;
      }
    },
    onDone: async (final) => {
      scenarioEl.textContent = `Winner: ${final.winnerText || final.winnerId}. Loading next…`;

      // next year
      showOverlay('Fate is not given — it is constructed…');
      try {
        const next = await getNextScenario({pin, previousScenarioId: scenarioId});
        stepIndex += 1;
        const {hasChoices} = renderScenarioAndChoices(next);
        if (!hasChoices) {
          showOverlay('Generating choices…');
          await pollUntilChoicesReady({pin});
        }
      } catch (e) {
        console.error('getNextScenario failed', e);
        scenarioEl.textContent = 'Failed to load next scenario. Retrying…';
      } finally {
        hideOverlay();
        optionsUl.querySelectorAll('button.option').forEach((b) => (b.disabled = false));
      }
    },
  });
});

(async function bootstrap() {
  try {
    pin = getPinFromUrl();
  } catch (e) {
    scenarioEl.textContent = e.message || 'Missing PIN in URL.';
    hideOverlay();
    return;
  }
  await loadStep(0);
})();
