import { useEffect, useState } from "react";
import { api, getApiToken, setApiToken } from "../api.js";
import { Bolt, Check, Flow, Key, Plus, Sparkle, Trash } from "../icons.jsx";

/* ---------------------------------------------------------------- helpers */

function timeAgo(ts) {
  if (!ts) return "";
  const s = Math.max(0, Date.now() / 1000 - ts);
  if (s < 60) return "just now";
  if (s < 3600) return `${Math.floor(s / 60)} min ago`;
  if (s < 86400) return `${Math.floor(s / 3600)} h ago`;
  return `${Math.floor(s / 86400)} d ago`;
}

const fmt = (n) => (typeof n === "number" ? n.toLocaleString() : n ?? 0);

function EmptyState({ icon: Icon, title, children }) {
  return (
    <div className="empty-page">
      <span className="ep-ic">
        <Icon width="22" height="22" />
      </span>
      <div className="big">{title}</div>
      <p>{children}</p>
    </div>
  );
}

/* ------------------------------------------------------- Automations page */
/* Saved crews: load them back onto the canvas, or delete them. */

export function AutomationsPage({ onLoad, notify }) {
  const [crews, setCrews] = useState(null);

  useEffect(() => {
    api.crews().then((d) => setCrews(d.crews || [])).catch(() => setCrews([]));
  }, []);

  const remove = (name) =>
    api
      .deleteCrew(name)
      .then((d) => {
        setCrews(d.crews || []);
        notify(`Deleted “${name}”`);
      })
      .catch((e) => notify("Could not delete: " + e.message));

  return (
    <div className="page">
      <h1>Automations</h1>
      <p className="lead">
        Crews you've saved from the Studio. Open one to keep building — or run it — any time.
      </p>

      {crews && crews.length === 0 && (
        <EmptyState icon={Bolt} title="No saved crews yet">
          Build a crew in the Studio, give it a name in the top bar, and press <b>Save</b>. It will
          appear here, ready to reopen and run.
        </EmptyState>
      )}

      <div className="grid">
        {(crews || []).map((c) => (
          <div className="tile crew-tile" key={c.name}>
            <div className="k">Saved crew</div>
            <h3>{c.name}</h3>
            <p className="mono-sub">
              {c.agents ?? "–"} agents · {c.tasks ?? "–"} tasks · saved {timeAgo(c.saved_at)}
            </p>
            <div className="tile-actions">
              <button className="btn dark sm" onClick={() => onLoad(c.graph, c.name)}>
                <Flow width="13" height="13" /> Open in Studio
              </button>
              <button className="icon-btn danger" title="Delete crew" onClick={() => remove(c.name)}>
                <Trash width="14" height="14" />
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------ Agents page */

export function AgentsPage({ onAddAgent }) {
  const [agents, setAgents] = useState([]);

  useEffect(() => {
    api.templates().then((d) => setAgents(d.agents || [])).catch(() => {});
  }, []);

  return (
    <div className="page">
      <h1>Agents Repository</h1>
      <p className="lead">
        Ready-made agents with a role, instructions, and scoped tools. Add one straight into your
        crew on the canvas.
      </p>
      <div className="grid">
        {agents.map((a) => (
          <div className="tile agent-tile" key={a.name}>
            <div className="tile-top">
              <span className="role-badge">{a.role}</span>
            </div>
            <h3>{a.name.replace(/_/g, " ")}</h3>
            <p>{a.description || a.system_prompt}</p>
            {a.tools?.length > 0 && (
              <div className="chips">
                {a.tools.map((t) => (
                  <span className="chip" key={t}>
                    {t}
                  </span>
                ))}
              </div>
            )}
            <div className="tile-actions">
              <button
                className="btn subtle sm"
                onClick={() =>
                  onAddAgent({
                    name: a.name
                      .replace(/_/g, " ")
                      .replace(/\b\w/g, (ch) => ch.toUpperCase()),
                    role: a.role,
                    model: "",
                    system_prompt: a.system_prompt || a.description || "",
                    tools: a.tools || [],
                  })
                }
              >
                <Plus width="13" height="13" /> Add to Studio
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------- Tools page */

export function ToolsPage() {
  const [catalog, setCatalog] = useState({});
  useEffect(() => {
    api.toolCatalog().then((d) => setCatalog(d.categories || {})).catch(() => {});
  }, []);
  return (
    <div className="page">
      <h1>Tools &amp; Integrations</h1>
      <p className="lead">
        The tools your agents can call, grouped by domain. Everything runs locally, sandboxed, and
        deny-by-default.
      </p>
      {Object.entries(catalog).map(([cat, tools]) =>
        tools.length ? (
          <div key={cat} style={{ marginBottom: 26 }}>
            <div className="cat-label">{cat}</div>
            <div className="grid">
              {tools.map((t) => {
                const fn = t.function || t;
                return (
                  <div className="tile" key={fn.name}>
                    <h3 style={{ fontFamily: "var(--font-mono)", fontSize: 15 }}>{fn.name}</h3>
                    <p>{fn.description}</p>
                  </div>
                );
              })}
            </div>
          </div>
        ) : null
      )}
    </div>
  );
}

/* ------------------------------------------------------------ Traces page */

export function TracesPage() {
  const [runs, setRuns] = useState(null);
  const [open, setOpen] = useState(null);

  useEffect(() => {
    api.runs(100).then((d) => setRuns(d.runs || [])).catch(() => setRuns([]));
  }, []);

  return (
    <div className="page">
      <h1>Traces</h1>
      <p className="lead">Every crew run — status, tasks, tokens, and cost. Newest first.</p>

      {runs && runs.length === 0 && (
        <EmptyState icon={Sparkle} title="No runs yet">
          Run a crew from the Studio and its full trace will be recorded here.
        </EmptyState>
      )}

      {runs && runs.length > 0 && (
        <div className="runs-table">
          <div className="rt-row rt-head">
            <span />
            <span>Crew</span>
            <span>Tasks</span>
            <span>Tokens</span>
            <span>Cost</span>
            <span>Duration</span>
            <span>Model</span>
            <span>When</span>
          </div>
          {runs.map((r) => (
            <div key={r.id}>
              <button
                className={`rt-row ${open === r.id ? "open" : ""}`}
                onClick={() => setOpen(open === r.id ? null : r.id)}
              >
                <span className={`run-dot ${r.success ? "ok" : "err"}`} />
                <span className="rt-name">{r.name || "crew"}</span>
                <span>{r.tasks?.length ?? 0}</span>
                <span>{fmt(r.tokens)}</span>
                <span className="mono">${(r.cost_usd ?? 0).toFixed(4)}</span>
                <span>{(r.duration ?? 0).toFixed(2)}s</span>
                <span className="mono rt-model">{r.model || "—"}</span>
                <span className="rt-when">{timeAgo(r.timestamp)}</span>
              </button>
              {open === r.id && (
                <div className="rt-detail">
                  {r.error && <div className="rt-error">{r.error}</div>}
                  {(r.tasks || []).map((t, i) => (
                    <div className="rt-task" key={i}>
                      <span className={`run-dot sm ${t.success ? "ok" : "err"}`} />
                      <span className="rt-task-name">{t.task}</span>
                      <span className="rt-task-agent">{t.agent}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------- LLM Connections page */

const PROVIDERS = [
  {
    id: "openai",
    label: "OpenAI",
    blurb: "GPT models — or any OpenAI-compatible endpoint via a custom base URL.",
    models: ["gpt-4o-mini", "gpt-4o", "gpt-4.1-mini", "gpt-4.1"],
    env: "OPENAI_API_KEY",
    hasBaseUrl: true,
  },
  {
    id: "anthropic",
    label: "Anthropic",
    blurb: "Claude models via the Anthropic API.",
    models: ["claude-fable-5", "claude-opus-4-8", "claude-sonnet-5", "claude-haiku-4-5-20251001"],
    env: "ANTHROPIC_API_KEY",
  },
];

function ProviderCard({ meta, info, refresh, notify }) {
  const connected = info?.providers?.includes(meta.id);
  const isDefault = info?.default === meta.id;
  const current = info?.detail?.find((d) => d.name === meta.id);
  const [key, setKey] = useState("");
  const [model, setModel] = useState("");
  const [baseUrl, setBaseUrl] = useState("");
  const [busy, setBusy] = useState(false);

  const connect = async () => {
    if (!key.trim() && !connected) {
      notify("Paste an API key first");
      return;
    }
    setBusy(true);
    try {
      const d = await api.connectProvider({
        provider: meta.id,
        api_key: key.trim() || undefined,
        model: model.trim() || undefined,
        base_url: baseUrl.trim() || undefined,
        make_default: true,
      });
      refresh(d);
      setKey("");
      notify(`${meta.label} connected — it's now the default provider`);
    } catch (e) {
      notify("Could not connect: " + e.message);
    } finally {
      setBusy(false);
    }
  };

  const makeDefault = () =>
    api
      .setDefaultProvider(meta.id)
      .then((d) => {
        refresh(d);
        notify(`${meta.label} is now the default provider`);
      })
      .catch((e) => notify(e.message));

  const disconnect = () =>
    api
      .disconnectProvider(meta.id)
      .then((d) => {
        refresh(d);
        notify(`${meta.label} disconnected`);
      })
      .catch((e) => notify(e.message));

  return (
    <div className={`conn-card ${connected ? "connected" : ""}`}>
      <div className="conn-head">
        <h3>{meta.label}</h3>
        {isDefault ? (
          <span className="pill-badge ok">default</span>
        ) : connected ? (
          <span className="pill-badge">connected</span>
        ) : (
          <span className="pill-badge off">not connected</span>
        )}
      </div>
      <p>{meta.blurb}</p>

      {connected && (
        <div className="conn-current mono">
          model · {current?.model || "—"}
        </div>
      )}

      <label className="fld">
        <span className="fld-label">API key</span>
        <div className="key-input">
          <Key width="14" height="14" />
          <input
            type="password"
            placeholder={connected ? "•••••••• (already set — paste to replace)" : "sk-…"}
            value={key}
            onChange={(e) => setKey(e.target.value)}
            autoComplete="off"
          />
        </div>
        <span className="fld-hint">
          Kept in the engine's memory only — never written to disk, never shown again. You can also
          set the <code>{meta.env}</code> environment variable before launching.
        </span>
      </label>

      <label className="fld">
        <span className="fld-label">Model</span>
        <input
          list={`models-${meta.id}`}
          placeholder={meta.models[0]}
          value={model}
          onChange={(e) => setModel(e.target.value)}
        />
        <datalist id={`models-${meta.id}`}>
          {meta.models.map((m) => (
            <option key={m} value={m} />
          ))}
        </datalist>
      </label>

      {meta.hasBaseUrl && (
        <label className="fld">
          <span className="fld-label">Base URL (optional)</span>
          <input
            placeholder="https://api.openai.com/v1"
            value={baseUrl}
            onChange={(e) => setBaseUrl(e.target.value)}
          />
        </label>
      )}

      <div className="conn-actions">
        <button className="btn dark sm" onClick={connect} disabled={busy}>
          {busy ? <span className="spin sm" /> : <Check width="13" height="13" />}
          {connected ? "Update" : "Connect"}
        </button>
        {connected && !isDefault && (
          <button className="btn subtle sm" onClick={makeDefault}>
            Use as default
          </button>
        )}
        {connected && (
          <button className="btn subtle sm danger-text" onClick={disconnect}>
            Disconnect
          </button>
        )}
      </div>
    </div>
  );
}

export function ConnectionsPage({ info, refresh, notify }) {
  const mockDefault = info?.default === "mock";
  return (
    <div className="page">
      <h1>LLM Connections</h1>
      <p className="lead">
        AIForge is provider-agnostic. Connect a real model here — or stay on the built-in mock,
        which runs offline and free.
      </p>

      <div className="conn-grid">
        {PROVIDERS.map((p) => (
          <ProviderCard key={p.id} meta={p} info={info} refresh={refresh} notify={notify} />
        ))}

        <div className={`conn-card mock ${mockDefault ? "connected" : ""}`}>
          <div className="conn-head">
            <h3>Mock</h3>
            {mockDefault ? (
              <span className="pill-badge ok">default</span>
            ) : (
              <span className="pill-badge">built-in</span>
            )}
          </div>
          <p>
            The offline provider. Deterministic, costs nothing, needs no key — perfect for building
            and testing crews before pointing them at a paid model.
          </p>
          {!mockDefault && (
            <div className="conn-actions">
              <button
                className="btn subtle sm"
                onClick={() =>
                  api.setDefaultProvider("mock").then((d) => {
                    refresh(d);
                    notify("Mock is now the default provider");
                  })
                }
              >
                Use as default
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------- Usage page */

export function UsagePage() {
  const [metrics, setMetrics] = useState({});
  const [runs, setRuns] = useState([]);
  useEffect(() => {
    api.metrics().then((d) => setMetrics(d.metrics || {})).catch(() => {});
    api.runs(500).then((d) => setRuns(d.runs || [])).catch(() => {});
  }, []);
  const cost = runs.reduce((s, r) => s + (r.cost_usd || 0), 0);
  const stats = [
    ["Crew runs", runs.length],
    ["LLM calls", fmt(metrics["llm.calls"] || 0)],
    ["Total tokens", fmt(metrics["tokens.total"] || 0)],
    ["Tool calls", fmt(metrics["tools.calls"] || 0)],
    ["Errors", fmt(metrics["errors.total"] || 0)],
    ["Total cost", `$${cost.toFixed(4)}`],
  ];
  return (
    <div className="page">
      <h1>Usage</h1>
      <p className="lead">Live metrics from the event bus, plus totals across recorded runs.</p>
      <div className="stat-row">
        {stats.map(([l, n]) => (
          <div className="stat" key={l}>
            <div className="n">{n}</div>
            <div className="l">{l}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ---------------------------------------------------------- Settings page */

const CONFIG_SECTIONS = [
  ["provider", "Provider", "Default provider and model settings the engine boots with."],
  ["security", "Security", "Sandbox root, execution limits, and the shell/network policy."],
  ["storage", "Storage", "Where runs, memory, and saved crews are persisted."],
  ["api", "API", "Host and port for this server, and allowed CORS origins."],
];

export function SettingsPage({ notify }) {
  const [config, setConfig] = useState(null);
  const [token, setToken] = useState(getApiToken());

  useEffect(() => {
    api.config().then((d) => setConfig(d.config || {})).catch(() => setConfig({}));
  }, []);

  const saveToken = () => {
    setApiToken(token.trim());
    notify(token.trim() ? "API token saved in this browser" : "API token cleared");
  };

  const resetCanvas = () => {
    localStorage.removeItem("aiforge_studio_graph");
    notify("Studio canvas reset — reopen the Studio to start fresh");
  };

  return (
    <div className="page">
      <h1>Settings</h1>
      <p className="lead">
        Workspace configuration. Values come from <code>aiforge.json</code> /{" "}
        <code>AIFORGE_*</code> environment variables and are read-only here.
      </p>

      <div className="settings-card">
        <h3>API token</h3>
        <p>
          Sent as a <code>Bearer</code> header with every request. Only needed when the server is
          started with <code>api.auth_token</code> set. Stored in this browser only.
        </p>
        <div className="token-row">
          <input
            type="password"
            placeholder="paste token…"
            value={token}
            onChange={(e) => setToken(e.target.value)}
            autoComplete="off"
          />
          <button className="btn dark sm" onClick={saveToken}>
            Save
          </button>
        </div>
      </div>

      {config &&
        CONFIG_SECTIONS.map(([key, title, blurb]) => {
          const section = config[key];
          if (!section) return null;
          return (
            <div className="settings-card" key={key}>
              <h3>{title}</h3>
              <p>{blurb}</p>
              <div className="cfg-rows">
                {Object.entries(section).map(([k, v]) => (
                  <div className="cfg-row" key={k}>
                    <span className="cfg-key">{k}</span>
                    <span className="cfg-val mono">
                      {typeof v === "object" ? JSON.stringify(v) : String(v)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          );
        })}

      <div className="settings-card danger-zone">
        <h3>Reset Studio canvas</h3>
        <p>Clears the locally saved canvas (nodes and edges). Saved crews are not affected.</p>
        <button className="btn subtle sm danger-text" onClick={resetCanvas}>
          <Trash width="13" height="13" /> Reset canvas
        </button>
      </div>
    </div>
  );
}
