import { Env, Share, Download, Deploy, Play } from "../icons.jsx";

export default function Topbar({ tab, setTab, onRun, running, onDownload, onVariables, onShare, onExportCode }) {
  return (
    <header className="topbar">
      <div className="breadcrumb">
        Studio <span style={{ color: "var(--faint)" }}>/</span> <b>Untitled Project</b>
      </div>

      <div className="tabs">
        <button className={`tab ${tab === "canvas" ? "active" : ""}`} onClick={() => setTab("canvas")}>
          Canvas
        </button>
        <button className={`tab ${tab === "run" ? "active" : ""}`} onClick={() => setTab("run")}>
          Run
        </button>
      </div>

      <div className="topbar-actions">
        <button className="btn subtle" onClick={onVariables}>
          <Env />
          Variables
        </button>
        <button className="btn subtle" onClick={onShare}>
          <Share />
          Share
        </button>
        <button className="btn subtle" onClick={onDownload}>
          <Download />
          Download
        </button>
        <button className="btn" onClick={onExportCode}>
          <Deploy />
          Export code
        </button>
        <button className="btn run" onClick={onRun} disabled={running}>
          {running ? <span className="spin" /> : <Play width="13" height="13" />}
          Run
        </button>
      </div>
    </header>
  );
}
