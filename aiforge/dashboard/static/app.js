// AIForge dashboard — vanilla JS, no frameworks. Talks to the /api REST layer.
const api = {
  async get(path) {
    const r = await fetch(path, { headers: authHeaders() });
    if (!r.ok) throw new Error(`${r.status}`);
    return r.json();
  },
  async post(path, body) {
    const r = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify(body || {}),
    });
    return r.json();
  },
};

function authHeaders() {
  const t = localStorage.getItem("aiforge_token");
  return t ? { Authorization: "Bearer " + t } : {};
}

const el = (id) => document.getElementById(id);
const esc = (s) => String(s).replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));

// ---- Navigation ----
const titles = {
  chat: "Live Execution", agents: "Agent Explorer", tools: "Tool Manager",
  memory: "Memory Viewer", timeline: "Execution Timeline", logs: "Logs",
  analytics: "Analytics", settings: "Settings",
};
document.querySelectorAll(".nav-item").forEach((btn) => {
  btn.addEventListener("click", () => switchView(btn.dataset.view));
});
function switchView(view) {
  document.querySelectorAll(".nav-item").forEach((b) => b.classList.toggle("active", b.dataset.view === view));
  document.querySelectorAll(".view").forEach((v) => v.classList.remove("active"));
  el("view-" + view).classList.add("active");
  el("view-title").textContent = titles[view];
  loaders[view] && loaders[view]();
}

// ---- Chat / Live execution ----
el("chat-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const text = el("chat-text").value.trim();
  const agent = el("agent-select").value;
  if (!text || !agent) return;
  addMsg("user", "you", text);
  el("chat-text").value = "";
  const thinking = addMsg("agent", agent, "…");
  try {
    const res = await api.post(`/api/agents/${agent}/run`, { input: text });
    thinking.querySelector(".body").textContent = res.output ?? res.error ?? "(no output)";
  } catch (err) {
    thinking.querySelector(".body").textContent = "Error: " + err.message;
  }
});
function addMsg(cls, who, body) {
  const div = document.createElement("div");
  div.className = "msg " + cls;
  div.innerHTML = `<div class="who">${esc(who)}</div><div class="body">${esc(body)}</div>`;
  el("chat-window").appendChild(div);
  el("chat-window").scrollTop = el("chat-window").scrollHeight;
  return div;
}

// ---- Loaders per view ----
const loaders = {
  async chat() {
    const { agents } = await api.get("/api/agents");
    const sel = el("agent-select");
    const current = sel.value;
    sel.innerHTML = agents.map((a) => `<option value="${esc(a.name)}">${esc(a.name)} (${esc(a.role)})</option>`).join("");
    if (!agents.length) sel.innerHTML = `<option value="">— create an agent first —</option>`;
    if (current) sel.value = current;
  },
  async agents() {
    const { agents } = await api.get("/api/agents");
    const { templates } = await api.get("/api/templates");
    el("template-select").innerHTML = templates.map((t) => `<option>${esc(t)}</option>`).join("");
    el("agents-list").innerHTML = agents.length
      ? agents.map(agentCard).join("")
      : `<p class="muted">No agents yet. Create one from a template above.</p>`;
  },
  async tools() {
    const { tools } = await api.get("/api/tools");
    el("tools-list").innerHTML = tools.map((t) => {
      const fn = t.function || t;
      return `<div class="card"><h3>${esc(fn.name)}</h3><p>${esc(fn.description || "")}</p>
        <div class="tags">${Object.keys((fn.parameters || {}).properties || {}).map((p) => `<span class="tag">${esc(p)}</span>`).join("")}</div></div>`;
    }).join("");
  },
  async memory() {
    const stats = await api.get("/api/memory/stats");
    el("memory-stats").innerHTML = Object.entries(stats).map(([k, v]) => `<span class="tag">${esc(k)}: ${v}</span>`).join("");
  },
  async timeline() {
    const { timeline } = await api.get("/api/timeline?limit=120");
    el("timeline-list").innerHTML = timeline.slice().reverse().map((e) => {
      const t = new Date(e.timestamp * 1000).toLocaleTimeString();
      return `<div class="event"><span class="src">${esc(t)}</span><span class="type">${esc(e.type)}</span>
        <span class="data">${esc(JSON.stringify(e.data))}</span></div>`;
    }).join("") || `<p class="muted">No events yet.</p>`;
  },
  async logs() {
    const { logs } = await api.get("/api/logs");
    el("logs-box").textContent = logs.map((l) => `[${new Date((l.timestamp || 0) * 1000).toLocaleTimeString()}] ${l.type}  ${JSON.stringify(l.data || {})}`).join("\n") || "No logs.";
  },
  async analytics() {
    const snap = await api.get("/api/metrics");
    const m = snap.metrics || {};
    const stats = [
      ["LLM calls", m["llm.calls"] || 0],
      ["Total tokens", m["tokens.total"] || 0],
      ["Tool calls", m["tools.calls"] || 0],
      ["Errors", m["errors.total"] || 0],
    ];
    el("stat-grid").innerHTML = stats.map(([label, value]) =>
      `<div class="stat"><div class="value">${value}</div><div class="label">${label}</div></div>`).join("");
    const usage = snap.tool_usage || {};
    const max = Math.max(1, ...Object.values(usage));
    el("tool-usage").innerHTML = Object.entries(usage).map(([name, n]) =>
      `<div class="bar"><span class="name">${esc(name)}</span><span class="track"><span class="fill" style="width:${(n / max) * 100}%"></span></span><span class="num">${n}</span></div>`).join("") || `<p class="muted">No tool usage yet.</p>`;
  },
  async settings() {
    const status = await api.get("/api/status");
    el("settings-box").textContent = JSON.stringify(status, null, 2);
  },
};

function agentCard(a) {
  return `<div class="card"><span class="role">${esc(a.role)}</span><h3>${esc(a.name)}</h3>
    <p>${esc(a.description || a.system_prompt || "")}</p>
    <div class="tags">${(a.tools || []).map((t) => `<span class="tag">${esc(t)}</span>`).join("")}</div></div>`;
}

el("create-agent").addEventListener("click", async () => {
  const template = el("template-select").value;
  await api.post("/api/agents", { template });
  loaders.agents();
});
el("memory-search").addEventListener("click", async () => {
  const q = el("memory-query").value.trim();
  const { results } = await api.get("/api/memory?query=" + encodeURIComponent(q));
  el("memory-list").innerHTML = results.map((r) =>
    `<div class="card"><span class="role">${esc(r.kind)} · ${r.score.toFixed(3)}</span><p>${esc(r.content)}</p></div>`).join("") || `<p class="muted">No matches.</p>`;
});

// ---- Connection status + boot ----
async function ping() {
  try {
    await api.get("/api/health");
    const { providers } = await api.get("/api/providers");
    el("conn").textContent = "● connected";
    el("conn").style.color = "var(--ok)";
    el("provider-pill").textContent = "provider: " + (providers[0] || "—");
  } catch {
    el("conn").textContent = "● disconnected";
    el("conn").style.color = "var(--err)";
  }
}
ping();
setInterval(ping, 5000);
switchView("chat");
