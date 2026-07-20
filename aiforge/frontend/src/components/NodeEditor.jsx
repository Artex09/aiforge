import { Agent, Task, Trigger, Chevron } from "../icons.jsx";

const ROLES = ["assistant", "researcher", "coder", "analyst", "planner", "critic", "router", "executor"];

function Field({ label, children, hint }) {
  return (
    <label className="fld">
      <span className="fld-label">{label}</span>
      {children}
      {hint && <span className="fld-hint">{hint}</span>}
    </label>
  );
}

export default function NodeEditor({ node, agentNames, toolNames, onChange, onDelete, onClose }) {
  const d = node.data || {};
  const set = (patch) => onChange(node.id, patch);
  const Icon = node.type === "agent" ? Agent : node.type === "task" ? Task : Trigger;

  const toggleTool = (t) => {
    const cur = d.tools || [];
    set({ tools: cur.includes(t) ? cur.filter((x) => x !== t) : [...cur, t] });
  };

  return (
    <aside className="inspector">
      <div className="editor-head">
        <button className="back" onClick={onClose}>
          <Chevron width="15" height="15" style={{ transform: "rotate(180deg)" }} />
        </button>
        <span className={`ehead-ic ${node.type}`}>
          <Icon width="15" height="15" />
        </span>
        <div>
          <div className="ehead-kind">{node.type}</div>
          <div className="ehead-title">Edit {node.type}</div>
        </div>
      </div>

      <div className="editor-body">
        {node.type === "agent" && (
          <>
            <Field label="Name">
              <input value={d.name || ""} onChange={(e) => set({ name: e.target.value })} />
            </Field>
            <Field label="Role" hint="Shapes the agent's default behaviour and permissions.">
              <div className="select-wrap">
                <select value={d.role || "assistant"} onChange={(e) => set({ role: e.target.value })}>
                  {ROLES.map((r) => (
                    <option key={r} value={r}>
                      {r}
                    </option>
                  ))}
                </select>
              </div>
            </Field>
            <Field label="Model">
              <input value={d.model || ""} onChange={(e) => set({ model: e.target.value })} placeholder="aiforge-mock-1" />
            </Field>
            <Field label="Instructions" hint="What this agent should do and how.">
              <textarea
                rows={4}
                value={d.system_prompt || ""}
                onChange={(e) => set({ system_prompt: e.target.value })}
              />
            </Field>
            <Field label="Tools">
              <div className="tool-picker">
                {toolNames.map((t) => (
                  <button
                    key={t}
                    className={`pick ${(d.tools || []).includes(t) ? "on" : ""}`}
                    onClick={() => toggleTool(t)}
                    type="button"
                  >
                    {t}
                  </button>
                ))}
              </div>
            </Field>
          </>
        )}

        {node.type === "task" && (
          <>
            <Field label="Title">
              <input value={d.label || ""} onChange={(e) => set({ label: e.target.value })} />
            </Field>
            <Field label="Description" hint="Plain-English instructions for the task.">
              <textarea
                rows={4}
                value={d.description || ""}
                onChange={(e) => set({ description: e.target.value })}
              />
            </Field>
            <Field label="Assigned agent">
              <div className="select-wrap">
                <select value={d.agent || ""} onChange={(e) => set({ agent: e.target.value })}>
                  <option value="">— choose an agent —</option>
                  {agentNames.map((a) => (
                    <option key={a} value={a}>
                      {a}
                    </option>
                  ))}
                </select>
              </div>
            </Field>
            <Field label="Expected output" hint="What a finished task looks like.">
              <textarea
                rows={2}
                value={d.expected_output || ""}
                onChange={(e) => set({ expected_output: e.target.value })}
              />
            </Field>
          </>
        )}

        {node.type === "trigger" && (
          <>
            <Field label="Label">
              <input value={d.label || ""} onChange={(e) => set({ label: e.target.value })} />
            </Field>
            <Field label="Note">
              <input value={d.subtitle || ""} onChange={(e) => set({ subtitle: e.target.value })} />
            </Field>
          </>
        )}

        <button className="delete-btn" onClick={() => onDelete(node.id)}>
          Delete {node.type}
        </button>
      </div>
    </aside>
  );
}
