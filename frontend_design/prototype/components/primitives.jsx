/* Shared icons + small components used across modules.
 * Pure SVG icons (1.5px stroke), in line with currentColor. */

const Icon = ({ d, size = 16, fill = "none", stroke = "currentColor", strokeWidth = 1.5, children, viewBox = "0 0 24 24", style }) => (
  <svg width={size} height={size} viewBox={viewBox} fill={fill} stroke={stroke} strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round" style={style}>
    {children || <path d={d} />}
  </svg>
);

const I = {
  Sparkle: (p) => <Icon {...p}><path d="M12 3l1.6 4.4L18 9l-4.4 1.6L12 15l-1.6-4.4L6 9l4.4-1.6L12 3z"/><path d="M19 15l.7 1.8L21.5 17.5l-1.8.7L19 20l-.7-1.8L16.5 17.5l1.8-.7L19 15z"/></Icon>,
  Compass: (p) => <Icon {...p}><circle cx="12" cy="12" r="9"/><path d="M15.5 8.5l-2 5.5-5.5 2 2-5.5 5.5-2z"/></Icon>,
  Lightbulb: (p) => <Icon {...p}><path d="M9 18h6M10 21h4M12 3a6 6 0 0 0-4 10.5c.7.7 1 1.5 1 2.5h6c0-1 .3-1.8 1-2.5A6 6 0 0 0 12 3z"/></Icon>,
  Chart: (p) => <Icon {...p}><path d="M3 3v18h18"/><path d="M7 14l3-3 3 3 5-6"/></Icon>,
  User: (p) => <Icon {...p}><circle cx="12" cy="8" r="4"/><path d="M4 21c0-4 4-6 8-6s8 2 8 6"/></Icon>,
  Send: (p) => <Icon {...p}><path d="M3 12l18-9-7 18-3-7-8-2z"/></Icon>,
  Plus: (p) => <Icon {...p}><path d="M12 5v14M5 12h14"/></Icon>,
  Check: (p) => <Icon {...p}><path d="M5 12l4 4 10-10"/></Icon>,
  Arrow: (p) => <Icon {...p}><path d="M5 12h14M13 6l6 6-6 6"/></Icon>,
  ArrowUp: (p) => <Icon {...p}><path d="M12 19V5M6 11l6-6 6 6"/></Icon>,
  ArrowDown: (p) => <Icon {...p}><path d="M12 5v14M6 13l6 6 6-6"/></Icon>,
  Chevron: (p) => <Icon {...p}><path d="M6 9l6 6 6-6"/></Icon>,
  ChevronR: (p) => <Icon {...p}><path d="M9 6l6 6-6 6"/></Icon>,
  Close: (p) => <Icon {...p}><path d="M6 6l12 12M18 6L6 18"/></Icon>,
  Pin: (p) => <Icon {...p}><path d="M12 2v6l4 4-4 4v6M8 8l8 0M8 16l8 0"/></Icon>,
  Heart: (p) => <Icon {...p}><path d="M12 21s-7-4.5-9-9c-1-2.5 1-6 4-6 2 0 3.5 1.5 5 3 1.5-1.5 3-3 5-3 3 0 5 3.5 4 6-2 4.5-9 9-9 9z"/></Icon>,
  Eye: (p) => <Icon {...p}><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/></Icon>,
  Comment: (p) => <Icon {...p}><path d="M21 12a8 8 0 0 1-8 8H7l-4 3 1-5a8 8 0 1 1 17-6z"/></Icon>,
  Share: (p) => <Icon {...p}><circle cx="6" cy="12" r="2.5"/><circle cx="18" cy="6" r="2.5"/><circle cx="18" cy="18" r="2.5"/><path d="M8 11l8-4M8 13l8 4"/></Icon>,
  Trend: (p) => <Icon {...p}><path d="M3 17l6-6 4 4 8-9"/><path d="M14 6h7v7"/></Icon>,
  Search: (p) => <Icon {...p}><circle cx="11" cy="11" r="7"/><path d="M20 20l-4-4"/></Icon>,
  Settings: (p) => <Icon {...p}><circle cx="12" cy="12" r="3"/><path d="M19 12a7 7 0 0 0-.1-1.2l2-1.5-2-3.5-2.4.8a7 7 0 0 0-2-1.2L14 3h-4l-.5 2.4a7 7 0 0 0-2 1.2l-2.4-.8-2 3.5 2 1.5A7 7 0 0 0 5 12c0 .4 0 .8.1 1.2l-2 1.5 2 3.5 2.4-.8a7 7 0 0 0 2 1.2L10 21h4l.5-2.4a7 7 0 0 0 2-1.2l2.4.8 2-3.5-2-1.5c.1-.4.1-.8.1-1.2z"/></Icon>,
  Hash: (p) => <Icon {...p}><path d="M5 9h14M5 15h14M10 3L8 21M16 3l-2 18"/></Icon>,
  Bolt: (p) => <Icon {...p}><path d="M13 2L3 14h7l-1 8 10-12h-7l1-8z"/></Icon>,
  Refresh: (p) => <Icon {...p}><path d="M3 12a9 9 0 0 1 15-6.7L21 8M21 3v5h-5M21 12a9 9 0 0 1-15 6.7L3 16M3 21v-5h5"/></Icon>,
  Bookmark: (p) => <Icon {...p}><path d="M6 3h12v18l-6-4-6 4V3z"/></Icon>,
  Mic: (p) => <Icon {...p}><rect x="9" y="3" width="6" height="12" rx="3"/><path d="M5 11a7 7 0 0 0 14 0M12 18v3"/></Icon>,
  Image: (p) => <Icon {...p}><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="9" cy="9" r="2"/><path d="M21 16l-5-5L5 21"/></Icon>,
  Filter: (p) => <Icon {...p}><path d="M3 5h18l-7 9v6l-4-2v-4L3 5z"/></Icon>,
  Path: (p) => <Icon {...p}><circle cx="6" cy="6" r="2.5"/><circle cx="18" cy="18" r="2.5"/><path d="M6 8.5C6 14 12 12 12 18M14.5 18H15.5"/></Icon>,
  Brain: (p) => <Icon {...p}><path d="M9 4a3 3 0 0 0-3 3 3 3 0 0 0-3 3 3 3 0 0 0 1.5 2.6A3 3 0 0 0 6 17a3 3 0 0 0 3 3V4zM15 4a3 3 0 0 1 3 3 3 3 0 0 1 3 3 3 3 0 0 1-1.5 2.6A3 3 0 0 1 18 17a3 3 0 0 1-3 3V4z"/></Icon>,
  Lock: (p) => <Icon {...p}><rect x="4.5" y="11" width="15" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/></Icon>,
  ArrowR: (p) => <Icon {...p}><path d="M5 12h14M13 6l6 6-6 6"/></Icon>,
};

