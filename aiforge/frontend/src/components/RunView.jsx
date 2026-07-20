import { Agent, Task, Tool, Sparkle, Check, Bolt } from "../icons.jsx";

// Map raw event-bus events to a friendly live-trace line.
function describe(ev) {
  const d = ev.data || {};
  switch (ev.type) {
    case "workflow.start":
      return { icon: Bolt, tone: "start", text: `Crew started (${d.process || "sequential"})` };
    case "workflow.step.start":
      return { icon: Task, tone: "task", text: `Task: ${d.task || d.step || ""}`, sub: d.agent };
    case "agent.start":
      return { icon: Agent, tone: "agent", text: `${d.agent} is working…` };
    case "llm.response":
      return {
        icon: Sparkle,
        tone: "llm",
        text: `${d.agent || "model"} responded`,
        sub: d.usage ? `${d.usage.total_tokens} tokens` : "",
      };
    case "tool.start":
      return { icon: Tool, tone: "tool", text: `Tool → ${d.tool}` };
    case "tool.end":
      return { icon: Tool, tone: "tool", text: `Tool ✓ ${d.tool}`, sub: `${(d.duration || 0).toFixed?.(2) || d.duration}s` };
    case "workflow.step.end":
      return { icon: Check, tone: "done", text: `Task complete: ${d.task || d.step || ""}` };
    case "workflow.end":
      return { icon: Check, tone: "done", text: "Crew finished" };
    default:
      return null;
  }
}

export default function RunView({ trace, result, running }) {
  const lines = (trace || []).map(describe).filter(Boolean);

  return (
    <div className="run-view">
      {(running || lines.length > 0) && (
        <>
          <div className="run-status">
            {running ? <span className="spin sm" /> : <span className="done-dot" />}
            <h3>{running ? "Running the crew…" : "Run trace"}</h3>
          </div>
          <div className="trace">
            {lines.map((l, i) => {
              const Icon = l.icon;
              return (
                <div className={`trace-line ${l.tone}`} key={i} style={{ animationDelay: `${Math.min(i, 8) * 30}ms` }}>
                  <span className="tl-ic">
                    <Icon width="13" height="13" />
                  </span>
                  <span className="tl-text">{l.text}</span>
                  {l.sub && <span className="tl-sub">{l.sub}</span>}
                </div>
              );
            })}
            {running && (
              <div className="trace-line pending">
                <span className="tl-ic">
                  <span className="spin sm" />
                </span>
                <span className="tl-text">working…</span>
              </div>
            )}
          </div>
        </>
      )}

      {!running && !result && lines.length === 0 && (
        <div className="empty">
          <div className="big">No run yet</div>
          <p>Press Run to execute the crew. You'll see each task, tool call, and token stream in live — then the results.</p>
        </div>
      )}

      {result && (
        <div className="results">
          <div className="result-summary">
            <span className={`pill-badge ${result.success ? "ok" : "err"}`}>
              {result.success ? "Completed" : "Failed"}
            </span>
            <span className="rs-item">{(result.task_outputs || []).length} tasks</span>
            <span className="rs-item">{(result.duration || 0).toFixed(2)}s</span>
            <span className="rs-item">{result.usage?.total_tokens ?? 0} tokens</span>
            <span className="rs-item cost">${(result.cost_usd ?? 0).toFixed(4)}</span>
            {result.model && <span className="rs-item mono">{result.model}</span>}
          </div>

          {result.error && (
            <div className="task-result">
              <div className="tr-head">
                <span className="tr-name">Error</span>
                <span className="badge err">failed</span>
              </div>
              <div className="out">{result.error}</div>
            </div>
          )}

          {(result.task_outputs || []).map((t, i) => (
            <div className="task-result" key={i} style={{ animationDelay: `${i * 70}ms` }}>
              <div className="tr-head">
                <span className="idx">{String(i + 1).padStart(2, "0")}</span>
                <div>
                  <div className="tr-name">{t.task}</div>
                  <div className="tr-agent">{t.agent}</div>
                </div>
                <span className={`badge ${t.success ? "ok" : "err"}`}>{t.success ? "done" : "failed"}</span>
              </div>
              <div className="out">{String(t.output ?? "")}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
