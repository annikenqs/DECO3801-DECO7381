// - Send faction to backend before jumping to After_*
// - Maintain a persistent sessionId in localStorage

const STORAGE_KEY = 'worldMode';
const SESSION_KEY = 'fmSessionId';
const API_BASE = '/api'; //  If use a Vite proxy, that's fine; If directly cross domains, can change it to the complete backend address

function ensureSession() {
  let sid = localStorage.getItem(SESSION_KEY);
  if (!sid) {
    sid = (self.crypto && crypto.randomUUID && crypto.randomUUID()) || String(Date.now());
    localStorage.setItem(SESSION_KEY, sid);
  }
  return sid;
}

async function sendFaction(sessionId, faction) {
  try {
    const res = await fetch(`${API_BASE}/faction`, {
      method: 'POST',
      headers: {Accept: 'application/json', 'Content-Type': 'application/json'},
      credentials: 'include',
      body: JSON.stringify({sessionId, faction}),
    });

    if (!res.ok) {
      let msg = `HTTP ${res.status}`;
      try {
        const data = await res.json();
        msg = (data && (data.error || data.message)) || msg;
      } catch (err) {
        // ignore saved state parse error
        void err;
      }

      throw new Error(msg);
    }
  } catch (e) {
    // Non-blocking jump: Only warns in the console
    console.warn('sendFaction failed:', e && e.message ? e.message : e);
  }
}

document.addEventListener('DOMContentLoaded', () => {
  const choices = Array.from(document.querySelectorAll('.choice'));

  // mapping next page
  const NEXT_BY_MODE = {
    rightists: 'rightists.html',
    resourceists: 'resourceists.html',
    responsibilists: 'responsibilists.html',
  };

  choices.forEach((btn) => {
    btn.addEventListener('click', async () => {
      // Selected state
      choices.forEach((b) => b.classList.remove('selected'));
      btn.classList.add('selected');

      // save changes (local)
      const mode = btn.dataset.mode;
      localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({mode, decidedAt: new Date().toISOString()})
      );

      // sync to backend (non-blocking)
      const sessionId = ensureSession();
      await sendFaction(sessionId, mode);

      // jump
      const nextUrl = NEXT_BY_MODE[mode];
      if (nextUrl) {
        setTimeout(() => {
          location.href = nextUrl;
        }, 200);
      }
    });
  });

  // Optional: restore previously selected button
  // try {
  //   const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || 'null');
  //   if (saved?.mode) {
  //     const target = document.querySelector(`.choice[data-mode="${saved.mode}"]`);
  //     target?.classList.add('selected');
  //   }
  // } catch {}
});
