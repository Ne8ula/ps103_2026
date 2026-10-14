// phase5-app.jsx — Phase 4 · Completion & Post-Print
// Reuses primitives from phase4-bits.jsx (StepTag, GlassCard, GlassButton, AlertBox, Tag, Checkbox, VoicePill, SpatialPin)
// and PrinterScene from phase4-printer.jsx. AskAI is re-defined here with Phase 4 prompts.
const { useState, useEffect, useRef, useMemo } = React;

// ============ Inline Staff Notified callout (small, used only for "stuck" branch) ============
const StaffNotifiedCard = ({ secondsLeft, onDismiss }) => {
  const pct = Math.max(0, Math.min(100, (1 - secondsLeft / 120) * 100));
  const mm = Math.floor(secondsLeft / 60);
  const ss = String(secondsLeft % 60).padStart(2, "0");
  return (
    <div className="staff-notified">
      <div className="sn-head">
        <div className="sn-icon"><i data-lucide="phone-call" width="18" height="18"></i></div>
        <div>
          <div className="sn-tag">STAFF NOTIFIED</div>
          <div className="sn-title">Help is on the way</div>
        </div>
        <button className="sn-close" onClick={onDismiss} aria-label="Dismiss">
          <i data-lucide="x" width="14" height="14"></i>
        </button>
      </div>
      <div className="sn-body">A MakerLAB staff member has been alerted to your printer.</div>
      <div className="sn-row">
        <div className="sn-avatar">JM</div>
        <div>
          <div className="sn-name">Jamie M.</div>
          <div className="sn-sub">Lab Technician · Bay 2</div>
        </div>
        <div className="sn-eta">
          <div className="sn-eta-v">{mm}:{ss}</div>
          <div className="sn-eta-l">ETA</div>
        </div>
      </div>
      <div className="sn-progress-wrap"><div className="sn-progress-fill" style={{ width: `${pct}%` }}></div></div>
      <div className="sn-meta">
        <span><i data-lucide="map-pin" width="11" height="11"></i> The Bust · Printer X1-A</span>
        <span>Acknowledged · 12s ago</span>
      </div>
    </div>
  );
};

// ============ Step definitions ============
// Expanded from the source (4 cards) to a fuller post-print flow that maps to the
// storyboard panels 7 & 8 (Print Complete Notification + Safe Removal).
const PH5_STEPS = [
  { id: "complete",      tag: "Step 15 · Print Complete",       name: "Print complete — handoff" },
  { id: "navigate",      tag: "Step 16 · Walk to Printer",      name: "Walking to your printer" },
  { id: "arrived",       tag: "Step 17 · You've Arrived",       name: "You're at the printer" },
  { id: "cooling-hot",   tag: "Step 18 · Cooling — Hot",        name: "Build plate is still hot" },
  { id: "cooling-warm",  tag: "Step 19 · Cooling — Warm",       name: "Almost cool" },
  { id: "cooling-safe",  tag: "Step 20 · Cooling — Safe",       name: "Ready to remove" },
  { id: "remove-prep",   tag: "Step 21 · Prepare to Remove",    name: "Remove the build plate" },
  { id: "lift-model",    tag: "Step 22 · Lift Model",           name: "Lift your model off the plate" },
  { id: "stuck",         tag: "Step 23 · Model Stuck (Optional)", name: "Model is stuck — gentle help" },
  { id: "inspect",       tag: "Step 24 · Inspect Print",        name: "Check the print quality" },
  { id: "reseat",        tag: "Step 25 · Reseat the Plate",     name: "Place the plate back" },
  { id: "wrap-up",       tag: "Step 26 · Wrap Up",              name: "All done — first print finished" },
];

const ph5Index = (id) => PH5_STEPS.findIndex(s => s.id === id);

// ============ Step rail (Phase 5 variant) ============
const StepRail5 = ({ currentId, visited, onSelect }) => (
  <div className="step-rail">
    <div className="rail-title">Phase 4 · Completion</div>
    {PH5_STEPS.map((s, i) => {
      const isActive = s.id === currentId;
      const isDone = visited.has(s.id) && !isActive;
      const isWarn = (s.id === "stuck") && isActive;
      return (
        <div
          key={s.id}
          className={`rail-step ${isActive ? "active" : ""} ${isDone ? "done" : ""} ${isWarn ? "error" : ""}`}
          onClick={() => onSelect(s.id)}
        >
          <div className="rs-num">{isDone ? "✓" : i + 1}</div>
          <div className="rs-meta">
            <div className="rs-tag">{s.tag.split("·")[0].trim()}</div>
            <div className="rs-name">{s.name}</div>
          </div>
        </div>
      );
    })}
  </div>
);

// ============ Temperature ring widget ============
const TempRing = ({ temp, target = 30, mode = "hot", eta }) => {
  // mode: hot | warm | safe
  const start = 220; // print temp peak (approx for nozzle path; visual)
  const initialPlate = 60; // build-plate started ~60°C
  const ratio = Math.max(0, Math.min(1, (temp - target) / (initialPlate - target)));
  const dashTotal = 201;
  const dashOffset = (1 - ratio) * dashTotal;
  // Temperature widget keeps its state color — that's the rule
  const color = mode === "hot" ? "#FF453A" : mode === "warm" ? "#FF9F0A" : "#30D158";
  return (
    <svg width="92" height="92" viewBox="0 0 92 92">
      <circle cx="46" cy="46" r="32" fill="none" stroke="rgba(255,255,255,0.14)" strokeWidth="6"/>
      <circle
        cx="46" cy="46" r="32" fill="none"
        stroke={color}
        strokeWidth="6"
        strokeDasharray={dashTotal}
        strokeDashoffset={dashOffset}
        strokeLinecap="round"
        transform="rotate(-90 46 46)"
        style={{ transition: "stroke-dashoffset 800ms cubic-bezier(0.32,0.72,0,1), stroke 400ms" }}
      />
      <text x="46" y="44" textAnchor="middle" fontSize="15" fontWeight="700" fill={color} fontFamily="Inter, sans-serif">
        {Math.round(temp)}°C
      </text>
      <text x="46" y="60" textAnchor="middle" fontSize="9" fontWeight="600" fill="rgba(255,255,255,0.6)" fontFamily="Inter, sans-serif" letterSpacing="1">
        {eta || (mode === "safe" ? "SAFE" : "COOLING")}
      </text>
    </svg>
  );
};

const TempLegend = ({ temp }) => {
  // Map temperature 60→30 to position 0→100%
  const pct = Math.max(0, Math.min(100, ((60 - temp) / (60 - 30)) * 100));
  return (
    <div>
      <div className="temp-legend">
        <div className="temp-legend-track">
          <div className="temp-legend-marker" style={{ left: `${pct}%` }}></div>
        </div>
      </div>
      <div className="temp-legend-stops">
        <span style={{ color: "var(--red)" }}>● Hot 60°</span>
        <span style={{ color: "var(--orange)" }}>● Warm 45°</span>
        <span style={{ color: "var(--green)" }}>● Safe 30°</span>
      </div>
    </div>
  );
};

// ============ Lift diagram — top-down view of plate with two hands ============
const LiftDiagram = ({ phase = "ready" }) => (
  <svg viewBox="0 0 280 160" className="lift-diagram-svg" aria-label="Two-handed lift technique">
    <defs>
      <linearGradient id="plateGrad" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stopColor="#2c2f35"/>
        <stop offset="100%" stopColor="#16181c"/>
      </linearGradient>
    </defs>

    {/* Build plate (top down) */}
    <rect x="60" y="40" width="160" height="100" rx="8" fill="url(#plateGrad)" stroke="rgba(255,255,255,0.08)"/>
    <rect x="64" y="44" width="152" height="92" rx="6" fill="none" stroke="rgba(255,255,255,0.04)"/>

    {/* Layer-line texture on plate */}
    {Array.from({ length: 18 }).map((_, i) => (
      <line key={i} x1={64 + i * 8.5} y1="44" x2={64 + i * 8.5} y2="136" stroke="rgba(255,255,255,0.025)" strokeWidth="1"/>
    ))}

    {/* The model on the plate — white */}
    <rect x="116" y="68" width="48" height="44" rx="4" fill="rgba(255,255,255,0.90)"/>
    <rect x="120" y="72" width="40" height="2" fill="rgba(0,0,0,0.08)"/>

    {/* Left hand — stabilize (palm flat on plate edge) */}
    <g className="lift-hand-arrow">
      <path
        d="M 30 80 Q 24 82, 24 90 L 24 110 Q 24 116, 30 116 L 56 116 Q 60 116, 60 110 L 60 88 Q 60 82, 54 82 Z"
        fill="rgba(10,132,255,0.78)"
        stroke="#fff" strokeWidth="1.5"
      />
      <text x="42" y="105" textAnchor="middle" fontSize="9" fontWeight="700" fill="#fff" fontFamily="Inter, sans-serif">HOLD</text>
    </g>

    {/* Right hand — lift edge (curl + arrow up) */}
    <g className="lift-hand-arrow" style={{ animationDelay: "0.6s" }}>
      <path
        d={phase === "lifting"
          ? "M 224 60 Q 218 62, 218 70 L 218 92 Q 218 98, 224 98 L 250 98 Q 254 98, 254 92 L 254 68 Q 254 62, 248 62 Z"
          : "M 224 80 Q 218 82, 218 90 L 218 112 Q 218 118, 224 118 L 250 118 Q 254 118, 254 112 L 254 88 Q 254 82, 248 82 Z"
        }
        fill="rgba(48,209,88,0.78)"
        stroke="#fff" strokeWidth="1.5"
        style={{ transition: "d 600ms cubic-bezier(0.32,0.72,0,1)" }}
      />
      <text x="236" y={phase === "lifting" ? 83 : 103} textAnchor="middle" fontSize="9" fontWeight="700" fill="#fff" fontFamily="Inter, sans-serif"
            style={{ transition: "y 600ms cubic-bezier(0.32,0.72,0,1)" }}>
        LIFT
      </text>
    </g>

    {/* Up arrow on right side */}
    <g opacity={phase === "lifting" ? 1 : 0.6} style={{ transition: "opacity 400ms" }}>
      <path d="M 236 56 L 236 32 M 232 38 L 236 32 L 240 38"
            stroke="var(--green)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" fill="none"/>
    </g>

    {/* Anchor on left side */}
    <g opacity="0.6">
      <circle cx="42" cy="62" r="3" fill="var(--blue)"/>
      <circle cx="42" cy="62" r="6" fill="none" stroke="var(--blue)" strokeWidth="1.2" opacity="0.4"/>
    </g>
  </svg>
);

