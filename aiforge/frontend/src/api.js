// Thin API client for the AIForge REST layer.
const TOKEN_KEY = "aiforge_token";

function headers(extra = {}) {
  const token = localStorage.getItem(TOKEN_KEY);
  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...extra,
  };
}

async function get(path) {
  const res = await fetch(path, { headers: headers() });
  if (!res.ok) throw new Error(`GET ${path} -> ${res.status}`);
  return res.json();
}

async function post(path, body) {
  const res = await fetch(path, {
    method: "POST",
    headers: headers(),
    body: JSON.stringify(body || {}),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.message || `POST ${path} -> ${res.status}`);
  return data;
}

async function del(path) {
  const res = await fetch(path, { method: "DELETE", headers: headers() });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.message || `DELETE ${path} -> ${res.status}`);
  return data;
}

// Stream a crew run over SSE (fetch + ReadableStream). Calls onEvent for each
// parsed message: {type:'run.start'|'event'|'run.end'|'run.error', ...}.
async function streamRun(graph, onEvent) {
  const res = await fetch("/api/runs/stream", {
    method: "POST",
    headers: headers(),
    body: JSON.stringify(graph),
  });
  if (!res.ok || !res.body) throw new Error(`stream failed (${res.status})`);
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let sep;
    while ((sep = buffer.indexOf("\n\n")) !== -1) {
      const frame = buffer.slice(0, sep);
      buffer = buffer.slice(sep + 2);
      if (frame.startsWith("data: ")) {
        try {
          onEvent(JSON.parse(frame.slice(6)));
        } catch {
          /* skip malformed frame */
        }
      }
    }
  }
}

export const api = {
  health: () => get("/api/health"),
  status: () => get("/api/status"),
  providers: () => get("/api/providers"),
  connectProvider: (body) => post("/api/providers/connect", body),
  setDefaultProvider: (provider) => post("/api/providers/default", { provider }),
  disconnectProvider: (provider) => post("/api/providers/disconnect", { provider }),
  config: () => get("/api/config"),
  templates: () => get("/api/templates"),
  toolCatalog: () => get("/api/tools/catalog"),
  agents: () => get("/api/agents"),
  metrics: () => get("/api/metrics"),
  runs: (limit = 50) => get(`/api/runs?limit=${limit}`),
  crews: () => get("/api/crews"),
  saveCrew: (name, graph) => post("/api/crews", { name, graph }),
  deleteCrew: (name) => del(`/api/crews/${encodeURIComponent(name)}`),
  studioChat: (message, graph) => post("/api/studio/chat", { message, graph }),
  runCrew: (graph) => post("/api/crew/run", graph),
  streamRun,
  graphCode: (graph) => post("/api/graph/code", graph),
};

export function getApiToken() {
  return localStorage.getItem(TOKEN_KEY) || "";
}
export function setApiToken(value) {
  if (value) localStorage.setItem(TOKEN_KEY, value);
  else localStorage.removeItem(TOKEN_KEY);
}
