import { useRef, useEffect, useState } from "react";
import { Plus, Check, Clock, Play } from "../icons.jsx";
import { api } from "../api.js";

export default function StudioChat({ onGraph, notify }) {
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      text: "Describe the crew you want to build and I'll wire up sequential agents and tasks on the canvas.",
    },
  ]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const bodyRef = useRef(null);

  useEffect(() => {
    if (bodyRef.current) bodyRef.current.scrollTop = bodyRef.current.scrollHeight;
  }, [messages, busy]);

  async function send() {
    const message = text.trim();
    if (!message || busy) return;
    setMessages((m) => [...m, { role: "user", text: message }]);
    setText("");
    setBusy(true);
    try {
      const res = await api.studioChat(message);
      setMessages((m) => [
        ...m,
        { role: "assistant", text: res.reply, steps: res.steps },
      ]);
      if (res.graph) {
        onGraph(res.graph);
        notify && notify("Crew added to canvas");
      }
    } catch (e) {
      setMessages((m) => [...m, { role: "assistant", text: "Couldn't reach the engine: " + e.message }]);
    } finally {
      setBusy(false);
    }
  }

  function onKey(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  }

  function renderText(t) {
    // very small markdown: **bold**
    const parts = t.split(/(\*\*[^*]+\*\*)/g);
    return parts.map((p, i) =>
      p.startsWith("**") ? <strong key={i}>{p.slice(2, -2)}</strong> : <span key={i}>{p}</span>
    );
  }

  return (
    <section className="chat">
      <div className="chat-head">
        <h2>Studio Chat</h2>
        <button className="ghost" title="History">
          <Clock width="15" height="15" />
        </button>
      </div>

      <div className="chat-body" ref={bodyRef}>
        {messages.map((m, i) => (
          <div key={i}>
            <div className={`bubble ${m.role}`}>{renderText(m.text)}</div>
            {m.steps && (
              <div className="checklist">
                {m.steps.map((s, j) => (
                  <div className="check" key={j} style={{ animationDelay: `${j * 90}ms` }}>
                    <span className="tick">
                      <Check />
                    </span>
                    {s}
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
        {busy && (
          <div className="bubble assistant" style={{ color: "var(--muted)" }}>
            Thinking…
          </div>
        )}
      </div>

      <div className="chat-input">
        <div className="field">
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={onKey}
            placeholder="Ask, build…  (Shift + Enter for a new line)"
          />
          <div className="row">
            <button className="btn run" onClick={send} disabled={busy}>
              {busy ? <span className="spin" /> : <Play width="13" height="13" />}
              Send
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}
