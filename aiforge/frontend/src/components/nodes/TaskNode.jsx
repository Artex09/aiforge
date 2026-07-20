import { Handle, Position } from "reactflow";
import { Task, Agent, Edit, Copy } from "../../icons.jsx";
import { useStudio } from "../../studio.js";

export default function TaskNode({ id, data, selected }) {
  const { onEdit, onDuplicate } = useStudio();
  return (
    <div className={`node task ${selected ? "selected" : ""}`}>
      <Handle type="target" position={Position.Top} className="hdl" />
      <div className="node-head">
        <div className="node-ic">
          <Task />
        </div>
        <div>
          <div className="node-kind">Task</div>
          <div className="node-title">{data.label || "Untitled task"}</div>
        </div>
      </div>
      {data.description && <div className="node-desc">{data.description}</div>}
      <div className="node-meta">
        <div className="meta-row">
          <Agent />
          <span className={data.agent ? "" : "unassigned"}>
            {data.agent || "no agent assigned"}
          </span>
        </div>
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