// ============ Cool-down printer scene (mini) ============
const CooldownPrinter = ({ temp, mode, showWisps = false }) => (
  <div style={{ position: "relative" }}>
    {/* Use the existing scene-printer SVG — but make it static, "done" state */}
    {showWisps && (
      <svg className="heat-wisp" viewBox="0 0 100 100" preserveAspectRatio="none">
        <circle cx="40" cy="80" r="6" fill="rgba(255,159,10,0.55)" />
        <circle cx="55" cy="80" r="5" fill="rgba(255,159,10,0.45)" />
        <circle cx="50" cy="80" r="7" fill="rgba(255,159,10,0.35)" />
      </svg>
    )}
  </div>
);

// ============ Collapsible detail section ============
const CollapsibleInfo = ({ label, icon = "info", tone = "neutral", children }) => {
  const [open, setOpen] = useState(false);
  return (
    <div className={`collapsible-info ci-${tone}`}>
      <button className="ci-toggle" onClick={() => setOpen(o => !o)}>
        <i data-lucide={icon} width="12" height="12"/>
        <span>{label}</span>
        <i data-lucide={open ? "chevron-up" : "chevron-down"} width="12" height="12" style={{ marginLeft: "auto", opacity: 0.5 }}/>
      </button>
      {open && <div className="ci-body">{children}</div>}
    </div>
  );
};

// ============ Card variants per step ============
const Card_Complete = ({ onAdvance, onDismiss }) => (
  <GlassCard tint="green">
    <StepTag>Step 15 · Print Complete</StepTag>
    <CardTitle>Print complete!</CardTitle>
    <div style={{ marginTop: 10 }}>
      <Tag tone="green" icon="check-circle-2">Bambu Lab X1 Carbon · The Bust</Tag>
    </div>
    <CollapsibleInfo label="Articulated Cat · v3  ·  2h 14m  ·  32g" icon="file-text" tone="neutral">
      <div className="model-card" style={{ background: "rgba(255,255,255,0.12)", borderColor: "rgba(255,255,255,0.2)", marginTop: 6 }}>
        <div className="model-thumb"></div>
        <div className="model-meta">
          <div className="model-name" style={{ color: "#fff" }}>Articulated Cat · v3</div>
          <div className="model-sub" style={{ color: "rgba(255,255,255,0.7)" }}>cat_v3.gcode · 32g PLA</div>
          <div className="model-stats" style={{ color: "rgba(255,255,255,0.8)" }}>
            <span><i data-lucide="clock" width="11" height="11"></i> 2h 14m</span>
            <span><i data-lucide="layers" width="11" height="11"></i> 312 layers</span>
          </div>
        </div>
      </div>
    </CollapsibleInfo>
    <div className="btn-row" style={{ marginTop: 14 }}>
      <GlassButton variant="primary" icon="navigation" full onClick={onAdvance}>Navigate to Printer</GlassButton>
    </div>
  </GlassCard>
);

const Card_Navigate = ({ distance, eta, onArrive }) => (
  <GlassCard>
    <StepTag>Step 16 · Walk to Printer</StepTag>
    <CardTitle>Follow the floor anchor</CardTitle>
    <div className="nav-anchor">
      <i data-lucide="navigation" width="18" height="18"></i>
      <div className="nav-anchor-text">
        <strong>Bay 2 · The Bust</strong><br/>Walk straight ahead
      </div>
      <div className="nav-anchor-distance">{distance}m</div>
    </div>
    <div className="btn-row">
      <GlassButton variant="primary" icon="check" full onClick={onArrive}>I've Arrived</GlassButton>
    </div>
  </GlassCard>
);

const Card_Arrived = ({ onAdvance }) => (
  <GlassCard tint="blue">
    <StepTag>Step 17 · You've Arrived</StepTag>
    <CardTitle>You're at the right printer</CardTitle>
    <AlertBox tone="info" icon="thermometer">
      <strong>Don't open yet</strong> — plate is still hot. Checking temperature now.
    </AlertBox>
    <div className="btn-row">
      <GlassButton variant="primary" icon="chevron-right" full onClick={onAdvance}>Check Temperature</GlassButton>
    </div>
  </GlassCard>
);

const Card_CoolingHot = ({ temp, eta, onAdvance, onSpeedup }) => (
  <GlassCard tint="red">
    <StepTag>Step 18 · Cooling</StepTag>
    <CardTitle>Do not touch — plate is hot</CardTitle>
    <div className="temp-ring">
      <TempRing temp={temp} mode="hot" eta={`~${eta}`} />
      <div className="temp-meta">
        <div className="temp-state hot">Hot · Do Not Touch</div>
        <div className="temp-msg">Surface is <strong>{Math.round(temp)}°C</strong>.<br/>Auto-advancing at 45°C.</div>
        <div className="temp-eta">Safe in ~{eta}</div>
      </div>
    </div>
    <CollapsibleInfo label="Why can't I touch it yet?" icon="alert-triangle" tone="warn">
      <p style={{ fontSize: 13, color: "rgba(255,255,255,0.8)", margin: "4px 0 0", lineHeight: 1.5 }}>
        Touching the plate above 45°C can cause burns and warp the model. The plate auto-advances when safe.
      </p>
      <TempLegend temp={temp} />
    </CollapsibleInfo>
    <div className="btn-row">
      <GlassButton variant="ghost" icon="fast-forward" onClick={onSpeedup}>Speed Up Demo</GlassButton>
    </div>
  </GlassCard>
);

const Card_CoolingWarm = ({ temp, eta, onAdvance, onSpeedup, onDoorOpen, doorOpen }) => (
  <GlassCard tint="orange">
    <StepTag>Step 19 · Almost Cool</StepTag>
    <CardTitle>Open the door to vent heat</CardTitle>
    <div className="temp-ring">
      <TempRing temp={temp} mode="warm" eta={`~${eta}`} />
      <div className="temp-meta">
        <div className="temp-state warm">Warm · Almost There</div>
        <div className="temp-msg">Surface is <strong>{Math.round(temp)}°C</strong>.</div>
        <div className="temp-eta">Safe in ~{eta}</div>
      </div>
    </div>
    <div className="btn-row">
      <GlassButton variant="ghost" icon="fast-forward" onClick={onSpeedup}>Speed Up Demo</GlassButton>
      <GlassButton
        variant={doorOpen ? "success" : "primary"}
        icon={doorOpen ? "check" : "door-open"}
        onClick={!doorOpen ? onDoorOpen : undefined}
      >
        {doorOpen ? "Door Is Open" : "Door Opened"}
      </GlassButton>
    </div>
  </GlassCard>
);

const Card_CoolingSafe = ({ temp, onAdvance }) => (
  <GlassCard tint="green">
    <StepTag>Step 20 · Safe to Touch</StepTag>
    <CardTitle>Ready — remove the build plate</CardTitle>
    <div className="temp-ring">
      <TempRing temp={temp} mode="safe" eta="SAFE" />
      <div className="temp-meta">
        <div className="temp-state safe">Safe to Touch</div>
        <div className="temp-msg" style={{ color: "#fff" }}>Plate at <strong>{Math.round(temp)}°C</strong> — good to go.</div>
      </div>
    </div>
    <div className="btn-row" style={{ marginTop: 4 }}>
      <GlassButton variant="primary" icon="hand" full onClick={onAdvance}>Remove the Build Plate</GlassButton>
    </div>
  </GlassCard>
);

