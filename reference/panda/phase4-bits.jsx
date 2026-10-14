// phase4-bits.jsx — primitives for the Phase 4 prototype
const StepTag = ({ children }) => <div className="step-tag">{children}</div>;
const CardTitle = ({ children }) => <div className="card-title">{children}</div>;
const CardBody = ({ children, style }) => <div className="card-body" style={style}>{children}</div>;

const GlassButton = ({ variant = "primary", icon, children, onClick, disabled, full }) => (
  <button
    className={`gbtn ${variant} ${full ? "full" : ""}`}
    onClick={onClick}
    disabled={disabled}
  >
    {icon && <i data-lucide={icon} width="14" height="14"></i>}
    <span>{children}</span>
  </button>
);

const Tag = ({ tone = "blue", icon, children }) => (
  <span className={`tag ${tone}`}>
    {icon ? <i data-lucide={icon} width="12" height="12"></i> : <span className="dot"></span>}
    {children}
  </span>
);

const VoicePill = ({ children }) => (
  <span className="voice-pill">
    <span className="mic-dot"><i data-lucide="mic" width="10" height="10"></i></span>
    {children}
  </span>
);

const AlertBox = ({ tone = "info", icon, children }) => {
  const defaultIcon = {
    info: "info",
    success: "check-circle-2",
    warn: "alert-triangle",
    error: "alert-octagon",
  }[tone];
  return (
    <div className={`alert ${tone}`}>
      <i className="ai" data-lucide={icon || defaultIcon} width="16" height="16"></i>
      <div>{children}</div>
    </div>
  );
};

const StatBox = ({ value, label, color, sub }) => (
  <div className="stat-box">
    <div className="stat-value" style={color ? { color } : undefined}>{value}</div>
    <div className="stat-label">{label}</div>
    {sub && <div className="stat-sub">{sub}</div>}
  </div>
);

const Checkbox = ({ checked, onChange }) => (
  <span
    className={`checkbox ${checked ? "on" : ""}`}
    role="checkbox"
    aria-checked={checked}
    tabIndex="0"
    onClick={onChange}
    onKeyDown={(e) => (e.key === " " || e.key === "Enter") && onChange?.()}
  ></span>
);

const GlassCard = ({ tint = "", wide = false, children, style, className = "" }) => (
  <div
    className={`gcard ${tint ? "tint-" + tint : ""} ${wide ? "wide" : ""} ${className}`}
    style={style}
  >
    {children}
  </div>
);

// Spatial pin marker — points to a location in the AR scene
const SpatialPin = ({ x, y, label, tone = "blue", icon }) => (
  <div className="spatial-pin" style={{ left: `${x}%`, top: `${y}%` }}>
    <div className={`pin-target ${tone}`}>
      {icon && <i data-lucide={icon} width="14" height="14"></i>}
    </div>
    {label && <div className={`pin-label ${tone}`}>{label}</div>}
  </div>
);

// Anchor line from pin to a card edge
const AnchorLine = ({ from, to, tone = "blue" }) => (
  <svg className="anchor-line" style={{ pointerEvents: "none" }}>
    <line
      x1={`${from.x}%`} y1={`${from.y}%`}
      x2={`${to.x}%`} y2={`${to.y}%`}
      stroke={`var(--${tone})`} strokeWidth="1.2"
      strokeDasharray="3 4" opacity="0.6"
    />
  </svg>
);

Object.assign(window, {
  StepTag, CardTitle, CardBody, GlassButton, Tag, VoicePill,
  AlertBox, StatBox, Checkbox, GlassCard, SpatialPin, AnchorLine,
});
