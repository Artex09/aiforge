import { useEffect } from "react";
import { Edit, Copy } from "../icons.jsx";

export default function ContextMenu({ menu, onEdit, onDuplicate, onDelete, onClose }) {
  useEffect(() => {
    const close = () => onClose();
    window.addEventListener("click", close);
    window.addEventListener("scroll", close, true);
    return () => {
      window.removeEventListener("click", close);
      window.removeEventListener("scroll", close, true);
    };
  }, [onClose]);

  if (!menu) return null;
  return (
    <div className="ctx-menu" style={{ left: menu.x, top: menu.y }} onClick={(e) => e.stopPropagation()}>
      <button onClick={() => { onEdit(menu.nodeId); onClose(); }}>
        <Edit width="14" height="14" /> Edit
      </button>
      <button onClick={() => { onDuplicate(menu.nodeId); onClose(); }}>
        <Copy width="14" height="14" /> Duplicate
      </button>
      <div className="ctx-sep" />
      <button className="danger" onClick={() => { onDelete(menu.nodeId); onClose(); }}>
        Delete
      </button>
    </div>
  );
}
