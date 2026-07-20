import { useEffect, useState } from "react";
import { api } from "../api.js";

const COPY = {
  automations: ["Automations", "Saved crews you can run on a schedule or via an event trigger."],
  skills: ["Skills Repository", "Reusable capabilities agents can compose — coming online as you add them."],
  traces: ["Traces", "Every crew run, step by step, with token usage and timing."],
  connections: ["LLM Connections", "Configure providers. AIForge is provider-agnostic — mock, OpenAI, Anthropic."],
  settings: ["Settings", "Workspace configuration: sandbox, limits, secrets, and defaults."],
};

export function Placeholder({ view }) {
  const [title, lead] = COPY[view] || ["AIForge", "A modular framework for autonomous agent crews."];
  return (
    <div className="page">
      <h1>{title}</h1>
      <p className="lead">{lead}</p>
      <div className="grid">
        {[1, 2, 3].map((i) => (
          <div className="tile" key={i}>
            <div className="k">Module</div>
            <h3>{title} · {i}</h3>
            <p>Configured through the AIForge engine and surfaced here in the Studio.</p>
          </div>
        ))}
      </div>
    </div>
  );
}

export function AgentsPage() {
  const [templates, setTemplates] = useState([]);
  useEffect(() => {
    api.templates().then((d) => setTemplates(d.templates || [])).catch(() => {});
  }, []);
  return (
    <div className="page">
      <h1>Agents Repository</h1>
      <p className="lead">
        Ready-made agent templates. Drop one into a crew or start from scratch in the Studio.
      </p>
      <div className="grid">
        {templates.map((t) => (
          <div className="tile" key={t}>
            <div className="k">Template</div>
            <h3>{t.replace(/_/g, " ")}</h3>
            <p>A pre-configured agent with a role, system prompt, and scoped tools.</p>
          </div>
        ))}
      </div>
    </div>
  );
}

export function ToolsPage() {
  const [catalog, setCatalog] = useState({});
  useEffect(() => {
    api.toolCatalog().then((d) => setCatalog(d.categories || {})).catch(() => {});
  }, []);
  return (
    <div className="page">
      <h1>Tools &amp; Integrations</h1>
      <p className="lead">The tools your agents can call, grouped by domain. Everything runs locally and safely by default.</p>
      {Object.entries(catalog).map(([cat, tools]) =>
        tools.length ? (
          <div key={cat} style={{ marginBottom: 26 }}>
            <div className="k" style={{ color: "var(--ember)", fontFamily: "var(--font-mono)", fontSize: 11, letterSpacing: "0.1em", textTransform: "uppercase", marginBottom: 12 }}>
              {cat}
            </div>
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

export function UsagePage() {
  const [metrics, setMetrics] = useState({});
  useEffect(() => {
    api.metrics().then((d) => setMetrics(d.metrics || {})).catch(() => {});
  }, []);
  const stats = [
    ["LLM calls", metrics["llm.calls"] || 0],
    ["Total tokens", metrics["tokens.total"] || 0],
    ["Tool calls", metrics["tools.calls"] || 0],
    ["Errors", metrics["errors.total"] || 0],
  ];
  return (
    <div className="page">
      <h1>Usage</h1>
      <p className="lead">Live metrics collected from the event bus across every crew run.</p>
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