const REMOVE_PREP_STEPS = [
  { id: "door",  label: <>Open the front door <strong>fully</strong> until it locks open</> },
  { id: "grip",  label: <>Grip the plate by its <strong>front tabs</strong> with both hands</> },
  { id: "slide", label: <>Slide it <strong>straight out</strong> — magnets release after 2 cm</> },
];

// Top-down view of plate removal — animates in sync with the three checklist steps
const RemovePlateDiagram = ({ checks, plateExiting }) => {
  const doneCount = checks.filter(c => c.done).length;
  const slideY = plateExiting ? 130 : (doneCount >= 3 ? 40 : 0);
  const slideDur = plateExiting ? "650ms" : "750ms";
  return (
    <svg viewBox="0 0 280 188" overflow="visible"
         style={{ width: "100%", height: "auto", display: "block" }}
         aria-label="Build plate removal sequence">
      <defs>
        <linearGradient id="rpBody" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#2c2f35"/>
          <stop offset="100%" stopColor="#16181c"/>
        </linearGradient>
        <linearGradient id="rpPlate" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#3a3d44"/>
          <stop offset="100%" stopColor="#22252b"/>
        </linearGradient>
      </defs>

      {/* Printer body outline (top-down view) */}
      <rect x="28" y="8" width="224" height="110" rx="10"
            fill="url(#rpBody)" stroke="rgba(255,255,255,0.10)" strokeWidth="1.5"/>
      <text x="140" y="24" textAnchor="middle" fontSize="8" fontWeight="700"
            fill="rgba(255,255,255,0.28)" letterSpacing="1.5">TOP VIEW</text>

      {/* Door panel — fades out when step 1 done */}
      <g style={{ opacity: doneCount >= 1 ? 0 : 1, transition: "opacity 500ms ease" }}>
        <rect x="28" y="97" width="224" height="21" rx="0"
              fill="rgba(160,210,255,0.13)" stroke="rgba(160,210,255,0.32)" strokeWidth="1"/>
        <text x="140" y="111" textAnchor="middle" fontSize="8" fontWeight="600"
              fill="rgba(255,255,255,0.38)">DOOR</text>
      </g>

      {/* Door-open indicator: thin blue line at printer opening */}
      <line x1="28" y1="118" x2="252" y2="118"
            stroke="rgba(10,132,255,0.55)" strokeWidth="2"
            style={{ opacity: doneCount >= 1 ? 1 : 0, transition: "opacity 500ms ease 200ms" }}/>

      {/* Build plate group — slides out on step 3, exits on plateExiting */}
      <g style={{
        transform: `translateY(${slideY}px)`,
        transition: `transform ${slideDur} cubic-bezier(0.32,0.72,0,1)`,
      }}>
        {/* Plate surface */}
        <rect x="58" y="30" width="164" height="68" rx="4"
              fill="url(#rpPlate)" stroke="rgba(255,255,255,0.16)" strokeWidth="1"/>
        {/* Texture grid */}
        {Array.from({ length: 9 }).map((_, i) => (
          <line key={i} x1={58 + i * 20.5} y1="30" x2={58 + i * 20.5} y2="98"
                stroke="rgba(255,255,255,0.035)" strokeWidth="1"/>
        ))}
        {/* Model — white (top-down view, cat reads as white rectangle at this scale) */}
        <rect x="116" y="50" width="48" height="30" rx="3" fill="rgba(255,255,255,0.90)"/>
        <rect x="120" y="54" width="40" height="2" fill="rgba(0,0,0,0.08)"/>

        {/* Front tabs */}
        <rect x="78" y="93" width="22" height="10" rx="3"
              fill="rgba(255,255,255,0.12)" stroke="rgba(255,255,255,0.28)" strokeWidth="1"/>
        <rect x="180" y="93" width="22" height="10" rx="3"
              fill="rgba(255,255,255,0.12)" stroke="rgba(255,255,255,0.28)" strokeWidth="1"/>

        {/* Hands — appear at step 2 */}
        {doneCount >= 2 && (
          <>
            {/* Left hand — HOLD */}
            <g style={{ animation: "rpHandIn 400ms cubic-bezier(0.32,0.72,0,1) both" }}>
              <path d="M 52 90 Q 46 92,46 100 L 46 120 Q 46 126,52 126 L 76 126 Q 80 126,80 120 L 80 96 Q 80 90,74 90 Z"
                    fill="rgba(10,132,255,0.80)" stroke="#fff" strokeWidth="1.5"/>
              <text x="63" y="112" textAnchor="middle" fontSize="8" fontWeight="700" fill="#fff">HOLD</text>
            </g>
            {/* Right hand — GRIP */}
            <g style={{ animation: "rpHandIn 400ms cubic-bezier(0.32,0.72,0,1) 180ms both" }}>
              <path d="M 200 90 Q 194 92,194 100 L 194 120 Q 194 126,200 126 L 228 126 Q 232 126,232 120 L 232 96 Q 232 90,226 90 Z"
                    fill="rgba(48,209,88,0.80)" stroke="#fff" strokeWidth="1.5"/>
              <text x="213" y="112" textAnchor="middle" fontSize="8" fontWeight="700" fill="#fff">GRIP</text>
            </g>
          </>
        )}
      </g>

      {/* Slide-out arrow + label — appears at step 3 */}
      {doneCount >= 3 && (
        <g style={{ animation: "rpFadeIn 500ms ease 350ms both" }}>
          <path d="M 140 162 L 140 176 M 132 167 L 140 176 L 148 167"
                stroke="var(--green)" strokeWidth="2.5"
                strokeLinecap="round" strokeLinejoin="round" fill="none"/>
          <text x="140" y="186" textAnchor="middle" fontSize="9" fontWeight="700"
                fill="var(--green)" letterSpacing="0.5">SLIDING OUT</text>
        </g>
      )}
    </svg>
  );
};

const Card_RemovePrep = ({ onAdvance, checks, plateExiting }) => {
  const allDone = checks.every(c => c.done);
  return (
    <GlassCard>
      <StepTag>Step 21 · Remove Plate</StepTag>
      <CardTitle>Slide the build plate out</CardTitle>

      <div className="remove-plate-diagram">
        <RemovePlateDiagram checks={checks} plateExiting={plateExiting} />
      </div>

      <CollapsibleInfo label="Step-by-step instructions" icon="list" tone="neutral">
        <ul className="lift-checklist" style={{ marginTop: 8 }}>
          {REMOVE_PREP_STEPS.map((s, i) => {
            const done = checks[i] && checks[i].done;
            return (
              <li key={s.id} className={done ? "done" : ""}>
                <span className="lc-num">{done ? "✓" : i + 1}</span>
                <span className="lc-text">{s.label}</span>
              </li>
            );
          })}
        </ul>
        <p style={{ fontSize: 12, color: "rgba(255,255,255,0.6)", margin: "8px 0 0" }}>
          Set the plate flat on a clean bench — never on its side.
        </p>
      </CollapsibleInfo>

      <div className="btn-row">
        <GlassButton variant="primary" icon="chevron-right" full disabled={!allDone} onClick={onAdvance}>
          {allDone ? "Plate Is Out" : "Following the steps…"}
        </GlassButton>
      </div>
    </GlassCard>
  );
};

const Card_LiftModel = ({ checks, onToggle, onAdvance, onStuck }) => {
  const allDone = checks.every(c => c.done);
  return (
    <GlassCard>
      <StepTag>Step 22 · Lift Model</StepTag>
      <CardTitle>Lift your model off the plate</CardTitle>
      <ul className="lift-checklist">
        {checks.map((c, i) => (
          <li key={c.id} className={c.done ? "done" : ""} onClick={() => onToggle(c.id)}>
            <Checkbox checked={c.done} onChange={() => onToggle(c.id)} />
            <span className="lc-text">{c.label}</span>
          </li>
        ))}
      </ul>
      <CollapsibleInfo label="Lift tips" icon="info" tone="neutral">
        <p style={{ fontSize: 13, color: "rgba(255,255,255,0.8)", margin: "4px 0 0", lineHeight: 1.5 }}>
          Flex the plate gently — most prints pop off. Do not force if still stuck.
        </p>
      </CollapsibleInfo>
      <div className="btn-row">
        <GlassButton variant="ghost" icon="alert-triangle" onClick={onStuck}>Model Is Stuck</GlassButton>
        <GlassButton variant="primary" icon="check" disabled={!allDone} onClick={onAdvance}>
          {allDone ? "Model Removed" : `${checks.filter(c=>c.done).length}/${checks.length} ready`}
        </GlassButton>
      </div>
    </GlassCard>
  );
};

