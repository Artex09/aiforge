import { useCallback, useRef } from "react";
import ReactFlow, {
  Background,
  Controls,
  BackgroundVariant,
  ConnectionLineType,
  MarkerType,
  ReactFlowProvider,
  useReactFlow,
} from "reactflow";
import AgentNode from "./nodes/AgentNode.jsx";
import TaskNode from "./nodes/TaskNode.jsx";
import TriggerNode from "./nodes/TriggerNode.jsx";
import { Layers, ChevronDown } from "../icons.jsx";

const nodeTypes = { agent: AgentNode, task: TaskNode, trigger: TriggerNode };
const edgeOptions = {
  type: "smoothstep",
  markerEnd: { type: MarkerType.ArrowClosed, width: 18, height: 18, color: "#c9a08c" },
  style: { strokeWidth: 2 },
};

let seq = 0;
const nextId = (t) => `${t}-${Date.now()}-${seq++}`;

function ProcessCard({ process }) {
  return (
    <div className="process-card">
      <div className="ver">Version 1</div>
      <h4>Process Type</h4>
      <div className="process-select">
        <span className="pi">
          <Layers width="15" height="15" />
        </span>
        <div>
          <b>{process === "sequential" ? "Sequential" : "Hierarchical"}</b>
          <span>Tasks run in order</span>
        </div>
        <ChevronDown className="chev" width="15" height="15" />
      </div>
    </div>
  );
}

function Flow({
  nodes,
  edges,
  onNodesChange,
  onEdgesChange,
  onConnect,
  onDropNode,
  onNodeClick,
  onPaneClick,
  onNodeContextMenu,
  onPaneContextMenu,
  process,
}) {
  const wrapRef = useRef(null);
  const { screenToFlowPosition } = useReactFlow();

  const onDragOver = useCallback((e) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = "move";
  }, []);

  const onDrop = useCallback(
    (e) => {
      e.preventDefault();
      const raw = e.dataTransfer.getData("application/aiforge");
      if (!raw) return;
      const payload = JSON.parse(raw);
      const position = screenToFlowPosition({ x: e.clientX, y: e.clientY });
      onDropNode({ id: nextId(payload.type), type: payload.type, position, data: payload.data });
    },
    [screenToFlowPosition, onDropNode]
  );

  return (
    <div className="canvas-wrap" ref={wrapRef}>
      <ProcessCard process={process} />
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onDrop={onDrop}
        onDragOver={onDragOver}
        onNodeClick={onNodeClick}
        onPaneClick={onPaneClick}
        onNodeContextMenu={onNodeContextMenu}
        onPaneContextMenu={onPaneContextMenu}
        connectionLineType={ConnectionLineType.SmoothStep}
        connectionRadius={40}
        defaultEdgeOptions={edgeOptions}
        deleteKeyCode={["Backspace", "Delete"]}
        fitView
        fitViewOptions={{ padding: 0.28, maxZoom: 1 }}
        minZoom={0.35}
        maxZoom={1.6}
        proOptions={{ hideAttribution: true }}
      >
        <Background variant={BackgroundVariant.Dots} gap={22} size={1.4} />
        <Controls showInteractive={false} position="bottom-left" />
      </ReactFlow>
    </div>
  );
}

export default function Canvas(props) {
  return (
    <ReactFlowProvider>
      <Flow {...props} />
    </ReactFlowProvider>
  );
}

export { nextId };
