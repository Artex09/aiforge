# AIForge Studio (frontend)

A Node.js, flow-based visual workflow builder for AIForge — **React + Vite +
React Flow**. It's the "Node-based UI" for designing and running **sequential
agent crews**: drag Agent / Task / Trigger nodes onto a canvas, wire them in
order, describe the crew in Studio Chat, and hit **Run**.

## Develop

```bash
npm install
npm run dev        # http://127.0.0.1:5173  (proxies /api to the engine on :8787)
```

Run the engine + API in another terminal so the UI has a backend:

```bash
python -m aiforge.cli serve
```

## Build

```bash
npm run build      # outputs ./dist
```

The AIForge stdlib API server (`aiforge/api/server.py`) automatically serves
`dist/` at `/` when it exists, with SPA fallback routing. So after building:

```bash
python -m aiforge.cli studio    # serves the built Studio at http://127.0.0.1:8787
```

## Design

An "editorial forge" aesthetic — warm porcelain canvas, ink typography, a single
ember accent (true to *AIForge*), Fraunces + Hanken Grotesk. No component library;
every node, panel, and control is hand-built.

## Structure

```
src/
├── App.jsx              # shell: sidebar + studio chat + canvas/run + inspector
├── api.js               # REST client for /api
├── icons.jsx            # inline SVG icon set
├── styles.css           # the design system
└── components/
    ├── Sidebar.jsx      # Build / Operate / Manage navigation
    ├── StudioChat.jsx   # brief -> crew (calls /api/studio/chat)
    ├── Topbar.jsx       # Canvas | Run tabs + actions + Run
    ├── Canvas.jsx       # React Flow canvas + Process-type card
    ├── Inspector.jsx    # Crew palette + Tools catalog
    ├── RunView.jsx      # per-task results
    ├── Pages.jsx        # Agents / Tools / Usage / placeholders
    └── nodes/           # AgentNode, TaskNode, TriggerNode
```
