import { useCallback, useEffect, useMemo, useState } from "react";
import { addEdge, applyEdgeChanges, applyNodeChanges } from "reactflow";
import Sidebar from "./components/Sidebar.jsx";
import StudioChat from "./components/StudioChat.jsx";
import Topbar from "./components/Topbar.jsx";
import Canvas, { nextId } from "./components/Canvas.jsx";
import Inspector from "./components/Inspector.jsx";
import NodeEditor from "./components/NodeEditor.jsx";
import RunView from "./components/RunView.jsx";
import ContextMenu from "./components/ContextMenu.jsx";
import Modal from "./components/Modal.jsx";
import { AgentsPage, ToolsPage, UsagePage, Placeholder } from "./components/Pages.jsx";
import { StudioContext } from "./studio.js";
import { api } from "./api.js";

const START_NODES = [
  { id: "trigger-1", type: "trigger", position: { x: 60, y: 250 }, data: { label: "Trigger", subtitle: "Manual run" } },
  {
    id: "agent-1",
    type: "agent",
    position: { x: 360, y: 60 },
    data: {
      name: "Research Specialist",
      role: "researcher",
      model: "aiforge-mock-1",
      system_prompt: "Gather comprehensive, reliable information about the topic.",
      tools: ["web_search", "http_request", "summarize_text"],
    },
  },
  {
    id: "task-1",
    type: "task",
    position: { x: 700, y: 120 },
    data: {
      label: "Research the topic",
      description: "Conduct in-depth research using web and document tools.",
      agent: "Research Specialist",
      expected_output: "A structured set of findings.",
    },
  },
  {
    id: "task-2",
    type: "task",
    position: { x: 700, y: 380 },
    data: {
      label: "Write the report",
      description: "Write a clear report from the research findings.",
      agent: "Research Specialist",
      expected_output: "A finished report.",
    },
  },
];
const START_EDGES = [
  { id: "e1", source: "trigger-1", target: "task-1", type: "smoothstep" },
  { id: "e2", source: "task-1", target: "task-2", type: "smoothstep" },
];
const STORE_KEY = "aiforge_studio_graph";

function loadStored() {
  try {
    const g = JSON.parse(localStorage.getItem(STORE_KEY) || "null");
    if (g?.nodes?.length) return g;
  } catch {
    /* ignore */
  }
  return { nodes: START_NODES, edges: START_EDGES };
}