const Card_Stuck = ({ onAdvance, onCallStaff, staffNotified }) => (
  <GlassCard tint="orange">
    <StepTag>Step 23 · Model Stuck</StepTag>
    <CardTitle>Don't force it</CardTitle>
    <ul className="lift-checklist">
      <li>
        <span className="lc-num">1</span>
        <span className="lc-text"><strong>Flex the plate</strong> in both directions</span>
      </li>
      <li>
        <span className="lc-num">2</span>
        <span className="lc-text">Wait <strong>2 more minutes</strong> — cooling releases the bond</span>
      </li>
      <li>
        <span className="lc-num">3</span>
        <span className="lc-text">Use the <strong>plastic spudger</strong> under one corner</span>
      </li>
    </ul>
    <CollapsibleInfo label="What not to use" icon="alert-triangle" tone="warn">
      <p style={{ fontSize: 13, color: "rgba(255,255,255,0.8)", margin: "4px 0 0", lineHeight: 1.5 }}>
        Never use knives, screwdrivers, or pliers — they damage the PEI coating. Call staff if it won't budge.
      </p>
    </CollapsibleInfo>
    <div className="btn-row">
      <GlassButton variant="primary" icon="check" onClick={onAdvance}>It Came Off</GlassButton>
      <GlassButton variant="danger" icon="phone" onClick={onCallStaff} disabled={staffNotified}>
        {staffNotified ? "Staff Notified" : "Call Staff"}
      </GlassButton>
    </div>
  </GlassCard>
);

const Card_Inspect = ({ rating, onRate, onAdvance }) => (
  <GlassCard>
    <StepTag>Step 24 · Inspect Print</StepTag>
    <CardTitle>How does it look?</CardTitle>
    <div className="rating-row">
      {[
        { k: "great", emoji: "🤩", lbl: "Great" },
        { k: "ok",    emoji: "🙂", lbl: "OK" },
        { k: "issue", emoji: "🤔", lbl: "Issue" },
      ].map(r => (
        <button
          key={r.k}
          className={`rating-btn ${rating === r.k ? "selected" : ""}`}
          onClick={() => onRate(r.k)}
        >
          <span className="emoji">{r.emoji}</span>
          <span className="lbl">{r.lbl}</span>
        </button>
      ))}
    </div>
    {rating === "issue" && (
      <AlertBox tone="info" icon="sparkles">
        Saving these settings to improve your next attempt.
      </AlertBox>
    )}
    <CollapsibleInfo label="What to look for" icon="search" tone="neutral">
      <p style={{ fontSize: 13, color: "rgba(255,255,255,0.8)", margin: "4px 0 0", lineHeight: 1.5 }}>
        Check for scuffs, gaps between layers, or weak spots. Your rating helps PANDA tune settings for next time.
      </p>
    </CollapsibleInfo>
    <div className="btn-row">
      <GlassButton variant="primary" icon="chevron-right" full disabled={!rating} onClick={onAdvance}>
        {rating ? "Continue" : "Pick a rating"}
      </GlassButton>
    </div>
  </GlassCard>
);

const Card_Reseat = ({ checks, onToggle, onAdvance }) => {
  const allDone = checks.every(c => c.done);
  return (
    <GlassCard>
      <StepTag>Step 25 · Reset Printer</StepTag>
      <CardTitle>Place the plate back in</CardTitle>
      <ul className="lift-checklist">
        {checks.map((c, i) => (
          <li key={c.id} className={c.done ? "done" : ""} onClick={() => onToggle(c.id)}>
            <Checkbox checked={c.done} onChange={() => onToggle(c.id)} />
            <span className="lc-text">{c.label}</span>
          </li>
        ))}
      </ul>
      <div className="btn-row">
        <GlassButton variant="primary" icon="check" full disabled={!allDone} onClick={onAdvance}>
          {allDone ? "Printer Reset" : `${checks.filter(c=>c.done).length}/${checks.length} done`}
        </GlassButton>
      </div>
    </GlassCard>
  );
};

const Card_WrapUp = ({ totalTime, onRestart }) => (
  <GlassCard tint="green">
    <StepTag>Step 26 · All Done</StepTag>
    <div className="success-burst">
      <div className="sb-icon"><i data-lucide="party-popper" width="22" height="22"></i></div>
      <div className="sb-title">First print complete!</div>
      <div className="sb-sub">Nicely done — you handled the whole flow yourself.</div>
    </div>
    <Tag tone="purple" icon="sparkles" style={{ marginTop: 12 }}>PANDA Profile · Beginner → Apprentice</Tag>
    <CollapsibleInfo label="Print summary" icon="bar-chart-2" tone="neutral">
      <div className="stats-row" style={{ marginTop: 8 }}>
        <StatBox value={totalTime} label="Total time" />
        <StatBox value="312" label="Layers" />
      </div>
      <div className="stats-row">
        <StatBox value="32g" label="PLA used" sub="≈ $0.85" />
        <StatBox value="1" label="Prints today" sub="this week: 1" />
      </div>
      <div style={{ marginTop: 10, display: "flex", flexDirection: "column", gap: 6 }}>
        <Tag tone="green" icon="check-circle-2">Plate Reseated</Tag>
        <Tag tone="green" icon="check-circle-2">Printer Ready for Next User</Tag>
      </div>
    </CollapsibleInfo>
    <div className="btn-row" style={{ marginTop: 14 }}>
      <GlassButton variant="primary" icon="rotate-ccw" full onClick={onRestart}>Replay From Step 15</GlassButton>
    </div>
  </GlassCard>
);

// ============ Spatial pins per step (Phase 5) ============
// All pins anchored to top-right of the printer for consistency.
// (navigate/wrap-up steps don't have a printer in view — keep their own positioning.)
const PRINTER_PIN = { x: 70, y: 20 };
const PH5_PINS = {
  "complete":     [{ ...PRINTER_PIN, label: "Print ready", tone: "green", icon: "check-circle-2" }],
  "navigate":     [{ ...PRINTER_PIN, label: "Walk to Bay A", tone: "blue", icon: "navigation" }],
  "arrived":      [{ ...PRINTER_PIN, label: "This printer", tone: "blue", icon: "map-pin" }],
  "cooling-hot":  [{ ...PRINTER_PIN, label: "Hot · 52°C", tone: "red", icon: "flame" }],
  "cooling-warm": [{ ...PRINTER_PIN, label: "Warm · 42°C", tone: "orange", icon: "thermometer" }],
  "cooling-safe": [{ ...PRINTER_PIN, label: "Safe · 32°C", tone: "green", icon: "snowflake" }],
  "remove-prep":  [{ ...PRINTER_PIN, label: "Pull straight", tone: "blue", icon: "move-horizontal" }],
  "lift-model":   [{ ...PRINTER_PIN, label: "Lift here", tone: "green", icon: "hand" }],
  "stuck":        [{ ...PRINTER_PIN, label: "Flex gently", tone: "orange", icon: "alert-triangle" }],
  "inspect":      [{ ...PRINTER_PIN, label: "Inspect", tone: "purple", icon: "search" }],
  "reseat":       [{ ...PRINTER_PIN, label: "Slide back in", tone: "blue", icon: "move-horizontal" }],
  "wrap-up":      [{ ...PRINTER_PIN, label: "All done", tone: "green", icon: "sparkles" }],
};

// ============ Ask AI suggestions per step ============
const PH5_AI_SUGGESTIONS = {
  "complete":     ["Take me to the printer.", "How do I remove the print?", "When will it be cool?"],
  "navigate":     ["How far is it?", "Which printer is mine?", "Can I just wait here?"],
  "arrived":     ["Is it safe to open?", "Why is the plate hot?", "How long is cool-down?"],
  "cooling-hot":  ["Can I touch it now?", "Why is it taking so long?", "Can I open the door?"],
  "cooling-warm": ["Is it safe yet?", "Should I open the door?", "Will it cool faster?"],
  "cooling-safe": ["How do I remove the plate?", "Can I touch the model?", "Where do I set it down?"],
  "remove-prep":  ["Where do I grip the plate?", "What if it doesn't slide?", "Can I damage the plate?"],
  "lift-model":   ["What if it won't lift?", "Can I damage the plate?", "How hard should I pull?"],
  "stuck":        ["What's a spudger?", "How long do I wait?", "Should I call staff?"],
  "inspect":      ["What is layer separation?", "Why is the surface rough?", "Save this for next print."],
  "reseat":       ["Does it matter which way?", "Do I need to clean it?", "Where do I leave the model?"],
  "wrap-up":      ["Show me the print log.", "Print this again next week.", "Email me the file."],
};

const PH5_AI_FALLBACKS = {
  "Take me to the printer.": "Bay 2 — Bambu X1 Carbon, The Bust. I'll keep a blue waypoint on the floor until you get there.",
  "Can I touch it now?": "Not yet. The plate is at 52°C — that will burn. I'll auto-advance the moment it crosses 45°C.",
  "Is it safe yet?": "Almost. We're at 42°C — I want it under 35°C before you grip the plate. About 30 seconds.",
  "How do I remove the plate?": "Open the door fully, grip both front tabs, and pull straight toward you. Magnets release after about 2 cm.",
  "What if it won't lift?": "Don't force it. Flex the plate in both directions like a thin book — that pops most prints free. If not, give it two more minutes to cool.",
  "What's a spudger?": "A flat plastic pry tool. There's one in the supplies drawer next to the printer, marked 'PRINT TOOLS'.",
};

