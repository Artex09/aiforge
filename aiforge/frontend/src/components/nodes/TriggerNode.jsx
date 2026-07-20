import { Handle, Position } from "reactflow";
import { Trigger } from "../../icons.jsx";

export default function TriggerNode({ data, selected }) {
  return (
    <div className={`node trigger ${selected ? "selected" : ""}`}>
      <div className="node-head">
        <div className="node-ic">
          <Trigger />
        </div>
        <div>
          <div className="node-kind">Trigger</div>
          <div className="node-title">{data.label || "Trigger"}</div>
        </div>
      </div>
      <div className="node-meta">
        <div className="meta-row">
          <span style={{ color: "var(--muted)", fontSize: 11.5 }}>
            {data.subtitle || "Starts the crew"}
          </span>
        </div>
      </div>
      <Handle type="source" position={Position.Bottom} className="hdl" />
    </div>
  );
}
