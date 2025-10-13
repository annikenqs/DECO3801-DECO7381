import {getScenario, sendChoice} from '../api/futureMemoryApi.js';

const TOTAL_STEPS = 10;

const START_YEAR = 2075;

const progressEl = document.getElementById('progress');
const scenarioEl = document.getElementById('scenarioText');
const optionsUl = document.getElementById('options');

let pin = null;
let stepIndex = 0;
let scenarioId = null;
let isSubmitting = false;
// Calculation year & progress display
const yearOf = (i) => START_YEAR + i;
const setProgress = (i) => {
  progressEl.textContent = `YEAR ${yearOf(i)}`;
};

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
function disableChoices(disabled) {
  Array.from(optionsUl.querySelectorAll('button.option')).forEach((b) => (b.disabled = !!disabled));
}

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

async function advanceWithChoice(choiceId) {
  if (!pin || !scenarioId || isSubmitting) return;
  isSubmitting = true;
  disableChoices(true);

  try {
    // Send the player's choice; backend generates the next scenario & updates year
    const resp = await sendChoice({pin, scenarioId, choiceId});

    // Some backends return the new current scenario directly; others wrap it
    const next = resp?.nextScenario || resp;

    if (next && (next.id || next.scenarioId || next.text)) {
      stepIndex += 1;
      renderScenarioAndChoices(next);
    } else {
      stepIndex += 1;
      await loadStep(stepIndex);
    }
    // eslint-disable-next-line no-unused-vars
  } catch (_err) {
    // Keep UI experience moving even on error
    stepIndex += 1;
    await loadStep(stepIndex);
  } finally {
    isSubmitting = false;
    disableChoices(false);
  }
}

optionsUl.addEventListener('click', (ev) => {
  const btn = ev.target.closest('button.option');
  if (!btn) return;

  const cid = btn.dataset.choiceId;
  advanceWithChoice(cid);
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
