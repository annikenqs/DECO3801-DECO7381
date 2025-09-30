// Adapt API：createSession/getScenario/sendChoice（From ../api/FutureMemoryApi.js）
import {
  createSession,
  getScenario,
  sendChoice,
} from '../api/FutureMemoryApi.js';

(() => {
  const TOTAL_STEPS = 10;     // 2075..2084
  const START_YEAR = 2075;
  const SESSION_KEY = 'fmSessionId';

  const progressEl = document.getElementById('progress');
  const scenarioEl = document.getElementById('scenarioText');
  const optionsUl = document.getElementById('options');
  const restartBtn = document.getElementById('restartBtn');

  //  Generate simple idempotent keys
  const mkId = () =>
    (self.crypto && crypto.randomUUID && crypto.randomUUID()) ||
    `id_${Date.now()}_${Math.random().toString(16).slice(2)}`;

  // local storage session
  const getSession = () => localStorage.getItem(SESSION_KEY);
  const setSession = (sid) => localStorage.setItem(SESSION_KEY, sid);
  const clearSession = () => localStorage.removeItem(SESSION_KEY);

  // Calculation year & progress display
  const yearOf = (i) => START_YEAR + i;
  const setProgress = (i) => { progressEl.textContent = `YEAR ${yearOf(i)}`; };

  // Set the loading state
  const setLoadingUI = (i) => {
    scenarioEl.textContent = 'Fetching scenario from server...';
    renderOptions([
      { id: 'A', label: 'A: Fetching option from server...' },
      { id: 'B', label: 'B: Fetching option from server...' },
      { id: 'C', label: 'C: Fetching option from server...' },
    ]);
    setProgress(i);
  };

  // Render three lines of the "Text Button" option
  function renderOptions(choices) {
    optionsUl.innerHTML = '';
    (choices || []).slice(0, 3).forEach((c, idx) => {
      const letter = c?.id ?? ['A','B','C'][idx] ?? 'A';
      const label = c?.label ?? `Option ${letter}`;
      const li = document.createElement('li');
      const btn = document.createElement('button');
      btn.className = 'option';
      btn.dataset.id = letter;
      //A,B,C(Guarantee prefix)
      btn.textContent = label.startsWith(`${letter}:`) ? label : `${letter}: ${label.replace(/^Option\s+[ABC]\s*[-—:]\s*/i, '')}`;
      li.appendChild(btn);
      optionsUl.appendChild(li);
    });
  }

  // Status
  let sessionId = null;
  let stepIndex = 0;    // 0..9
  let scenarioId = null;

  async function ensureSession() {
    sessionId = getSession();
    if (!sessionId) {
      const resp = await createSession();
      sessionId = resp?.sessionId || resp?.id;
      if (!sessionId) throw new Error('createSession: no sessionId');
      setSession(sessionId);
    }
    return sessionId;
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
      // defined getScenario({sessionId})：POST /session/{sid}/scenario/
      const s = await getScenario({ sessionId });

      // Year
      if (typeof s?.year === 'number') {
        progressEl.textContent = `YEAR ${s.year}`;
      }

      // Scenario
      scenarioId = s?.scenarioId || s?.id || null;
      const text = s?.text || s?.content || 'No scenario text.';
      scenarioEl.textContent = text;

      // Option
      const mapped = Array.isArray(s?.choices)
        ? s.choices.map((c, idx) => ({
            id: c.id ?? ['A','B','C'][idx],
            label: (c.label && /^[ABC]:/.test(c.label))
              ? c.label
              : `${['A','B','C'][idx]}: ${c.label ?? `Option ${['A','B','C'][idx]}`}`,
          }))
        : null;

      if (mapped && mapped.length) {
        renderOptions(mapped);
      }
    } catch (e) {
      // When the backend fails, use demonstrable placeholder copy
      scenarioEl.textContent = `Year ${yearOf(stepIndex)}. Backend unavailable; showing placeholder.`;
      renderOptions([
        { id: 'A', label: 'A' },
        { id: 'B', label: 'B' },
        { id: 'C', label: 'C' },
      ]);
    }
  }

  async function handleOption(letter) {
    if (!sessionId || !scenarioId) return;

    try {
      // defined sendChoice：PATCH /session/{sid}/choice/  body:{scenarioId, choiceId}
      const resp = await sendChoice({
        sessionId,
        scenarioId,
        choiceId: letter,
        idempotencyKey: mkId(),
      });

      //  If nextScenario is returned, it can be displayed directly; Otherwise, proceed to the next step and pull again
      const next = resp?.nextScenario || resp?.scenario || null;
      if (next && (next.text || next.scenarioId)) {
        scenarioId = next.scenarioId || next.id || scenarioId;
        scenarioEl.textContent = next.text || 'No text.';
        setProgress(stepIndex + 1);
        const nextChoices = Array.isArray(next.choices)
          ? next.choices.map((c, idx) => ({
              id: c.id ?? ['A','B','C'][idx],
              label: (c.label && /^[ABC]:/.test(c.label))
                ? c.label
                : `${['A','B','C'][idx]}: ${c.label ?? `Option ${['A','B','C'][idx]}`}`,
            }))
          : null;
        if (nextChoices && nextChoices.length) renderOptions(nextChoices);
        stepIndex += 1;
      } else {
        await loadStep(stepIndex + 1);
      }
    } catch (e) {
      //  Failure also allows for progress, ensuring that the presentation is not interrupted
      await loadStep(stepIndex + 1);
    }
  }

  // （Click on any line“A: …/B: …/C: …”）
  optionsUl.addEventListener('click', (ev) => {
    const btn = ev.target.closest('.option');
    if (!btn) return;
    handleOption(btn.dataset.id || 'A');
  });


  async function bootstrap() {
    try {
      await ensureSession();
      await loadStep(0);
    } catch (e) {
      scenarioEl.textContent = `Init failed: ${e?.message || e}`;
    }
  }

  bootstrap();
})();