// ============ Confetti layer (final step) ============
const Confetti = ({ active }) => {
  const pieces = useMemo(() => Array.from({ length: 40 }, (_, i) => ({
    left: Math.random() * 100,
    delay: Math.random() * 1.2,
    color: ["#0A84FF", "#30D158", "#FF9F0A", "#BF5AF2", "#FFD60A"][i % 5],
    rotate: Math.random() * 360,
  })), []);
  if (!active) return null;
  return (
    <div className="confetti-layer">
      {pieces.map((p, i) => (
        <div key={i} className="confetti-piece" style={{
          left: `${p.left}%`,
          background: p.color,
          animationDelay: `${p.delay}s`,
          transform: `rotate(${p.rotate}deg)`,
        }}></div>
      ))}
    </div>
  );
};

// ============ Plate reseat scene (Step 25) ============
// Blurred printer behind, clear AR overlay showing the empty plate sliding back into the printer.
// Model is absent — it was removed in Step 24.
const PlateReseatScene = ({ checks }) => {
  const doneCount = checks.filter(c => c.done).length;

  // Plate slides from off-screen right into the slot
  const plateOffX = doneCount >= 2 ? 0 : doneCount >= 1 ? 86 : 218;

  // LED bar width tracks progress
  const ledPct = (doneCount / 3) * 204;
  const ledColor = doneCount >= 3 ? "rgba(48,209,88,0.7)" : "rgba(10,132,255,0.55)";

  return (
    <div className="plate-reseat-scene">
      <svg viewBox="0 0 310 200" overflow="hidden"
           style={{ width: "100%", height: "100%" }}>
        <defs>
          <linearGradient id="rsChassis" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#2c2f35"/>
            <stop offset="100%" stopColor="#18191e"/>
          </linearGradient>
          <linearGradient id="rsPlate" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#3a3d44"/>
            <stop offset="100%" stopColor="#22252b"/>
          </linearGradient>
        </defs>

        {/* ── Printer chassis ── */}
        <rect x="10" y="10" width="270" height="178" rx="12"
              fill="url(#rsChassis)" stroke="rgba(255,255,255,0.10)" strokeWidth="1.5"/>

        {/* Brand strip */}
        <rect x="10" y="10" width="270" height="18" rx="12 12 0 0"
              fill="rgba(255,255,255,0.05)"/>
        <text x="90" y="22" fontSize="7.5" fontWeight="700"
              fill="rgba(255,255,255,0.40)" letterSpacing="0.8">The Bust · MakerLAB Bay A</text>

        {/* Glass enclosure */}
        <rect x="18" y="30" width="210" height="108" rx="4"
              fill="rgba(160,210,255,0.05)" stroke="rgba(255,255,255,0.13)" strokeWidth="1"/>

        {/* LED progress bar (top of enclosure) */}
        <rect x="20" y="30" width="204" height="4" rx="2" fill="rgba(255,255,255,0.06)"/>
        <rect x="20" y="30" width={ledPct} height="4" rx="2"
              fill={ledColor}
              style={{ transition: "width 800ms cubic-bezier(0.32,0.72,0,1), fill 400ms ease" }}/>

        {/* Chamber interior — empty */}
        <rect x="20" y="36" width="204" height="100" rx="2" fill="rgba(0,0,0,0.14)"/>

        {/* Gantry rail */}
        <rect x="22" y="42" width="200" height="4" rx="2" fill="rgba(255,255,255,0.11)"/>
        {/* Print head */}
        <rect x="88" y="38" width="32" height="12" rx="3" fill="rgba(255,255,255,0.16)"/>
        <rect x="102" y="50" width="4" height="7" rx="1" fill="rgba(255,255,255,0.20)"/>

        {/* Empty plate slot indicator (dashed outline inside chamber) */}
        <rect x="24" y="100" width="196" height="30" rx="2"
              fill="rgba(10,132,255,0.04)" stroke="rgba(10,132,255,0.18)"
              strokeWidth="1" strokeDasharray="4 4"/>
        <text x="122" y="119" textAnchor="middle" fontSize="7.5" fontWeight="600"
              fill="rgba(10,132,255,0.35)" letterSpacing="0.5">PLATE SLOT</text>

        {/* Glass reflection */}
        <rect x="18" y="30" width="52" height="108" rx="4 0 0 4"
              fill="rgba(255,255,255,0.03)"/>

        {/* Front slot opening — plate enters here */}
        <rect x="18" y="136" width="210" height="26" rx="0"
              fill="rgba(0,0,0,0.32)" stroke="rgba(255,255,255,0.07)" strokeWidth="1"/>

        {/* ── Empty plate sliding in ── */}
        <g style={{
          transform: `translateX(${plateOffX}px)`,
          transition: "transform 840ms cubic-bezier(0.32,0.72,0,1)",
        }}>
          <rect x="20" y="138" width="202" height="18" rx="4"
                fill="url(#rsPlate)" stroke="rgba(255,255,255,0.16)" strokeWidth="1.5"/>
          {Array.from({ length: 10 }).map((_, i) => (
            <line key={i} x1={20 + i * 20.2} y1="138" x2={20 + i * 20.2} y2="156"
                  stroke="rgba(255,255,255,0.04)" strokeWidth="1"/>
          ))}
          {/* Tab nubs */}
          <rect x="34" y="153" width="14" height="6" rx="2"
                fill="rgba(255,255,255,0.07)" stroke="rgba(255,255,255,0.16)" strokeWidth="1"/>
          <rect x="174" y="153" width="14" height="6" rx="2"
                fill="rgba(255,255,255,0.07)" stroke="rgba(255,255,255,0.16)" strokeWidth="1"/>
        </g>

        {/* Door panel — closes on check 3 */}
        <rect x="18" y="136" width="210" height="26" rx="0"
              fill="rgba(160,210,255,0.14)" stroke="rgba(160,210,255,0.38)" strokeWidth="1"
              style={{ opacity: doneCount >= 3 ? 1 : 0, transition: "opacity 550ms ease 200ms" }}/>
        {doneCount >= 3 && (
          <text x="123" y="152" textAnchor="middle" fontSize="8" fontWeight="600"
                fill="rgba(160,210,255,0.70)"
                style={{ animation: "rpFadeIn 400ms ease 300ms both" }}>DOOR CLOSED</text>
        )}

        {/* Front bezel */}
        <rect x="18" y="164" width="210" height="22" rx="0 0 4px 4px"
              fill="rgba(255,255,255,0.03)" stroke="rgba(255,255,255,0.06)" strokeWidth="0.5"/>
        {/* Touchscreen */}
        <rect x="28" y="168" width="56" height="13" rx="2" fill="rgba(0,0,0,0.45)"/>
        <rect x="30" y="170" width="52" height="9" rx="1"
              fill={doneCount >= 3 ? "rgba(48,209,88,0.15)" : "rgba(10,132,255,0.12)"}
              stroke={doneCount >= 3 ? "rgba(48,209,88,0.4)" : "rgba(10,132,255,0.28)"} strokeWidth="0.5"
              style={{ transition: "fill 400ms ease, stroke 400ms ease" }}/>
        <text x="56" y="177" textAnchor="middle" fontSize="6" fontWeight="600"
              fill={doneCount >= 3 ? "rgba(48,209,88,0.8)" : "rgba(255,255,255,0.45)"}>
          {doneCount >= 3 ? "Ready" : "X1 Carbon"}
        </text>
        {/* Power button */}
        <circle cx="196" cy="174" r="5" fill="rgba(255,255,255,0.06)"
                stroke="rgba(255,255,255,0.18)" strokeWidth="1"/>

        {/* Side spool dock */}
        <rect x="232" y="34" width="44" height="100" rx="4"
              fill="rgba(255,255,255,0.03)" stroke="rgba(255,255,255,0.07)" strokeWidth="1"/>
        <circle cx="254" cy="84" r="26" fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth="1"/>
        {[18, 22].map((r, i) => (
          <circle key={i} cx="254" cy="84" r={r} fill="none"
                  stroke="rgba(255,255,255,0.05)" strokeWidth="3"/>
        ))}
        <circle cx="254" cy="84" r="10" fill="rgba(255,255,255,0.05)"
                stroke="rgba(255,255,255,0.10)" strokeWidth="1"/>

        {/* Base feet */}
        <rect x="30" y="184" width="36" height="4" rx="2" fill="rgba(255,255,255,0.08)"/>
        <rect x="244" y="184" width="36" height="4" rx="2" fill="rgba(255,255,255,0.08)"/>

        {/* Floor shadow */}
        <ellipse cx="145" cy="196" rx="132" ry="6" fill="rgba(0,0,0,0.35)"/>
      </svg>
    </div>
  );
};

