//Determine the "root path" of all requests
const API_BASE =
  (typeof import.meta !== "undefined" && import.meta.env && import.meta.env.VITE_API_BASE) ||
  "/api";

async function request(path, { method = "GET", query, body, timeoutMs = 10000, headers = {} } = {}) {
  const url = new URL(`${API_BASE}${path}`, window.location.origin);
  if (query) Object.entries(query).forEach(([k, v]) => v !== undefined && url.searchParams.set(k, String(v)));

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  const res = await fetch(url.toString(), {
    method,
    headers: {
      Accept: "application/json",
      ...(body ? { "Content-Type": "application/json" } : {}),
      ...headers,
    },
    body: body ? JSON.stringify(body) : undefined,
    signal: controller.signal,
    credentials: "include",
  }).catch((err) => {
    clearTimeout(timer);
    if (err.name === "AbortError") throw new Error("Request timed out");
    throw err;
  });

  clearTimeout(timer);

  let data = null;
  try {
    data = await res.json();
  } catch {}

  if (!res.ok) {
    const msg = (data && (data.error || data.message)) || `HTTP ${res.status}`;
    const e = new Error(msg);
    e.status = res.status;
    e.details = data || null;
    throw e;
  }
  return data;
}

//Get "The current plot scene to be displayed"
export function getScenario({ sessionId }) {
  if (!sessionId) throw new Error("getScenario: sessionId is required");
  return request("/scenario", { query: { sessionId } });
}

//Obtain the list of options (button text, etc.) for a certain scenario
export function getChoices({ sessionId, scenarioId }) {
  if (!sessionId) throw new Error("getChoices: sessionId is required");
  if (!scenarioId) throw new Error("getChoices: scenarioId is required");
  return request("/choices", { query: { sessionId, scenarioId } });
}

//Send the player's choices in the current scene to the backend and obtain the next scene (to advance the plot)
export function sendChoice({ sessionId, scenarioId, choiceId, idempotencyKey }) {
  if (!sessionId) throw new Error("sendChoice: sessionId is required");
  if (!scenarioId) throw new Error("sendChoice: scenarioId is required");
  if (!choiceId) throw new Error("sendChoice: choiceId is required");
  return request("/choice", {
    method: "POST",
    body: { sessionId, scenarioId, choiceId },
    headers: idempotencyKey ? { "Idempotency-Key": idempotencyKey } : undefined,
  });
}

//Record the faction chosen by the player (use it in scenario1)
export function sendFaction({ sessionId, faction }) {
  if (!sessionId) throw new Error("sendFaction: sessionId is required");
  if (!["rightists", "resourceists", "responsibilists"].includes(faction)) {
    throw new Error("sendFaction: faction must be rightists | resourceists | responsibilists");
  }
  return request("/faction", { method: "POST", body: { sessionId, faction } });
}
