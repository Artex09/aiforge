import { Env, Download, Deploy, Play, Check } from "../icons.jsx";

export default function Topbar({
  tab,
  setTab,
  crewName,
  setCrewName,
  onRun,
  running,
  onSave,
  onDownload,
  onVariables,
  onExportCode,
}) {
  return (
    <header className="topbar">
      <div className="breadcrumb">
        Studio <span style={{ color: "var(--faint)" }}>/</span>
        <input
          className="crew-name"
          value={crewName}
          onChange={(e) => setCrewName(e.target.value)}
          placeholder="Untitled crew"
          spellCheck={false}
          size={Math.max(crewName.length || 13, 8)}
        />
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
        <button className="btn subtle" onClick={onDownload}>
          <Download />
          Download
        </button>
        <button className="btn subtle" onClick={onSave} title="Save this crew to Automations">
          <Check />
          Save
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