// ============ Plate + Model focus overlay (Steps 22–25) ============
// Borderless hero view — blurred printer behind it, plate + model in realistic motion.
const PlateModelFocus = ({ stepId, liftChecks, spudgerActive }) => {
  const liftDone = liftChecks ? liftChecks.filter(c => c.done).length : 0;

  const isLift    = stepId === "lift-model";
  const isStuck   = stepId === "stuck";
  const isInspect = stepId === "inspect";

  // Model peels off plate — rotates around its left edge so the right side lifts first.
  const liftedByHand   = isLift && liftDone >= 2;
  const priedBySpudger = isStuck && spudgerActive;
  const modelTransform =
    isInspect        ? "translateY(-50px)"
    : liftedByHand   ? "translateY(-26px) rotate(-6deg)"
    : priedBySpudger ? "translateY(-9px)  rotate(-4deg)"
    : "translateY(0px) rotate(0deg)";

  // Floor shadow under model shrinks as model rises
  const modelShadowRx = isInspect ? 28 : liftedByHand ? 46 : priedBySpudger ? 58 : 64;

  return (
    <div className="plate-focus-overlay">
      <svg viewBox="0 0 340 240" overflow="visible"
           style={{ width: "100%", height: "100%", maxWidth: 500 }}>
        <defs>
          <linearGradient id="pmPlate" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#3a3d44"/>
            <stop offset="100%" stopColor="#22252b"/>
          </linearGradient>
          <linearGradient id="pmPlateEdge" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#1a1d21"/>
            <stop offset="100%" stopColor="#0d0e11"/>
          </linearGradient>
          <filter id="pmDropDeep" x="-25%" y="-20%" width="150%" height="180%">
            <feDropShadow dx="0" dy="12" stdDeviation="14" floodColor="#000" floodOpacity="0.60"/>
          </filter>
          <filter id="pmDropLight" x="-20%" y="-20%" width="140%" height="160%">
            <feDropShadow dx="0" dy="5" stdDeviation="7" floodColor="#000" floodOpacity="0.42"/>
          </filter>
        </defs>

        {/* Plate floor shadow */}
        <ellipse cx="170" cy="200" rx="118" ry="7" fill="rgba(0,0,0,0.30)"/>

        {/* Model contact shadow — shrinks as model lifts */}
        <ellipse cx="170" cy="154" rx={modelShadowRx} ry="5" fill="rgba(0,0,0,0.28)"
                 style={{ transition: "rx 680ms cubic-bezier(0.32,0.72,0,1)" }}/>

        {/* ── Main group: plate + model + hands ── */}
        <g>

          {/* Plate bottom depth edge (3-D illusion) */}
          <rect x="32" y="172" width="278" height="10" rx="0 0 6px 6px"
                fill="url(#pmPlateEdge)" opacity="0.85"/>

          {/* Plate top surface */}
          <rect x="30" y="152" width="280" height="22" rx="6"
                fill="url(#pmPlate)" stroke="rgba(255,255,255,0.14)" strokeWidth="1.5"
                filter="url(#pmDropDeep)"/>
          {Array.from({ length: 13 }).map((_, i) => (
            <line key={i} x1={30 + i * 21.5} y1="152" x2={30 + i * 21.5} y2="174"
                  stroke="rgba(255,255,255,0.04)" strokeWidth="1"/>
          ))}
          {/* Front-tab nubs */}
          <rect x="50" y="170" width="18" height="8" rx="2"
                fill="rgba(255,255,255,0.07)" stroke="rgba(255,255,255,0.18)" strokeWidth="1"/>
          <rect x="272" y="170" width="18" height="8" rx="2"
                fill="rgba(255,255,255,0.07)" stroke="rgba(255,255,255,0.18)" strokeWidth="1"/>

          {/* ── Model group — peels from left edge when lifted ── */}
          <g style={{
            transform: modelTransform,
            transformBox: "fill-box",
            transformOrigin: "left center",
            transition: "transform 680ms cubic-bezier(0.32,0.72,0,1)",
          }}>
            {/* Cat silhouette — white, same size Steps 22–24 */}
            {/* Body bottom sits at y=152 (plate surface). Ears reach y=96. Width=88px centered at x=170. */}
            <polygon points="128,116 142,96 155,116" fill="rgba(255,255,255,0.95)"
                     filter="url(#pmDropLight)"/>
            <polygon points="185,116 198,96 212,116" fill="rgba(255,255,255,0.95)"
                     filter="url(#pmDropLight)"/>
            <rect x="126" y="114" width="88" height="38" rx="6"
                  fill="rgba(255,255,255,0.95)" filter="url(#pmDropLight)"/>
            {[120,126,132,138,144,150].map(y => (
              <line key={y} x1="126" y1={y} x2="214" y2={y}
                    stroke="rgba(0,0,0,0.08)" strokeWidth="0.8"/>
            ))}

            {/* Inspect magnifier — positioned above the cat */}
            {isInspect && (
              <g style={{ animation: "rpFadeIn 500ms ease 200ms both" }}>
                <circle cx="170" cy="84" r="26" fill="none"
                        stroke="rgba(191,90,242,0.65)" strokeWidth="2.5"/>
                <circle cx="170" cy="84" r="19" fill="rgba(191,90,242,0.07)"/>
                <line x1="189" y1="101" x2="204" y2="116"
                      stroke="rgba(191,90,242,0.65)" strokeWidth="3.5" strokeLinecap="round"/>
              </g>
            )}
          </g>

          {/* ── HOLD hand — grips plate on left side (check 1) ── */}
          {isLift && liftDone >= 1 && (
            <g style={{ animation: "rpHandIn 380ms ease both" }}>
              <path d="M 22 150 Q 16 152,16 160 L 16 178 Q 16 184,22 184 L 48 184 Q 52 184,52 178 L 52 156 Q 52 150,46 150 Z"
                    fill="rgba(10,132,255,0.82)" stroke="#fff" strokeWidth="1.5"/>
              <text x="34" y="170" textAnchor="middle" fontSize="8" fontWeight="700" fill="#fff">HOLD</text>
            </g>
          )}

          {/* ── LIFT hand — at model's right edge (check 2) ── */}
          {isLift && liftDone >= 2 && (
            <g style={{ animation: "rpHandIn 380ms ease 140ms both" }}>
              <path d="M 228 148 Q 222 150,222 158 L 222 178 Q 222 184,228 184 L 263 184 Q 267 184,267 178 L 267 154 Q 267 148,261 148 Z"
                    fill="rgba(48,209,88,0.82)" stroke="#fff" strokeWidth="1.5"/>
              <text x="244" y="170" textAnchor="middle" fontSize="8" fontWeight="700" fill="#fff">LIFT</text>
              <path d="M 244 140 L 244 124 M 238 131 L 244 124 L 250 131"
                    stroke="var(--green)" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"
                    fill="none" style={{ animation: "pmLiftPulse 1.4s ease-in-out infinite" }}/>
            </g>
          )}

          {/* ── Spudger — slides in from right under model's right corner ── */}
          {isStuck && (
            <g style={{
              transform: spudgerActive ? "translateX(0)" : "translateX(168px)",
              transition: "transform 720ms cubic-bezier(0.32,0.72,0,1)",
            }}>
              {/* Wedge tip pointing left */}
              <polygon points="213,142 213,154 236,148"
                       fill="rgba(100,185,255,0.94)" stroke="rgba(255,255,255,0.55)" strokeWidth="1"/>
              {/* Handle body */}
              <rect x="236" y="144" width="92" height="8" rx="2"
                    fill="rgba(100,185,255,0.94)" stroke="rgba(255,255,255,0.55)" strokeWidth="1"/>
              {/* Label above */}
              <text x="282" y="138" textAnchor="middle" fontSize="7" fontWeight="600"
                    fill="rgba(255,255,255,0.65)" letterSpacing="0.5">SPUDGER</text>
            </g>
          )}
        </g>
      </svg>
    </div>
  );
};

