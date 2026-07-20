// Minimal inline SVG icon set — stroke-based, 24x24 viewBox, currentColor.
const S = ({ children, ...p }) => (
  <svg
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="1.8"
    strokeLinecap="round"
    strokeLinejoin="round"
    {...p}
  >
    {children}
  </svg>
);

export const Forge = (p) => (
  <svg viewBox="0 0 24 24" fill="none" {...p}>
    <path d="M12 4l7 13H5z" stroke="#e4572e" strokeWidth="2.2" strokeLinejoin="round" />
  </svg>
);
export const Chevron = (p) => (
  <S {...p}>
    <path d="M9 6l6 6-6 6" />
  </S>
);
export const ChevronDown = (p) => (
  <S {...p}>
    <path d="M6 9l6 6 6-6" />
  </S>
);
export const Plus = (p) => (
  <S {...p}>
    <path d="M12 5v14M5 12h14" />
  </S>
);
export const Agent = (p) => (
  <S {...p}>
    <circle cx="12" cy="8" r="3.4" />
    <path d="M5 20c0-3.6 3.1-6 7-6s7 2.4 7 6" />
  </S>
);
export const Task = (p) => (
  <S {...p}>
    <rect x="5" y="4" width="14" height="16" rx="2" />
    <path d="M9 9h6M9 13h6M9 17h3" />
  </S>
);
export const Trigger = (p) => (
  <S {...p}>
    <path d="M13 3L4 14h6l-1 7 9-11h-6z" />
  </S>
);
export const Tool = (p) => (
  <S {...p}>
    <path d="M14.5 6.5a3.5 3.5 0 01-4.6 4.6l-5 5a1.8 1.8 0 102.5 2.5l5-5a3.5 3.5 0 004.6-4.6l-2 2-2-.5-.5-2z" />
  </S>
);
export const Model = (p) => (
  <S {...p}>
    <rect x="7" y="7" width="10" height="10" rx="2" />
    <path d="M10 3v4M14 3v4M10 17v4M14 17v4M3 10h4M3 14h4M17 10h4M17 14h4" />
  </S>
);
export const Search = (p) => (
  <S {...p}>
    <circle cx="11" cy="11" r="6.5" />
    <path d="M20 20l-3.5-3.5" />
  </S>
);
export const Play = (p) => (
  <svg viewBox="0 0 24 24" fill="currentColor" {...p}>
    <path d="M8 5.5v13l11-6.5z" />
  </svg>
);
export const Share = (p) => (
  <S {...p}>
    <circle cx="18" cy="5" r="2.5" />
    <circle cx="6" cy="12" r="2.5" />
    <circle cx="18" cy="19" r="2.5" />
    <path d="M8.2 10.8l7.6-4.4M8.2 13.2l7.6 4.4" />
  </S>
);
export const Download = (p) => (
  <S {...p}>
    <path d="M12 4v11m0 0l-4-4m4 4l4-4M5 20h14" />
  </S>
);
export const Deploy = (p) => (
  <S {...p}>
    <path d="M12 3c3 2 5 5 5 9l-5 3-5-3c0-4 2-7 5-9z" />
    <circle cx="12" cy="10" r="1.6" />
    <path d="M9 18l-2 3M15 18l2 3" />
  </S>
);
export const Env = (p) => (
  <S {...p}>
    <path d="M4 7h16M4 12h16M4 17h10" />
  </S>
);
export const Check = (p) => (
  <S {...p}>
    <path d="M5 12l4.5 4.5L19 7" />
  </S>
);
export const Edit = (p) => (
  <S {...p}>
    <path d="M4 20h4l10-10-4-4L4 16z" />
  </S>
);
export const Copy = (p) => (
  <S {...p}>
    <rect x="9" y="9" width="11" height="11" rx="2" />
    <path d="M6 15H5a2 2 0 01-2-2V5a2 2 0 012-2h8a2 2 0 012 2v1" />
  </S>
);
export const Globe = (p) => (
  <S {...p}>
    <circle cx="12" cy="12" r="8.5" />
    <path d="M3.5 12h17M12 3.5c2.5 2.5 2.5 14.5 0 17M12 3.5c-2.5 2.5-2.5 14.5 0 17" />
  </S>
);
export const Database = (p) => (
  <S {...p}>
    <ellipse cx="12" cy="6" rx="7" ry="3" />
    <path d="M5 6v12c0 1.7 3.1 3 7 3s7-1.3 7-3V6M5 12c0 1.7 3.1 3 7 3s7-1.3 7-3" />
  </S>
);
export const File = (p) => (
  <S {...p}>
    <path d="M14 3H7a2 2 0 00-2 2v14a2 2 0 002 2h10a2 2 0 002-2V8z" />
    <path d="M14 3v5h5" />
  </S>
);
export const Bolt = (p) => (
  <S {...p}>
    <path d="M13 3L4 14h6l-1 7 9-11h-6z" />
  </S>
);
export const Cpu = Model;
export const Sparkle = (p) => (
  <S {...p}>
    <path d="M12 4l1.6 4.8L18 10l-4.4 1.2L12 16l-1.6-4.8L6 10l4.4-1.2z" />
  </S>
);
export const Clock = (p) => (
  <S {...p}>
    <circle cx="12" cy="12" r="8.5" />
    <path d="M12 7v5l3 2" />
  </S>
);
export const Grid = (p) => (
  <S {...p}>
    <rect x="4" y="4" width="7" height="7" rx="1.5" />
    <rect x="13" y="4" width="7" height="7" rx="1.5" />
    <rect x="4" y="13" width="7" height="7" rx="1.5" />
    <rect x="13" y="13" width="7" height="7" rx="1.5" />
  </S>
);
export const Layers = (p) => (
  <S {...p}>
    <path d="M12 3l9 5-9 5-9-5z" />
    <path d="M3 13l9 5 9-5" />
  </S>
);
export const Settings = (p) => (
  <S {...p}>
    <circle cx="12" cy="12" r="3" />
    <path d="M12 2v3M12 19v3M2 12h3M19 12h3M5 5l2 2M17 17l2 2M19 5l-2 2M7 17l-2 2" />
  </S>
);
export const Book = (p) => (
  <S {...p}>
    <path d="M5 4h11a2 2 0 012 2v14H7a2 2 0 01-2-2z" />
    <path d="M5 16h13" />
  </S>
);
export const Flow = (p) => (
  <S {...p}>
    <rect x="3" y="9" width="6" height="6" rx="1.5" />
    <rect x="15" y="4" width="6" height="6" rx="1.5" />
    <rect x="15" y="14" width="6" height="6" rx="1.5" />
    <path d="M9 12h3v-5h3M12 12h3v5h3" />
  </S>
);
export const Gauge = (p) => (
  <S {...p}>
    <path d="M4 18a8 8 0 1116 0" />
    <path d="M12 18l4-5" />
  </S>
);
export const Trash = (p) => (
  <S {...p}>
    <path d="M4 7h16M9 7V5a1 1 0 011-1h4a1 1 0 011 1v2M6 7l1 13a1 1 0 001 1h8a1 1 0 001-1l1-13" />
    <path d="M10 11v6M14 11v6" />
  </S>
);
export const Key = (p) => (
  <S {...p}>
    <circle cx="8" cy="14" r="4" />
    <path d="M11 11l9-9M17 5l3 3M14 8l2 2" />
  </S>
);
export const Broom = (p) => (
  <S {...p}>
    <path d="M14 4l6 6M9 9l6 6-5 5H6a2 2 0 01-2-2v-4z" />
  </S>
);
