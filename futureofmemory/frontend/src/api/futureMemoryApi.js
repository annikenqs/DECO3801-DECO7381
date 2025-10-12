// Overwriting is allowed through Vite environment variables or global variables; Otherwise, default '/api'
const API_BASE =
  (typeof window !== 'undefined' && window.__API_BASE__) ||
  import.meta.env?.VITE_API_BASE ||
  '/api';

export async function request(
  path,
  {method = 'GET', query, body, timeoutMs = 10000, headers = {}} = {}
) {
  const url = new URL(`${API_BASE}${path}`, window.location.origin);
  if (query) {
    Object.entries(query).forEach(
      ([k, v]) => v !== undefined && url.searchParams.set(k, String(v))
    );
  }

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  let res;
  try {
    res = await fetch(url.toString(), {
      method,
      headers: {
        Accept: 'application/json',
        ...(body ? {'Content-Type': 'application/json'} : {}),
        ...headers,
      },
      body: body ? JSON.stringify(body) : undefined,
      signal: controller.signal,
      credentials: 'include',
    });
  } catch (err) {
    clearTimeout(timer);
    if (err.name === 'AbortError') throw new Error('Request timed out');
    throw err;
  } finally {
    clearTimeout(timer);
  }

  let data = null;
  try {
    data = await res.json();
  } catch (err) {
    /* ignore non-JSON response */
    void err; // avoid no-unused-vars/no-empty
  }

  if (!res.ok) {
    const msg = (data && (data.error || data.message)) || `HTTP ${res.status}`;
    const e = new Error(msg);
    e.status = res.status;
    e.details = data || null;
    throw e;
  }
  return data;
}

export function createSession({faction = 'Unknown', year = 2075, pin} = {}) {
  return request('/session/', {method: 'POST', body: {faction, year, ...(pin ? {pin} : {})}});
}

export function joinSession({pin}) {
  if (!pin) throw new Error('joinSession: pin is required');
  return request('/session/join/', {method: 'POST', body: {pin}});
}

export function updateGameStatus({pin, status}) {
  if (!pin) throw new Error('updateGameStatus: pin is required');
  if (!status) throw new Error('updateGameStatus: status is required');
  return request(`/session/${pin}/state/`, {method: 'PATCH', body: {status}});
}

export function startGame({pin}) {
  return updateGameStatus({pin, status: 'in-progress'});
}

export function setFaction({pin, faction}) {
  if (!pin) throw new Error('setFaction: pin is required');
  if (!['rightists', 'resourceists', 'responsibilists'].includes(faction)) {
    throw new Error('setFaction: faction must be rightists | resourceists | responsibilists');
  }
  return request(`/session/${pin}/faction/`, {method: 'POST', body: {faction}});
}

// Scenario (server requires status === 'in-progress')
export function getScenario({pin, timeoutMs = 60000}) {
  if (!pin) throw new Error('getScenario: pin is required');
  return request(`/session/${pin}/scenario/`, {
    method: 'POST',
    body: {},
    timeoutMs,
  });
}

export function sendChoice({pin, scenarioId, choiceId, idempotencyKey}) {
  if (!pin) throw new Error('sendChoice: pin is required');
  if (scenarioId == null) throw new Error('sendChoice: scenarioId is required');
  if (choiceId == null) throw new Error('sendChoice: choiceId is required');
  return request(`/session/${pin}/choice/`, {
    method: 'PATCH',
    body: {scenarioId, choiceId},
    headers: idempotencyKey ? {'Idempotency-Key': idempotencyKey} : undefined,
  });
}