// ============ Main App ============
const App = () => {
  const [stepId, setStepId] = useState("complete");
  const [visited, setVisited] = useState(new Set(["complete"]));

  // Live state
  const [plateTemp, setPlateTemp] = useState(58);
  const [walkDistance, setWalkDistance] = useState(12);
  const [rating, setRating] = useState(null);
  const [staffNotified, setStaffNotified] = useState(false);
  const [staffSeconds, setStaffSeconds] = useState(120);
  const [doorOpen, setDoorOpen] = useState(false);
  const [plateExiting, setPlateExiting] = useState(false);
  const [spudgerActive, setSpudgerActive] = useState(false);
  const [removePrepChecks, setRemovePrepChecks] = useState([
    { id: "door", done: false },
    { id: "grip", done: false },
    { id: "slide", done: false },
  ]);

  const [liftChecks, setLiftChecks] = useState([
    { id: "stable", label: "One hand stabilizes the plate", done: false },
    { id: "edge",   label: "One hand lifts from this edge ↗", done: false },
  ]);

  const [reseatChecks, setReseatChecks] = useState([
    { id: "align", label: "Align tabs with the slot", done: false },
    { id: "slide", label: "Slide all the way in until magnets click", done: false },
    { id: "close", label: "Close the front door", done: false },
  ]);

  // Mark visited
  useEffect(() => {
    setVisited(prev => {
      const next = new Set(prev); next.add(stepId); return next;
    });
  }, [stepId]);

  // Plate cooling animation — runs whenever we're in cooling-* steps
  useEffect(() => {
    if (stepId === "cooling-hot") {
      const t = setInterval(() => {
        setPlateTemp(p => {
          if (p <= 45.5) { setStepId("cooling-warm"); return 45; }
          return p - 0.4;
        });
      }, 220);
      return () => clearInterval(t);
    }
    if (stepId === "cooling-warm") {
      const t = setInterval(() => {
        setPlateTemp(p => {
          if (p <= 32.5) { setStepId("cooling-safe"); return 32; }
          return p - 0.4;
        });
      }, 220);
      return () => clearInterval(t);
    }
  }, [stepId]);

  // Walking animation
  useEffect(() => {
    if (stepId !== "navigate") return;
    const t = setInterval(() => {
      setWalkDistance(d => {
        if (d <= 0.5) return 0;
        return Math.max(0, d - 0.4);
      });
    }, 280);
    return () => clearInterval(t);
  }, [stepId]);

  // Staff ETA countdown
  useEffect(() => {
    if (!staffNotified) return;
    const t = setInterval(() => setStaffSeconds(s => Math.max(0, s - 1)), 1000);
    return () => clearInterval(t);
  }, [staffNotified]);

  // Reset door-open state when navigating to steps before cooling-warm
  useEffect(() => {
    if (ph5Index(stepId) < ph5Index("cooling-warm")) setDoorOpen(false);
  }, [stepId]);

  // Auto-check remove-prep steps sequentially when entering that step
  useEffect(() => {
    if (stepId !== "remove-prep") return;
    setRemovePrepChecks(c => c.map(x => ({ ...x, done: false })));
    const t1 = setTimeout(() => setRemovePrepChecks(c => c.map((x, i) => i === 0 ? { ...x, done: true } : x)), 1400);
    const t2 = setTimeout(() => setRemovePrepChecks(c => c.map((x, i) => i <= 1 ? { ...x, done: true } : x)), 3000);
    const t3 = setTimeout(() => setRemovePrepChecks(c => c.map(x => ({ ...x, done: true }))), 4600);
    return () => { clearTimeout(t1); clearTimeout(t2); clearTimeout(t3); };
  }, [stepId]);

  // Re-render lucide icons after each state change
  useEffect(() => {
    const t = setTimeout(() => window.lucide && window.lucide.createIcons(), 60);
    return () => clearTimeout(t);
  }, [stepId, plateTemp, walkDistance, rating, liftChecks, reseatChecks, staffNotified, doorOpen, removePrepChecks]);

  const advance = (id) => setStepId(id);

  // Step 21 → 22: animate plate exiting before advancing
  const handleRemovePrepAdvance = () => {
    setPlateExiting(true);
    setTimeout(() => { setPlateExiting(false); advance("lift-model"); }, 680);
  };

  // Step 23: slide spudger in, then advance to inspect
  const handleStuckAdvance = () => {
    setSpudgerActive(true);
    setTimeout(() => { setSpudgerActive(false); advance("inspect"); }, 880);
  };

  const restart = () => {
    setStepId("complete");
    setVisited(new Set(["complete"]));
    setPlateTemp(58);
    setWalkDistance(12);
    setRating(null);
    setStaffNotified(false);
    setStaffSeconds(120);
    setDoorOpen(false);
    setPlateExiting(false);
    setSpudgerActive(false);
    setLiftChecks(c => c.map(x => ({ ...x, done: false })));
    setReseatChecks(c => c.map(x => ({ ...x, done: false })));
    setRemovePrepChecks(c => c.map(x => ({ ...x, done: false })));
  };

  // Map step → printer state for SVG
  const printerState = useMemo(() => {
    if (stepId === "cooling-hot" || stepId === "cooling-warm") return "done"; // post-print, glowing
    return "done";
  }, [stepId]);

  // ETA strings
  const hotEta = useMemo(() => {
    const remainingTo45 = Math.max(0, plateTemp - 45);
    const secs = Math.ceil(remainingTo45 / 0.4 * 0.22);
    if (secs >= 60) return `${Math.floor(secs/60)}m ${(secs%60).toString().padStart(2,"0")}s`;
    return `${secs}s`;
  }, [plateTemp]);

  const warmEta = useMemo(() => {
    const remainingTo32 = Math.max(0, plateTemp - 32);
    const secs = Math.ceil(remainingTo32 / 0.4 * 0.22);
    return `${secs}s`;
  }, [plateTemp]);

  const card = (() => {
    switch (stepId) {
      case "complete":
        return <Card_Complete onAdvance={() => advance("navigate")} onDismiss={() => advance("navigate")} />;
      case "navigate":
        return <Card_Navigate
                  distance={walkDistance.toFixed(1)}
                  eta={walkDistance > 0 ? `${Math.max(1, Math.round(walkDistance * 1.5))}s` : "Arrived"}
                  onArrive={() => advance("arrived")} />;
      case "arrived":
        return <Card_Arrived onAdvance={() => advance("cooling-hot")} />;
      case "cooling-hot":
        return <Card_CoolingHot temp={plateTemp} eta={hotEta} onAdvance={() => advance("cooling-warm")}
                  onSpeedup={() => setPlateTemp(45)} />;
      case "cooling-warm":
        return <Card_CoolingWarm temp={plateTemp} eta={warmEta} onAdvance={() => advance("cooling-safe")}
                  onSpeedup={() => setPlateTemp(32)} onDoorOpen={() => setDoorOpen(true)} doorOpen={doorOpen} />;
      case "cooling-safe":
        return <Card_CoolingSafe temp={plateTemp} onAdvance={() => advance("remove-prep")} />;
      case "remove-prep":
        return <Card_RemovePrep checks={removePrepChecks} onAdvance={handleRemovePrepAdvance} plateExiting={plateExiting} />;
      case "lift-model":
        return <Card_LiftModel
                  checks={liftChecks}
                  onToggle={(id) => setLiftChecks(cs => cs.map(c => c.id === id ? { ...c, done: !c.done } : c))}
                  onAdvance={() => advance("inspect")}
                  onStuck={() => advance("stuck")} />;
      case "stuck":
        return <Card_Stuck
                  onAdvance={handleStuckAdvance}
                  onCallStaff={() => setStaffNotified(true)}
                  staffNotified={staffNotified} />;
      case "inspect":
        return <Card_Inspect rating={rating} onRate={setRating} onAdvance={() => advance("reseat")} />;
      case "reseat":
        return <Card_Reseat
                  checks={reseatChecks}
                  onToggle={(id) => setReseatChecks(cs => cs.map(c => c.id === id ? { ...c, done: !c.done } : c))}
                  onAdvance={() => advance("wrap-up")} />;
      case "wrap-up":
        return <Card_WrapUp totalTime="2h 14m" onRestart={restart} />;
      default: return null;
    }
  })();

  const idx = ph5Index(stepId);
  const phaseChipTone = stepId === "stuck" ? "error" : stepId === "wrap-up" ? "success" : "";

  // Show heat wisps near plate during hot/warm cooling
  const showWisps = stepId === "cooling-hot";

  // Steps where the background printer blurs (reseat returns to the printer)
  const focusSteps = ["lift-model", "stuck", "inspect"];
  const focusMode = focusSteps.includes(stepId);
  const plateModelSteps = ["lift-model", "stuck", "inspect"];

  // During reseat, keep door open until check 3 closes it
  const reseatDone = reseatChecks.filter(c => c.done).length;
  const effectiveDoorOpen = stepId === "reseat"
    ? (reseatDone < 3)          // door open until plate in + door closed
    : doorOpen;

  return (
    <div className="stage phase4" data-screen-label="Phase 4 · Completion & Post-Print">
      <div className="scene-bg"></div>
      <div className="scene-shelf"></div>
      <div className="scene-bench"></div>

      <div className={focusMode ? "scene-focus-blur" : ""}>
        <PrinterScene
          progress={100} state="done"
          statusPin={PH5_PINS[stepId]?.[0]}
          doorOpen={effectiveDoorOpen}
          plateReseating={stepId === "reseat"}
          reseatDone={reseatDone}
          modelRemoved={["lift-model","stuck","inspect","reseat","wrap-up"].includes(stepId)}
        />
      </div>

      {/* Plate + model hero (Steps 22–24) */}
      {plateModelSteps.includes(stepId) && (
        <PlateModelFocus
          stepId={stepId}
          liftChecks={liftChecks}
          spudgerActive={spudgerActive}
        />
      )}


      {/* Heat wisps overlay above the printer when plate is hot */}
      {showWisps && (
        <div style={{
          position: "absolute",
          left: "50%", top: "44%",
          transform: "translate(-50%, -50%)",
          width: 80, height: 80,
          pointerEvents: "none",
          zIndex: 6,
        }}>
          <svg className="heat-wisp" viewBox="0 0 80 80" width="80" height="80">
            <circle cx="30" cy="60" r="6" fill="rgba(255,159,10,0.45)"/>
            <circle cx="48" cy="60" r="5" fill="rgba(255,159,10,0.35)"/>
            <circle cx="40" cy="60" r="7" fill="rgba(255,159,10,0.30)"/>
          </svg>
        </div>
      )}

      {/* Floor anchor under printer */}
      <div className="floor-anchor">
        <span className="glow"></span>
        Bambu Lab X1 Carbon · The Bust
      </div>


      {/* Phase navigation */}
      <div className="phase-nav">
        <a href="Phase 1 Prototype.html">Phase 1</a>
        <a href="Phase 2 Prototype.html">Phase 2</a>
        <a href="Phase 3 Prototype.html">Phase 3</a>
        <a href="Phase 4 Prototype.html" className="active">Phase 4</a>
      </div>

      {/* Top brand + phase chip */}
      <div className="topbar">
        <div className="brand-pill">
          <img src="assets/panda-logo.svg" alt=""/>
          <div>
            <div className="nm">PANDA</div>
            <div className="sub">MakerLAB Assistant</div>
          </div>
        </div>
        <div className={`phase-chip ${phaseChipTone}`}>
          <span className="dot"></span>
          Phase 4 · Completion &amp; Post-Print
        </div>
      </div>

      {/* Step rail */}
      <StepRail5
        currentId={stepId}
        visited={visited}
        onSelect={(id) => setStepId(id)}
      />

      {/* Card cluster (right) */}
      <div className="card-cluster">
        {card}
        <AskAI5 stepId={stepId} isErrorContext={stepId === "stuck"} />
      </div>

      {/* Staff notified callout */}
      {staffNotified && stepId === "stuck" && (
        <StaffNotifiedCard
          secondsLeft={staffSeconds}
          onDismiss={() => { setStaffNotified(false); setStaffSeconds(120); }}
        />
      )}

      {/* Confetti layer (only on wrap-up) */}
      <Confetti active={stepId === "wrap-up"} />

      {/* Bottom controls */}
      <div className="controls">
        <span className="ctrl-label">Demo</span>
        <button className="ctrl-btn" disabled={idx === 0}
                onClick={() => setStepId(PH5_STEPS[Math.max(0, idx - 1)].id)}>
          <i data-lucide="chevron-left" width="14" height="14"></i> Prev
        </button>
        <button className="ctrl-btn primary" disabled={idx === PH5_STEPS.length - 1}
                onClick={() => setStepId(PH5_STEPS[Math.min(PH5_STEPS.length - 1, idx + 1)].id)}>
          Next <i data-lucide="chevron-right" width="14" height="14"></i>
        </button>
        <button className="ctrl-btn" onClick={restart}>
          <i data-lucide="rotate-ccw" width="14" height="14"></i> Restart
        </button>
      </div>
    </div>
  );
};

