import {
  getScenario,
  castScenarioVote,
  getVoteStatus,
  getNextScenario,
} from '../api/futureMemoryApi.js';

const START_YEAR = 2075;
const TOTAL_STEPS = 10;

const progressEl = document.getElementById('progress');
const scenarioEl = document.getElementById('scenarioText');
const optionsUl = document.getElementById('options');

let pin = null;
let stepIndex = 0;
let scenarioId = null;
// Calculation year & progress display
const yearOf = (i) => START_YEAR + i;
const setProgress = (i) => {
  progressEl.textContent = `YEAR ${yearOf(i)}`;
};

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

// Render three lines of the "Text Button" option (used for placeholders / loading)
function renderOptions(choices) {
  optionsUl.innerHTML = '';
  (choices || []).slice(0, 3).forEach((c, idx) => {
    const letter = c?.id ?? ['A', 'B', 'C'][idx] ?? 'A';
    const label = c?.label ?? `Option ${letter}`;
    const li = document.createElement('li');
    const btn = document.createElement('button');
    btn.className = 'option';
    btn.dataset.id = letter;
    // Guarantee the prefix is “A: … / B: … / C: …”
    btn.textContent = label.startsWith(`${letter}:`)
      ? label
      : `${letter}: ${label.replace(/^Option\s+[ABC]\s*[-—:]\s*/i, '')}`;
    li.appendChild(btn);
    optionsUl.appendChild(li);
  });
}

// Set the loading state
const setLoadingUI = (i) => {
  scenarioEl.textContent = 'Fetching scenario from server...';
  renderOptions([
    {id: 'A', label: 'A: Fetching option from server...'},
    {id: 'B', label: 'B: Fetching option from server...'},
    {id: 'C', label: 'C: Fetching option from server...'},
  ]);
  setProgress(i);
};

function getPinFromUrl() {
  const qsPin = new URLSearchParams(window.location.search).get('pin');
  if (!qsPin) throw new Error('No PIN in URL (?pin=...).');
  return qsPin;
}

const letters = ['A', 'B', 'C'];

// Render the scenario/choices from backend
function renderScenarioAndChoices(s) {
  scenarioId = s?.id ?? s?.scenarioId ?? null;
  const text = s?.text ?? s?.content ?? 'No scenario text.';
  scenarioEl.textContent = text;

  // If backend provides year, show it; otherwise UI already shows year via setProgress(stepIndex)
  if (typeof s?.year === 'number') {
    progressEl.textContent = `YEAR ${s.year}`;
  }

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
}

async function loadStep(i) {
  stepIndex = i;

  if (stepIndex >= TOTAL_STEPS) {
    setProgress(TOTAL_STEPS - 1);
    scenarioEl.textContent = 'The decade concludes. (End)';
    renderOptions([]);
    return;
  }

  setLoadingUI(stepIndex);

  try {
    // Server requires status === 'in-progress' already; otherwise this may 403
    const s = await getScenario({pin}); // your helper has a long timeout
    if (!s) throw new Error('Empty scenario.');
    renderScenarioAndChoices(s);
    // eslint-disable-next-line no-unused-vars
  } catch (_err) {
    // Fallback placeholder to keep presentation going
    scenarioEl.textContent = `Backend unavailable; showing placeholder.`;
    renderOptions([
      {id: 'A', label: 'A'},
      {id: 'B', label: 'B'},
      {id: 'C', label: 'C'},
    ]);
  }
}

optionsUl.addEventListener('click', (ev) => {
  const btn = ev.target.closest('button.option');
  if (!btn) return;
  if (scenarioId == null) return;

  const choice = btn.dataset.choiceId;
  if (choice == null) return;

  // Disable while waiting
  optionsUl.querySelectorAll('button.option').forEach((b) => (b.disabled = true));
  scenarioEl.textContent = 'Waiting for others to vote…';

  submitVoteAndPoll({
    pin,
    scenarioId,
    choice,
    onTick: (s) => {
      if (!s || s.error) return;
      scenarioEl.textContent = `Waiting… ${s.total_votes}/${s.number_of_players} votes in`;
    },
    onDone: async (final) => {
      scenarioEl.textContent = `Winner: ${final.winnerText || final.winnerId}. Loading next…`;
      try {
        const next = await getNextScenario({pin, previousScenarioId: scenarioId});
        // bump the step and render the newly stored scenario
        stepIndex += 1;
        renderScenarioAndChoices(next);
      } catch (e) {
        console.error('getNextScenario failed', e);
        // fall back to retrying the same step or showing a message
        scenarioEl.textContent = 'Failed to load next scenario. Retrying…';
      } finally {
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
    return;
  }
  await loadStep(0);
})();
