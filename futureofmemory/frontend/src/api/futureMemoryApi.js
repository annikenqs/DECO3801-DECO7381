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

/** ---- Sessions ---- **/

// Create a new game session (PIN can be server-generated; faction/year optional)
export function createSession({faction = 'Unknown', year = 2075, pin} = {}) {
  return request('/session/', {
    method: 'POST',
    body: {faction, year, ...(pin ? {pin} : {})},
  });
}

// Get "The current plot scene to be displayed"
export function getScenario({sessionId}) {
  if (!sessionId) throw new Error('getScenario: sessionId is required');
  return request(`/session/${sessionId}/scenario/`, {
    method: 'POST',
    body: {},
  });
}

// Send the player's choice and get the next scene
export function sendChoice({sessionId, scenarioId, choiceId, idempotencyKey}) {
  if (!sessionId) throw new Error('sendChoice: sessionId is required');
  if (!scenarioId) throw new Error('sendChoice: scenarioId is required');
  if (!choiceId) throw new Error('sendChoice: choiceId is required');
  return request(`/session/${sessionId}/choice/`, {
    method: 'PATCH',
    body: {scenarioId, choiceId},
    headers: idempotencyKey ? {'Idempotency-Key': idempotencyKey} : undefined,
  });
}

// Record the faction selected in scenario1
export function sendFaction({sessionId, faction}) {
  if (!sessionId) throw new Error('sendFaction: sessionId is required');
  if (!['rightists', 'resourceists', 'responsibilists'].includes(faction)) {
    throw new Error('sendFaction: faction must be rightists | resourceists | responsibilists');
  }
  return request(`/session/${sessionId}/faction`, {
    method: 'POST',
    body: {faction},
  });
}
