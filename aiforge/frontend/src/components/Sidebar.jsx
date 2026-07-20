import { Forge, Chevron, ChevronDown, Flow, Grid, Tool, Layers, Gauge, Bolt, Settings, Book, Agent } from "../icons.jsx";

const NAV = [
  {
    label: "Build",
    items: [
      { id: "automations", name: "Automations", icon: Bolt },
      { id: "crew-studio", name: "Crew Studio", icon: Flow },
      { id: "agents", name: "Agents Repository", icon: Agent },
      { id: "tools", name: "Tools & Integrations", icon: Tool },
      { id: "skills", name: "Skills Repository", icon: Layers },
    ],
  },
  {
    label: "Operate",
    items: [
      { id: "traces", name: "Traces", icon: Grid },
      { id: "connections", name: "LLM Connections", icon: Book },
    ],
  },
  {
    label: "Manage",
    items: [
      { id: "usage", name: "Usage", icon: Gauge },
      { id: "settings", name: "Settings", icon: Settings },
    ],
  },
];

export default function Sidebar({ view, setView, connected, provider }) {
  return (
    <aside className="sidebar">
      <div className="org">
        <div className="mark">
          <Forge width="20" height="20" />
        </div>
        <div className="org-name">
          AIForge
          <small>Your workspace</small>
        </div>
        <ChevronDown className="chev" width="15" height="15" />
      </div>

      {NAV.map((group) => (
        <div className="nav-group" key={group.label}>
          <div className="nav-label">{group.label}</div>
          {group.items.map((item) => {
            const Icon = item.icon;
            return (
              <button
                key={item.id}
                className={`nav-item ${view === item.id ? "active" : ""}`}
                onClick={() => setView(item.id)}
              >
                <Icon />
                {item.name}
              </button>
            );
          })}
        </div>
      ))}

      <div className="sidebar-foot">
        <span className={`dot ${connected ? "on" : ""}`} />
        {connected ? `engine · ${provider || "mock"}` : "connecting…"}
      </div>
    </aside>
  );
}
