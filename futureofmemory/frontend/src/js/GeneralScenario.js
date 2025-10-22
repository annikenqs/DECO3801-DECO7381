import {
  getScenario,
  castScenarioVote,
  getVoteStatus,
  getNextScenario,
  getCurrentScenario,
} from '../api/futureMemoryApi.js';

const FMLoading = (() => {
  const el = () => document.getElementById('fm-loading');
  const textEl = () => document.getElementById('fm-loading-text');

  let counter = 0;
  let timeoutId = null;

  const lines = ['Fate is not given — it is constructed...'];

  function pickLine(reason) {
    if (typeof reason === 'string' && reason.trim()) return reason;
    return lines[Math.floor(Math.random() * lines.length)];
  }

  function show(reason) {
    counter++;
    const root = el();
    if (!root) return;
    root.hidden = false;
    const t = textEl();
    if (t) t.textContent = pickLine(reason);
    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => forceHide(), 25000);
  }

  function hide() {
    counter = Math.max(0, counter - 1);
    if (counter === 0) forceHide();
  }

  function forceHide() {
    const root = el();
    if (root) root.hidden = true;
    clearTimeout(timeoutId);
    timeoutId = null;
    counter = 0;
  }

  function setText(msg) {
    const t = textEl();
    if (t && typeof msg === 'string' && msg.trim()) t.textContent = msg;
  }

  return {show, hide, forceHide, setText};
})();

const START_YEAR = 2075;
const TOTAL_STEPS = 10;

const progressEl = document.getElementById('progress');
const scenarioEl = document.getElementById('scenarioText');
const optionsUl = document.getElementById('options');

let pin = null;
let stepIndex = 0;
let scenarioId = null;

let lastChoicesMap = Object.create(null);

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

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

function renderOptions(choices) {
  optionsUl.innerHTML = '';
  (choices || []).slice(0, 3).forEach((c, idx) => {
    const letter = c?.id ?? ['A', 'B', 'C'][idx] ?? 'A';
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

const setLoadingUI = (i) => {
  FMLoading.show('ENTERING 2075...');
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

function renderScenarioAndChoices(s) {
  scenarioId = s?.id ?? s?.scenarioId ?? null;
  const text = s?.text ?? s?.content ?? 'No scenario text.';
  scenarioEl.textContent = text;

  if (typeof s?.year === 'number') {
    progressEl.textContent = `YEAR ${s.year}`;
  }

  lastChoicesMap = Object.create(null);
  const choices = Array.isArray(s?.choices) ? s.choices.slice(0, 3) : [];
  optionsUl.innerHTML = '';

  choices.forEach((c, idx) => {
    const li = document.createElement('li');
    const btn = document.createElement('button');
    btn.className = 'option';

    btn.dataset.choiceId = c.id;
    const letter = letters[idx] || 'A';
    const label = c.text ?? c.label ?? `Option ${letter}`;
    const display = `${letter}: ${label}`.replace(/^([ABC]):\s*/, '$1: ');

    if (c.id != null) lastChoicesMap[c.id] = display;
    lastChoicesMap[letter] = display;

    btn.textContent = display;
    li.appendChild(btn);
    optionsUl.appendChild(li);
  });
}

function showGameFinished() {
  setProgress(TOTAL_STEPS - 1);

  const overlay = document.createElement('div');
  overlay.id = 'game-finished-overlay';
  overlay.innerHTML = `
    <div class="fm-card game-finish-card">
      <p class="finish-title">The world has reached its end of memory</p>
      <button class="option" id="returnHomeBtn">Return to Home</button>
    </div>
  `;
  document.body.appendChild(overlay);

  requestAnimationFrame(() => overlay.classList.add('visible'));

  document.getElementById('returnHomeBtn').onclick = () => {
    window.location.href = '../../index.html';
  };
}

function showFinalYearScene(s) {
  const finalYear = START_YEAR + TOTAL_STEPS;
  const text = s?.text ?? s?.content ?? 'No scenario text.';
  scenarioId = s?.id ?? s?.scenarioId ?? null;

  document.body.classList.add('final-year');

  progressEl.textContent = `YEAR ${s?.year ?? finalYear}`;
  scenarioEl.textContent = text;

  optionsUl.innerHTML = '';
}

async function loadStep(i) {
  stepIndex = i;

  if (stepIndex > TOTAL_STEPS) {
    showGameFinished();
    return;
  }

  setLoadingUI(stepIndex);

  try {
    const s = await getCurrentScenario({pin});
    console.log('[loadStep] got current scenario', s);
    if (!s || !s.id) throw Object.assign(new Error('Empty current scenario'), {status: 404});
    renderScenarioAndChoices(s);
  } catch (err) {
    console.warn('[loadStep] current scenario GET failed', err);
    if (err && err.status === 404) {
      try {
        console.log('[loadStep] creating first scenario via POST …');
        const created = await getScenario({pin});
        console.log('[loadStep] created scenario', created);
        renderScenarioAndChoices(created);
      } catch (inner) {
        console.error('[loadStep] POST /scenario failed', inner);
        scenarioEl.textContent = 'Backend unavailable; showing placeholder.';
        renderOptions([
          {id: 'A', label: 'A'},
          {id: 'B', label: 'B'},
          {id: 'C', label: 'C'},
        ]);
      }
    } else {
      scenarioEl.textContent = 'Backend unavailable; showing placeholder.';
      renderOptions([
        {id: 'A', label: 'A'},
        {id: 'B', label: 'B'},
        {id: 'C', label: 'C'},
      ]);
    }
  } finally {
    FMLoading.hide();
  }
}

optionsUl.addEventListener('click', (ev) => {
  const btn = ev.target.closest('button.option');
  if (!btn) return;
  if (scenarioId == null) return;

  const choice = btn.dataset.choiceId;
  if (choice == null) return;

  optionsUl.querySelectorAll('button.option').forEach((b) => (b.disabled = true));

  // Waiting for others
  FMLoading.show('Waiting for others to vote…');
  scenarioEl.textContent = 'Waiting for others to vote…';

  submitVoteAndPoll({
    pin,
    scenarioId,
    choice,
    onTick: (s) => {
      if (!s || s.error) return;
      const msg = `Waiting… ${s.total_votes}/${s.number_of_players} votes in`;
      scenarioEl.textContent = msg;
      FMLoading.setText(msg);
    },
    onDone: async (final) => {
      // —— final choice ——
      const winnerId =
        final?.winnerId ??
        final?.winner_id ??
        final?.winner ??
        final?.winnerLetter ??
        final?.winner_letter;
      const winnerText =
        final?.winnerText ??
        final?.winner_text ??
        lastChoicesMap[winnerId] ??
        (winnerId ? `Option ${winnerId}` : 'Winner decided');

      const finalMsg = `Final choice: ${winnerText}`;
      scenarioEl.textContent = finalMsg;
      FMLoading.setText(finalMsg);

      await sleep(4000);

      FMLoading.setText('Fate is not given — it is constructed...');
      try {
        const next = await getNextScenario({pin, previousScenarioId: scenarioId});
        stepIndex += 1;

        if (stepIndex === TOTAL_STEPS) {
          showFinalYearScene(next);
          FMLoading.hide();
          setTimeout(() => showGameFinished(), 10000);
          return;
        }

        renderScenarioAndChoices(next);
      } catch (e) {
        console.error('getNextScenario failed', e);
        scenarioEl.textContent = 'Failed to load next scenario. Retrying…';
      } finally {
        optionsUl.querySelectorAll('button.option').forEach((b) => (b.disabled = false));
        FMLoading.hide();
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