// Phase-5-aware AskAI (defined inline so it doesn't depend on phase4-app.jsx)
const AskAI5 = ({ stepId, isErrorContext }) => {
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState("");
  const [history, setHistory] = useState([]);
  const [listening, setListening] = useState(false);
  const inputRef = useRef(null);

  const suggestions = PH5_AI_SUGGESTIONS[stepId] || [];

  useEffect(() => {
    const t = setTimeout(() => window.lucide && window.lucide.createIcons(), 30);
    return () => clearTimeout(t);
  }, [open, history, listening, stepId]);

  useEffect(() => {
    setHistory([]); setInput(""); setOpen(false);
  }, [stepId]);

  const ask = async (q) => {
    if (!q || !q.trim()) return;
    const question = q.trim();
    setInput("");
    setHistory(h => [...h, { q: question, a: "", loading: true }]);
    let answer = PH5_AI_FALLBACKS[question] || "";
    try {
      if (window.claude && typeof window.claude.complete === "function") {
        const ctx = `You are PANDA, an AR assistant guiding a novice through the post-print steps of a Bambu X1 Carbon 3D print. The user is currently at step "${stepId}" of phase 4 (Completion & Post-Print — cool-down, removal, inspection). Reply in 1-2 short sentences, calm and specific, second-person. No emoji. No markdown.`;
        const res = await window.claude.complete({
          messages: [{ role: "user", content: `${ctx}\n\nUser asks: ${question}` }]
        });
        if (res && typeof res === "string" && res.trim()) answer = res.trim();
      }
    } catch (e) {}
    if (!answer) {
      answer = "Wait for the plate to reach 32°C before touching, then flex the plate gently to release the print.";
    }
    setHistory(h => h.map((it, i) => i === h.length - 1 ? { q: question, a: answer, loading: false } : it));
  };

  const onMic = () => {
    setListening(l => !l);
    if (!listening) {
      setTimeout(() => {
        setListening(false);
        if (suggestions[0]) ask(suggestions[0]);
      }, 1400);
    }
  };

  const onKey = (e) => {
    if (e.key === "Enter") { e.preventDefault(); ask(input); }
  };

  return (
    <div className={`ask-ai ${open ? "open" : ""} ${isErrorContext ? "error" : ""}`}>
      {open && (
        <div className="ask-ai-panel">
          <div className="ask-ai-header">
            <div className="ask-ai-brand">
              <span className="ask-ai-orb"><i data-lucide="sparkles" width="14" height="14"></i></span>
              <div>
                <div className="ask-ai-title">Ask PANDA</div>
                <div className="ask-ai-sub">AI assistant · always listening</div>
              </div>
            </div>
            <button className="ask-ai-close" onClick={() => setOpen(false)} aria-label="Collapse">
              <i data-lucide="chevron-down" width="14" height="14"></i>
            </button>
          </div>

          {history.length === 0 && (
            <div className="ask-ai-suggestions">
              <div className="ask-ai-suggestions-label">Try asking</div>
              {suggestions.map((s, i) => (
                <button key={i} className="ask-ai-chip" onClick={() => ask(s)}>
                  <i data-lucide="message-circle" width="11" height="11"></i>
                  {s}
                </button>
              ))}
            </div>
          )}

          {history.length > 0 && (
            <div className="ask-ai-thread">
              {history.map((it, i) => (
                <div key={i} className="ask-ai-turn">
                  <div className="ask-ai-q">
                    <span className="ask-ai-q-tag">You</span>
                    <span>{it.q}</span>
                  </div>
                  <div className="ask-ai-a">
                    <span className="ask-ai-a-tag"><i data-lucide="sparkles" width="10" height="10"></i> PANDA</span>
                    {it.loading
                      ? <span className="ask-ai-loading"><span></span><span></span><span></span></span>
                      : <span>{it.a}</span>}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      <div className="ask-ai-bar">
        <button className={`ask-ai-mic ${listening ? "listening" : ""}`} onClick={onMic} aria-label="Voice input">
          <i data-lucide="mic" width="16" height="16"></i>
          {listening && <span className="ask-ai-mic-pulse"></span>}
        </button>
        <input
          ref={inputRef}
          className="ask-ai-input"
          placeholder={listening ? "Listening…" : open ? "Ask PANDA anything…" : `Ask PANDA — ${suggestions[0] || "Type or speak"}`}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={onKey}
          onFocus={() => setOpen(true)}
        />
        <button className="ask-ai-send" onClick={() => ask(input)} disabled={!input.trim()} aria-label="Send">
          <i data-lucide="arrow-up" width="14" height="14"></i>
        </button>
        {!open && (
          <button className="ask-ai-expand" onClick={() => setOpen(true)} aria-label="Expand">
            <i data-lucide="chevron-up" width="14" height="14"></i>
          </button>
        )}
      </div>
    </div>
  );
};

// Mount
const rootEl = document.getElementById("root");
if (rootEl) {
  const root = ReactDOM.createRoot(rootEl);
  root.render(<App />);
}

// Expose cards + helpers for the paper-prototype page
Object.assign(window, {
  PH5_Card_Complete: Card_Complete,
  PH5_Card_Navigate: Card_Navigate,
  PH5_Card_Arrived: Card_Arrived,
  PH5_Card_CoolingHot: Card_CoolingHot,
  PH5_Card_CoolingWarm: Card_CoolingWarm,
  PH5_Card_CoolingSafe: Card_CoolingSafe,
  PH5_Card_RemovePrep: Card_RemovePrep,
  PH5_Card_LiftModel: Card_LiftModel,
  PH5_Card_Stuck: Card_Stuck,
  PH5_Card_Inspect: Card_Inspect,
  PH5_Card_Reseat: Card_Reseat,
  PH5_Card_WrapUp: Card_WrapUp,
  PH5_StaffNotifiedCard: StaffNotifiedCard,
  PH5_AI_SUGGESTIONS,
});
