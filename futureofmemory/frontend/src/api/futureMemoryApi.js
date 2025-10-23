// Overwriting is allowed through Vite environment variables or global variables; Otherwise, default '/api'
const API_BASE =
  (typeof window !== 'undefined' && window.__API_BASE__) ||
  import.meta.env?.VITE_API_BASE ||
  '/api';

// Generic helper for making HTTP requests to the backend
export async function request(
  path,
  {method = 'GET', query, body, timeoutMs = 10000, headers = {}} = {}
) {
  const url = new URL(`${API_BASE}${path}`, window.location.origin);
  // Append query parameters if provided
  if (query) {
    Object.entries(query).forEach(
      ([k, v]) => v !== undefined && url.searchParams.set(k, String(v))
    );
  }
  // Setup timeout controller for long-running requests
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  let res;
  try {
    // Perform fetch request with JSON support
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
  // Try to parse JSON response (ignore if not JSON)
  let data = null;
  try {
    data = await res.json();
  } catch (err) {
    /* ignore non-JSON response */
    void err; // avoid no-unused-vars/no-empty
  }
  // Handle non-OK HTTP status responses
  if (!res.ok) {
    const msg = (data && (data.error || data.message)) || `HTTP ${res.status}`;
    const e = new Error(msg);
    e.status = res.status;
    e.details = data || null;
    throw e;
  }
  return data;
}
// Create a new game session
export function createSession({faction = 'Unknown', year = 2075, pin} = {}) {
  return request('/session/', {
    method: 'POST',
    body: {faction, year, ...(pin ? {pin} : {})},
  });
}
// Join an existing session using PIN
export function joinSession({pin}) {
  if (!pin) throw new Error('joinSession: pin is required');
  return request('/session/join/', {method: 'POST', body: {pin}});
}
// Get the current number of players in a session
export function getPlayerCount({pin}) {
  if (!pin) throw new Error('getPlayerCount: pin is required');
  return request(`/session/${pin}/players/count/`, {method: 'GET'});
}
// Update the current game state (e.g., "waiting", "in-progress")
export function updateGameStatus({pin, status}) {
  if (!pin) throw new Error('updateGameStatus: pin is required');
  if (!status) throw new Error('updateGameStatus: status is required');
  return request(`/session/${pin}/state/`, {method: 'PATCH', body: {status}});
}
// Shortcut to start the game
export function startGame({pin}) {
  return updateGameStatus({pin, status: 'in-progress'});
}
// Submit a player’s faction vote
export function voteForFaction({pin, faction}) {
  if (!pin) throw new Error('voteForFaction: pin is required');
  if (!faction) throw new Error('voteForFaction: faction is required');

  return request(`/session/${pin}/faction/vote/`, {
    method: 'POST',
    body: {faction},
  });
}
// Check current faction voting results
export function checkFactionVoting({pin}) {
  if (!pin) throw new Error('checkFactionVoting: pin is required');
  return request(`/session/${pin}/faction/result/`, {method: 'GET'});
}
// Get current game state (status, phase, etc.)
export function getGameState({pin}) {
  if (!pin) throw new Error('getGameState: pin is required');
  return request(`/session/${pin}/state/`, {method: 'GET'});
}

// Create a new scenario for the session
export function getScenario({pin, timeoutMs = 120000}) {
  if (!pin) throw new Error('getScenario: pin is required');
  return request(`/session/${pin}/scenario/`, {
    method: 'POST',
    body: {},
    timeoutMs,
  });
}
// Retrieve the next scenario based on the previous one
export function getNextScenario({pin, previousScenarioId, timeoutMs = 120000}) {
  if (!pin) throw new Error('getNextScenario: pin is required');
  if (previousScenarioId == null)
    throw new Error('getNextScenario: previousScenarioId is required');
  return request(`/session/${pin}/scenario/next/`, {
    method: 'POST',
    body: {previousScenarioId: Number(previousScenarioId)},
    timeoutMs,
  });
}
// Retrieve the current scenario (without creating a new one)
export function getCurrentScenario({pin, timeoutMs = 12000}) {
  if (!pin) throw new Error('getCurrentScenario: pin is required');
  return request(`/session/${pin}/scenario/current/`, {
    method: 'GET',
    timeoutMs,
  });
}
// Helper to convert letter (A/B/C) to choice ID number
const letterToId = (x) => ({A: 1, B: 2, C: 3})[String(x).toUpperCase()] ?? Number(x);
// Cast a player’s choice vote within a scenario
export function castScenarioVote({pin, scenarioId, choice}) {
  return request(`/session/${pin}/vote/`, {
    method: 'PATCH',
    body: {scenarioId: Number(scenarioId), choiceId: letterToId(choice)},
  });
}
// Get current voting progress and status for a scenario
export function getVoteStatus({pin, scenarioId}) {
  return request(`/session/${pin}/votes/status/`, {
    method: 'GET',
    query: {scenarioId: Number(scenarioId)},
  });
}