export default function App() {
  const stored = loadStored();
  const [view, setView] = useState("crew-studio");
  const [tab, setTab] = useState("canvas");
  const [nodes, setNodes] = useState(stored.nodes);
  const [edges, setEdges] = useState(stored.edges);
  const [process] = useState("sequential");
  const [running, setRunning] = useState(false);
  const [trace, setTrace] = useState([]);
  const [result, setResult] = useState(null);
  const [connected, setConnected] = useState(false);
  const [provider, setProvider] = useState("mock");
  const [toast, setToast] = useState(null);
  const [selectedId, setSelectedId] = useState(null);
  const [catalog, setCatalog] = useState({});
  const [menu, setMenu] = useState(null);
  const [modal, setModal] = useState(null); // 'variables' | 'code'
  const [inputs, setInputs] = useState([{ key: "topic", value: "" }]);
  const [code, setCode] = useState("");

  const notify = useCallback((msg) => {
    setToast(msg);
    setTimeout(() => setToast(null), 2200);
  }, []);

  useEffect(() => {
    let alive = true;
    const ping = () =>
      api
        .providers()
        .then((d) => {
          if (!alive) return;
          setConnected(true);
          setProvider(d.providers?.[0] || "mock");
        })
        .catch(() => alive && setConnected(false));
    ping();
    api.toolCatalog().then((d) => alive && setCatalog(d.categories || {})).catch(() => {});
    const t = setInterval(ping, 5000);
    return () => {
      alive = false;
      clearInterval(t);
    };
  }, []);

  useEffect(() => {
    try {
      localStorage.setItem(STORE_KEY, JSON.stringify({ nodes, edges }));
    } catch {
      /* ignore */
    }
  }, [nodes, edges]);

  const toolNames = useMemo(
    () => Object.values(catalog).flat().map((t) => t.function?.name || t.name).filter(Boolean),
    [catalog]
  );
  const agentNames = useMemo(
    () => nodes.filter((n) => n.type === "agent").map((n) => n.data.name).filter(Boolean),
    [nodes]
  );
  const selectedNode = nodes.find((n) => n.id === selectedId) || null;

  const onNodesChange = useCallback((c) => setNodes((nds) => applyNodeChanges(c, nds)), []);
  const onEdgesChange = useCallback((c) => setEdges((eds) => applyEdgeChanges(c, eds)), []);
  const onConnect = useCallback((params) => {
    setEdges((eds) => addEdge({ ...params, type: "smoothstep" }, eds));
  }, []);

  const addNode = useCallback((type, data) => {
    const node = { id: nextId(type), type, position: { x: 430 + Math.random() * 120, y: 150 + Math.random() * 160 }, data };
    setNodes((nds) => [...nds, node]);
    setSelectedId(node.id);
  }, []);
  const onDropNode = useCallback((node) => setNodes((nds) => [...nds, node]), []);

  const updateNodeData = useCallback((id, patch) => {
    setNodes((nds) => nds.map((n) => (n.id === id ? { ...n, data: { ...n.data, ...patch } } : n)));
  }, []);
  const deleteNode = useCallback((id) => {
    setNodes((nds) => nds.filter((n) => n.id !== id));
    setEdges((eds) => eds.filter((e) => e.source !== id && e.target !== id));
    setSelectedId((s) => (s === id ? null : s));
  }, []);
  const duplicateNode = useCallback((id) => {
    setNodes((nds) => {
      const src = nds.find((n) => n.id === id);
      if (!src) return nds;
      const data = { ...src.data };
      if (src.type === "agent" && data.name) data.name = `${data.name} copy`;
      const clone = {
        id: nextId(src.type),
        type: src.type,
        position: { x: src.position.x + 46, y: src.position.y + 46 },
        data,
      };
      return [...nds, clone];
    });
  }, []);

  const studioActions = useMemo(
    () => ({ onEdit: (id) => setSelectedId(id), onDuplicate: duplicateNode, onDelete: deleteNode }),
    [duplicateNode, deleteNode]
  );

  const applyGraph = useCallback((graph) => {
    if (!graph) return;
    setNodes((graph.nodes || []).map((n) => ({ ...n })));
    setEdges((graph.edges || []).map((e) => ({ ...e, type: "smoothstep" })));
    setResult(null);
    setTrace([]);
    setSelectedId(null);
    setTab("canvas");
  }, []);

  const buildGraph = useCallback(() => {
    const inputObj = {};
    inputs.forEach(({ key, value }) => {
      if (key.trim()) inputObj[key.trim()] = value;
    });
    return {
      process,
      name: "studio-crew",
      inputs: Object.keys(inputObj).length ? inputObj : undefined,
      nodes: nodes.map((n) => ({ id: n.id, type: n.type, data: n.data })),
      edges: edges.map((e) => ({ source: e.source, target: e.target })),
    };
  }, [nodes, edges, process, inputs]);

  const runCrew = useCallback(async () => {
    setRunning(true);
    setTab("run");
    setResult(null);
    setTrace([]);
    try {
      await api.streamRun(buildGraph(), (msg) => {
        if (msg.type === "event") setTrace((t) => [...t, msg.event]);
        else if (msg.type === "run.end") setResult(msg.result);
        else if (msg.type === "run.error") setResult({ success: false, error: msg.error, task_outputs: [] });
      });
      notify("Crew run complete");
    } catch (e) {
      setResult({ success: false, error: e.message, task_outputs: [] });
    } finally {
      setRunning(false);
    }
  }, [buildGraph, notify]);

  const downloadGraph = useCallback(() => {
    const blob = new Blob([JSON.stringify(buildGraph(), null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "aiforge-crew.json";
    a.click();
    URL.revokeObjectURL(url);
    notify("Exported crew as JSON");
  }, [buildGraph, notify]);

  const shareGraph = useCallback(() => {
    navigator.clipboard?.writeText(JSON.stringify(buildGraph(), null, 2)).then(
      () => notify("Crew JSON copied to clipboard"),
      () => notify("Clipboard unavailable")
    );
  }, [buildGraph, notify]);

  const exportCode = useCallback(async () => {
    try {
      const res = await api.graphCode(buildGraph());
      setCode(res.code || "");
      setModal("code");
    } catch (e) {
      notify("Could not generate code: " + e.message);
    }
  }, [buildGraph, notify]);

  const renderStudio = () => (
    <div className="workspace">
      <StudioChat onGraph={applyGraph} notify={notify} />
      <div className="stage">
        <Topbar
          tab={tab}
          setTab={setTab}
          onRun={runCrew}
          running={running}
          onDownload={downloadGraph}
          onVariables={() => setModal("variables")}
          onShare={shareGraph}
          onExportCode={exportCode}
        />
        {tab === "canvas" ? (
          <Canvas
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onDropNode={onDropNode}
            onNodeClick={(_, node) => setSelectedId(node.id)}
            onPaneClick={() => setSelectedId(null)}
            onNodeContextMenu={(e, node) => {
              e.preventDefault();
              setMenu({ x: e.clientX, y: e.clientY, nodeId: node.id });
            }}
            onPaneContextMenu={(e) => {
              e.preventDefault();
              setMenu(null);
            }}
            process={process}
          />
        ) : (
          <RunView trace={trace} result={result} running={running} />
        )}
      </div>
      {selectedNode ? (
        <NodeEditor
          node={selectedNode}
          agentNames={agentNames}
          toolNames={toolNames}
          onChange={updateNodeData}
          onDelete={deleteNode}
          onClose={() => setSelectedId(null)}
        />
      ) : (
        <Inspector onAdd={addNode} catalog={catalog} />
      )}
    </div>
  );

  const renderView = () => {
    switch (view) {
      case "crew-studio":
        return renderStudio();
      case "agents":
        return <AgentsPage />;
      case "tools":
        return <ToolsPage />;
      case "usage":
        return <UsagePage />;
      default:
        return <Placeholder view={view} />;
    }
  };

  return (
    <StudioContext.Provider value={studioActions}>
      <div className="app">
        <Sidebar view={view} setView={setView} connected={connected} provider={provider} />
        {renderView()}

        <ContextMenu
          menu={menu}
          onEdit={studioActions.onEdit}
          onDuplicate={studioActions.onDuplicate}
          onDelete={studioActions.onDelete}
          onClose={() => setMenu(null)}
        />

        {modal === "variables" && (
          <Modal title="Run variables" onClose={() => setModal(null)}>
            <p className="modal-lead">
              Values your tasks can reference. They're passed to the crew as context when you Run.
            </p>
            {inputs.map((row, i) => (
              <div className="kv-row" key={i}>
                <input
                  placeholder="name"
                  value={row.key}
                  onChange={(e) => setInputs((r) => r.map((x, j) => (j === i ? { ...x, key: e.target.value } : x)))}
                />
                <input
                  placeholder="value"
                  value={row.value}
                  onChange={(e) => setInputs((r) => r.map((x, j) => (j === i ? { ...x, value: e.target.value } : x)))}
                />
                <button className="kv-del" onClick={() => setInputs((r) => r.filter((_, j) => j !== i))}>
                  ✕
                </button>
              </div>
            ))}
            <button className="btn subtle" onClick={() => setInputs((r) => [...r, { key: "", value: "" }])}>
              + Add variable
            </button>
          </Modal>
        )}

        {modal === "code" && (
          <Modal title="Run this crew in Python" onClose={() => setModal(null)} wide>
            <p className="modal-lead">
              Your visual crew, as runnable code using the AIForge SDK. Fully round-trippable.
            </p>
            <pre className="code-block">{code}</pre>
            <button
              className="btn dark"
              onClick={() => navigator.clipboard?.writeText(code).then(() => notify("Code copied"))}
            >
              Copy code
            </button>
          </Modal>
        )}

        {toast && <div className="toast">{toast}</div>}
      </div>
    </StudioContext.Provider>
  );
}