/* Avatars: 小A — initial circle, AI — lime square w/ asterisk */
const Avatar = ({ kind = "user", size = 32 }) => {
  if (kind === "ai") {
    return (
      <div style={{
        width: size, height: size,
        borderRadius: 8,
        background: "var(--accent)",
        color: "var(--accent-ink)",
        display: "grid", placeItems: "center",
        fontSize: size * 0.55, fontWeight: 800,
        fontFamily: "var(--font-mono)",
      }}>✦</div>
    );
  }
  return (
    <div style={{
      width: size, height: size,
      borderRadius: "50%",
      background: "var(--bg-3)",
      color: "var(--fg-0)",
      display: "grid", placeItems: "center",
      fontSize: size * 0.42, fontWeight: 600,
      border: "1px solid var(--line-2)",
    }}>A</div>
  );
};

/* Sparkline — tiny inline chart */
const Sparkline = ({ values = [], width = 80, height = 24, color = "currentColor", fill = false }) => {
  if (!values.length) return null;
  const min = Math.min(...values), max = Math.max(...values);
  const range = max - min || 1;
  const step = width / (values.length - 1);
  const pts = values.map((v, i) => [i * step, height - ((v - min) / range) * (height - 4) - 2]);
  const d = pts.map((p, i) => (i === 0 ? `M${p[0]},${p[1]}` : `L${p[0]},${p[1]}`)).join(" ");
  const dFill = fill ? `${d} L${width},${height} L0,${height} Z` : "";
  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} style={{ overflow: "visible" }}>
      {fill && <path d={dFill} fill={color} opacity="0.14"/>}
      <path d={d} fill="none" stroke={color} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  );
};

/* Bar — horizontal progress for a 0–1 score, with label inside */
const Score = ({ value = 0.5, label, color = "var(--accent)", height = 6, width = "100%" }) => (
  <div style={{ width, display: "flex", alignItems: "center", gap: 8 }}>
    <div style={{ flex: 1, height, background: "var(--bg-3)", borderRadius: 999, overflow: "hidden" }}>
      <div style={{ width: `${Math.round(value * 100)}%`, height: "100%", background: color, borderRadius: 999 }}/>
    </div>
    {label !== undefined && <span style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--fg-1)", minWidth: 28, textAlign: "right" }}>{label}</span>}
  </div>
);

/* Section heading */
const SectionTitle = ({ kicker, title, sub, right }) => (
  <div style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between", marginBottom: 16 }}>
    <div>
      {kicker && <div className="h-mono" style={{ marginBottom: 6 }}>{kicker}</div>}
      <div style={{ fontSize: 22, fontWeight: 600, letterSpacing: "-0.01em", lineHeight: 1.2 }}>{title}</div>
      {sub && <div style={{ color: "var(--fg-2)", fontSize: 13, marginTop: 6, maxWidth: 560 }}>{sub}</div>}
    </div>
    {right}
  </div>
);

/* Source pill — distinguishes 画像-driven vs 趋势-driven recs */
const SourceTag = ({ source }) => {
  const map = {
    profile: { label: "画像驱动", color: "var(--pillar-person)" },
    trend:   { label: "趋势驱动", color: "var(--info)" },
    explore: { label: "探索驱动", color: "var(--pillar-explore)" },
    data:    { label: "数据驱动", color: "var(--accent)" },
  };
  const t = map[source] || map.profile;
  return (
    <span style={{
      fontFamily: "var(--font-mono)",
      fontSize: 9.5, letterSpacing: "0.08em", textTransform: "uppercase",
      padding: "2px 7px", borderRadius: 4,
      color: t.color, border: `1px solid ${t.color}40`,
      background: `${t.color}10`,
    }}>{t.label}</span>
  );
};

Object.assign(window, { Icon, I, Avatar, Sparkline, Score, SectionTitle, SourceTag });
