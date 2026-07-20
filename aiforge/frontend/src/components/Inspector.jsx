import { useState } from "react";
import { Task, Agent, Plus, Search, Tool, Sparkle, Bolt, Database, File, Globe, ChevronDown } from "../icons.jsx";

const CAT_ICON = {
  "AI & Machine Learning": Sparkle,
  "Automation & Integration": Bolt,
  "Database & Data": Database,
  "File & Document": File,
  System: Tool,
  Integrations: Globe,
};

function paletteDrag(type, data) {
  return (e) => {
    e.dataTransfer.setData("application/aiforge", JSON.stringify({ type, data }));
    e.dataTransfer.effectAllowed = "move";
  };
}

export default function Inspector({ onAdd, catalog = {} }) {
  const [open, setOpen] = useState({ "AI & Machine Learning": true });
  const [query, setQuery] = useState("");

  const newAgent = () => ({
    name: "New Agent",
    role: "assistant",
    model: "aiforge-mock-1",
    system_prompt: "A helpful specialist agent.",
    tools: [],
  });
  const newTask = () => ({ label: "New Task", description: "Describe the task…", agent: "" });

  return (
    <aside className="inspector">
      <div className="insp-section">
        <div className="insp-title">Crew</div>

        <div
          className="palette-item agent"
          draggable
          onDragStart={paletteDrag("agent", newAgent())}
          onClick={() => onAdd("agent", newAgent())}
        >
          <span className="pi">
            <Agent width="16" height="16" />
          </span>
          <div>
            <div className="pt">Agent</div>
            <div className="ps">A specialist with tools</div>
          </div>
          <Plus className="add" width="16" height="16" />
        </div>

        <div
          className="palette-item task"
          draggable
          onDragStart={paletteDrag("task", newTask())}
          onClick={() => onAdd("task", newTask())}
        >
          <span className="pi">
            <Task width="16" height="16" />
          </span>
          <div>
            <div className="pt">Task</div>
            <div className="ps">A unit of work for an agent</div>
          </div>
          <Plus className="add" width="16" height="16" />
        </div>
      </div>

      <div className="insp-section" style={{ flex: 1 }}>
        <div className="insp-title">Tools</div>
        <div className="search">
          <Search />
          <input
            placeholder="Search tools…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>

        {Object.entries(catalog).map(([cat, tools]) => {
          const Icon = CAT_ICON[cat] || Tool;
          const filtered = tools.filter((t) =>
            (t.function?.name || "").toLowerCase().includes(query.toLowerCase())
          );
          if (query && filtered.length === 0) return null;
          const isOpen = query ? true : open[cat];
          return (
            <div className={`cat ${isOpen ? "open" : ""}`} key={cat}>
              <div className="cat-head" onClick={() => setOpen((o) => ({ ...o, [cat]: !o[cat] }))}>
                <Icon width="15" height="15" style={{ color: "var(--muted)" }} />
                {cat}
                <span className="count">{filtered.length}</span>
                <ChevronDown className="chev" width="14" height="14" />
              </div>
              {isOpen &&
                filtered.map((t) => {
                  const fn = t.function || t;
                  return (
                    <div
                      className="tool-line"
                      key={fn.name}
                      draggable
                      onDragStart={paletteDrag("task", {
                        label: fn.name,
                        description: fn.description,
                        agent: "",
                      })}
                      title={fn.description}
                    >
                      <span className="ti">
                        <Tool />
                      </span>
                      {fn.name}
                    </div>
                  );
                })}
            </div>
          );
        })}
      </div>
    </aside>
  );
}
