import { Handle, Position } from "reactflow";
import { Agent, Model, Tool, Edit, Copy } from "../../icons.jsx";
import { useStudio } from "../../studio.js";

export default function AgentNode({ id, data, selected }) {
  const tools = data.tools || [];
  const { onEdit, onDuplicate, onDelete } = useStudio();
  return (
    <div className={`node agent ${selected ? "selected" : ""}`}>
      <Handle type="target" position={Position.Top} className="hdl" />
      <div className="node-head">
        <div className="node-ic">
          <Agent />
        </div>
        <div>
          <div className="node-kind">Agent</div>
          <div className="node-title">{data.name || "Untitled agent"}</div>
        </div>
      </div>
      {data.system_prompt && <div className="node-desc">{data.system_prompt}</div>}
      <div className="node-meta">
        <div className="meta-row">
          <Model />
          <span className="mono">{data.model || "aiforge-mock-1"}</span>
        </div>
        {tools.slice(0, 3).map((t) => (
          <div className="meta-row" key={t}>
            <Tool />
            <span>{t}</span>
          </div>
        ))}
        {tools.length > 3 && (
          <div className="meta-row">
            <Tool />
            <span>+{tools.length - 3} more tools</span>
          </div>
        )}
      </div>
      <div className="node-foot">
        <button title="Edit" onClick={() => onEdit(id)}>
          <Edit width="15" height="15" />
        </button>
        <button title="Duplicate" onClick={() => onDuplicate(id)}>
          <Copy width="15" height="15" />
        </button>
        <span className="foot-hint">drag ● to connect</span>
      </div>
      <Handle type="source" position={Position.Bottom} className="hdl" />
    </div>
  );
}
