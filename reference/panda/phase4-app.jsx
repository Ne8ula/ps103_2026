// phase4-app.jsx — Phase 3 Printing & Monitoring · interactive step machine
const { useState, useEffect, useRef, useMemo } = React;

// ============ Step definitions ============
const STEPS = [
  { id: "starting",     tag: "Step 8a · Print Starting",       name: "Heating bed & nozzle" },
  { id: "first-watch",  tag: "Step 8b · Watch First Layer",    name: "Watch the first layer" },
  { id: "first-passed", tag: "Step 9 · First Layer Passed",    name: "First layer adhesion confirmed" },
  { id: "monitoring",   tag: "Step 10 · Live Monitoring",      name: "Print in progress" },
  { id: "anomaly",      tag: "Step 11 · Anomaly Detected",     name: "Print paused — adhesion failure" },
  { id: "fix",          tag: "Step 11b · Guided Fix",          name: "Guided recovery steps" },
  { id: "resumed",      tag: "Step 12 · Resumed",              name: "Print resumed" },
  { id: "finishing",    tag: "Step 13 · Finishing",            name: "Final layers" },
  { id: "complete",     tag: "Step 14 · Print Complete",       name: "Print complete — handoff" },
];

const stepIndex = (id) => STEPS.findIndex(s => s.id === id);

// ============ Step rail ============
const StepRail = ({ currentId, visited, onSelect, onDismiss }) => (
  <div className="step-rail">
    <div className="rail-title">Phase 3 · Printing</div>
    <button className="step-rail-dismiss" onClick={onDismiss} aria-label="Dismiss panel">
      <i data-lucide="x" width="12" height="12"></i>
    </button>
    {STEPS.map((s, i) => {
      const isActive = s.id === currentId;
      const isDone = visited.has(s.id) && !isActive;
      const isError = (s.id === "anomaly" || s.id === "fix") && isActive;
      return (
        <div
          key={s.id}
          className={`rail-step ${isActive ? "active" : ""} ${isDone ? "done" : ""} ${isError ? "error" : ""}`}
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

// ============ Live camera-feed mini overlay ============
const LiveFeed = ({ progress, state, label = "Print Camera · Live", showError = false }) => {
  const tone = state === "error" || state === "paused" ? "" : state === "done" ? "success" : "warn";
  return (
    <div className="live-feed">
      <div className="live-feed-inner">
        <div className="live-feed-plate"></div>
        {/* White cat — full size, clipped from top to reveal bottom-up as progress grows */}
        <div style={{
          position: "absolute",
          left: "18%", right: "18%",
          bottom: "18%",
          height: "50%",
          clipPath: `inset(${Math.max(0, 100 - progress * 1.04)}% 0 0 0)`,
          transition: "clip-path 600ms linear",
          filter: "drop-shadow(0 0 5px rgba(255,255,255,0.30))",
        }}>
          <svg viewBox="0 0 80 68" width="100%" height="100%"
               preserveAspectRatio="xMidYMax meet"
               style={{ display: "block", position: "absolute", bottom: 0 }}>
            <polygon points="7,30 20,5 32,30" fill="rgba(255,255,255,0.95)"/>
            <polygon points="48,30 60,5 73,30" fill="rgba(255,255,255,0.95)"/>
            <rect x="7" y="28" width="66" height="36" rx="5" fill="rgba(255,255,255,0.95)"/>
            <line x1="7" y1="34" x2="73" y2="34" stroke="rgba(0,0,0,0.10)" strokeWidth="0.8"/>
            <line x1="7" y1="40" x2="73" y2="40" stroke="rgba(0,0,0,0.10)" strokeWidth="0.8"/>
            <line x1="7" y1="46" x2="73" y2="46" stroke="rgba(0,0,0,0.10)" strokeWidth="0.8"/>
            <line x1="7" y1="52" x2="73" y2="52" stroke="rgba(0,0,0,0.10)" strokeWidth="0.8"/>
            <line x1="7" y1="58" x2="73" y2="58" stroke="rgba(0,0,0,0.10)" strokeWidth="0.8"/>
          </svg>
        </div>
        <div className="live-feed-nozzle"></div>
      </div>
      <div className="live-feed-overlay"></div>
      <div className={`live-feed-label ${tone}`}>
        <span className="live-dot"></span>{label}
      </div>
      <div className="live-feed-time">{progress.toFixed(0)}%</div>
      {showError && (
        <div className="live-feed-bbox" style={{ left: "30%", top: "62%", width: "40%", height: "16%" }}>
          <div className="live-feed-bbox-label">Adhesion failure</div>
        </div>
      )}
    </div>
  );
};

// ============ Card variants per step ============
const Card_Starting = ({ progress, bedTemp, nozzleTemp, onAdvance }) => (
  <GlassCard>
    <StepTag>Step 8a · Print Starting</StepTag>
    <CardTitle>Heating bed & nozzle</CardTitle>
    <div className="stats-row">
      <StatBox value={`${Math.round(bedTemp)}°C`} label="Bed" sub="Target 60°C" color={bedTemp >= 58 ? "#1a7035" : "#8a5c00"} />
      <StatBox value={`${Math.round(nozzleTemp)}°C`} label="Nozzle" sub="Target 220°C" color={nozzleTemp >= 215 ? "#1a7035" : "#8a5c00"} />
    </div>
    <div className="progress-wrap"><div className="progress-fill warn" style={{ width: `${progress}%` }}></div></div>
    <div className="progress-meta">
      <span>Preheating</span><span>{progress.toFixed(0)}%</span>
    </div>
    <div className="btn-row">
      <GlassButton variant="primary" icon="chevron-right" onClick={onAdvance} disabled={progress < 100}>
        {progress < 100 ? "Heating…" : "Begin First Layer"}
      </GlassButton>
    </div>
  </GlassCard>
);

const Card_FirstWatch = ({ silent, onToggleSilent, onAdvance }) => (
  <GlassCard>
    <StepTag>Step 8b · Watch First Layer</StepTag>
    <CardTitle>Watch the first layer</CardTitle>
    <AlertBox tone="warn">
      <strong>Most failures happen here.</strong><br/>Stay nearby and observe carefully.
    </AlertBox>
    <div className="btn-row">
      <GlassButton variant={silent ? "success" : "ghost"} icon={silent ? "check" : undefined} onClick={() => onToggleSilent(true)}>
        {silent ? "Silent Mode On" : "Switch to Silent"}
      </GlassButton>
      <GlassButton variant="primary" icon="eye" onClick={onAdvance}>First Layer Looks Good</GlassButton>
    </div>
  </GlassCard>
);

const Card_FirstPassed = ({ silent, onToggleSilent, onAdvance }) => (
  <GlassCard tint="green">
    <StepTag>Step 9 · First Layer Passed</StepTag>
    <CardTitle>First layer looks good</CardTitle>
    <div style={{ marginTop: 4 }}>
      <Tag tone="green" icon="check-circle-2">First Layer Adhesion Confirmed</Tag>
    </div>
    <div className="btn-row">
      <GlassButton variant={!silent ? "success" : "primary"} icon={!silent ? "check" : "fast-forward"} onClick={() => onToggleSilent(false)}>
        {!silent ? "Switched to Standard" : "Switch to Standard"}
      </GlassButton>
      <GlassButton variant="primary" icon="chevron-right" onClick={onAdvance}>Continue Monitoring</GlassButton>
    </div>
  </GlassCard>
);

const Card_Monitoring = ({ progress, layer, totalLayers, timeLeft, onTriggerAnomaly, onComplete }) => (
  <GlassCard>
    <StepTag>Step 10 · Live Monitoring</StepTag>
    <CardTitle>Print in progress</CardTitle>
    <div className="progress-wrap"><div className="progress-fill" style={{ width: `${progress}%` }}></div></div>
    <div className="progress-meta">
      <span>{progress.toFixed(0)}% complete</span>
      <span>Est. {timeLeft} left</span>
    </div>
    <LiveFeed progress={progress} state="printing" />
    <div className="btn-row">
      <GlassButton variant="ghost" icon="bell" onClick={onTriggerAnomaly}>Simulate Anomaly</GlassButton>
      <GlassButton variant="ghost" icon="fast-forward" onClick={onComplete}>Skip to Done</GlassButton>
    </div>
  </GlassCard>
);

const Card_Anomaly = ({ onFix, onCallStaff, staffNotified }) => (
  <GlassCard tint="red">
    <StepTag>Step 11 · Anomaly Detected</StepTag>
    <CardTitle>Print anomaly — paused</CardTitle>
    <AlertBox tone="error">
      Filament not sticking to plate.<br/>Possible cause: temperature too low or plate not clean.
    </AlertBox>
    <LiveFeed progress={28} state="paused" label="Anomaly · Layer 24" showError />
    <div className="btn-row">
      <GlassButton variant="primary" icon="wand-2" onClick={onFix}>Fix With Guided Steps</GlassButton>
      <GlassButton variant="danger" icon="phone" onClick={onCallStaff} disabled={staffNotified}>
        {staffNotified ? "Staff On the Way" : "Call Staff"}
      </GlassButton>
    </div>
  </GlassCard>
);

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

const Card_Fix = ({ checks, onToggle, onResume }) => {
  const allDone = checks.every(c => c.done);
  return (
    <GlassCard tint="orange">
      <StepTag>Step 11b · Guided Fix</StepTag>
      <CardTitle>Recovery — three quick steps</CardTitle>
      <LiveFeed progress={28} state="paused" label="Paused · Layer 24" />
      <ul className="checklist">
        {checks.map((c, i) => (
          <li key={c.id} className={c.done ? "done" : ""}>
            <Checkbox checked={c.done} onChange={() => onToggle(c.id)} />
            <span><strong>{i + 1}.</strong> {c.label}</span>
          </li>
        ))}
      </ul>
      <div className="btn-row">
        <GlassButton variant="primary" icon="play" disabled={!allDone} onClick={onResume} full>
          {allDone ? "Resume Print" : `${checks.filter(c=>c.done).length}/${checks.length} complete`}
        </GlassButton>
      </div>
    </GlassCard>
  );
};

const Card_Resumed = ({ progress, onAdvance }) => (
  <GlassCard tint="blue">
    <StepTag>Step 12 · Resumed</StepTag>
    <CardTitle>Print resumed successfully</CardTitle>
    <div style={{ marginTop: 4 }}>
      <Tag tone="green" icon="check-circle-2">Adhesion restored</Tag>
    </div>
    <AlertBox tone="success">
      Layer 24 reprinted cleanly. I’ll alert you if anything changes.
    </AlertBox>
    <div className="progress-wrap"><div className="progress-fill" style={{ width: `${progress}%` }}></div></div>
    <div className="progress-meta">
      <span>{progress.toFixed(0)}% complete</span><span>~38m left</span>
    </div>
    <div className="btn-row">
      <GlassButton variant="primary" icon="chevron-right" full onClick={onAdvance}>Keep Monitoring</GlassButton>
    </div>
  </GlassCard>
);

const Card_Finishing = ({ progress, onComplete }) => (
  <GlassCard>
    <StepTag>Step 13 · Finishing</StepTag>
    <CardTitle>Final layers printing</CardTitle>
    <div className="progress-wrap"><div className="progress-fill success" style={{ width: `${progress}%` }}></div></div>
    <div className="progress-meta">
      <span>{progress.toFixed(0)}% complete</span><span>~2m left</span>
    </div>
    <AlertBox tone="info" icon="info">
      Stay nearby — auto-cooldown begins after the last layer.
    </AlertBox>
    <LiveFeed progress={progress} state="printing" label="Final Pass · Live" />
    <div className="btn-row">
      <GlassButton variant="success" icon="check" full onClick={onComplete}>Print Complete</GlassButton>
    </div>
  </GlassCard>
);

const Card_Complete = () => (
  <GlassCard tint="green">
    <StepTag>Step 14 · Print Complete</StepTag>
    <CardTitle>Print complete</CardTitle>
    <div className="stats-row">
      <StatBox value="2h 14m" label="Total time" />
      <StatBox value="312" label="Layers" />
    </div>
    <div style={{ marginTop: 12, display: "flex", flexDirection: "column", gap: 8 }}>
      <Tag tone="green" icon="check-circle-2">Bambu Lab X1 Carbon · The Bust</Tag>
    </div>
  </GlassCard>
);

// ============ Spatial pin sets per step (pinned to printer regions) ============
// All pins anchored to top-right of the printer for consistency.
const PRINTER_PIN = { x: 70, y: 20 };
const PINS = {
  "starting":     [{ ...PRINTER_PIN, label: "Heating", tone: "orange", icon: "flame" }],
  "first-watch":  [{ ...PRINTER_PIN, label: "Watch nozzle", tone: "purple", icon: "eye" }],
  "first-passed": [{ ...PRINTER_PIN, label: "Layer 1 OK", tone: "green", icon: "check" }],
  "monitoring":   [{ ...PRINTER_PIN, label: "Live", tone: "blue", icon: "activity" }],
  "anomaly":      [{ ...PRINTER_PIN, label: "Failure", tone: "red", icon: "alert-triangle" }],
  "fix":          [{ ...PRINTER_PIN, label: "Clean here", tone: "orange", icon: "sparkles" }],
  "resumed":      [{ ...PRINTER_PIN, label: "Resumed", tone: "blue", icon: "play" }],
  "finishing":    [{ ...PRINTER_PIN, label: "Top layers", tone: "blue", icon: "layers" }],
  "complete":     [{ ...PRINTER_PIN, label: "Ready", tone: "green", icon: "check-circle-2" }],
};

// ============ Ask AI — persistent purple assistant pinned bottom ============
const AI_SUGGESTIONS = {
  "starting":      ["How long until heating finishes?", "Why preheat the bed first?", "What temperature should the nozzle be?"],
  "first-watch":   ["How do I know if the first layer is good?", "What does a bad first layer look like?", "Should I stay near the printer?"],
  "first-passed":  ["What can go wrong from here?", "How often should I check?", "Can I leave the lab?"],
  "monitoring":    ["How much time is left?", "What's the printer doing now?", "How do I pause safely?"],
  "anomaly":       ["What went wrong?", "Is my print recoverable?", "Should I call staff?"],
  "fix":           ["Show me how to clean the plate.", "How do I auto-level?", "What temp should the bed be?"],
  "resumed":       ["Will the seam be visible?", "Is it safe to leave now?", "How do I prevent this next time?"],
  "finishing":     ["When can I remove the print?", "How long until cool-down?", "Do I need to shut anything off?"],
  "complete":      ["Take me to my model.", "How do I remove the print?", "Where's the cool-down guide?"],
};

const AI_FALLBACKS = {
  "How long until heating finishes?": "About 90 seconds. Bed is ramping to 65°C and the nozzle to 220°C — both should be ready at the same time.",
  "How do I know if the first layer is good?": "Look for even, glossy lines with no gaps between them. The filament should stick flat to the plate, not curl up at the corners.",
  "How much time is left?": "Roughly 1 hour 22 minutes. You're 28% through, currently on layer 47 of 312.",
  "What went wrong?": "The first layer isn't bonding. Most common causes: the plate wasn't clean, or the bed temp dropped below 60°C. The printer paused itself to protect the print.",
  "Show me how to clean the plate.": "Wipe the entire build surface with isopropyl alcohol on a lint-free cloth. Let it air-dry for 10 seconds. The plate is cool enough to touch.",
  "Take me to my model.": "Your print is on Bay 2, Printer X1-A. I'll keep the spatial pin active until you reach it.",
};

const AskAI = ({ stepId, isErrorContext }) => {
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState("");
  const [history, setHistory] = useState([]); // {q, a, loading}
  const [listening, setListening] = useState(false);
  const inputRef = useRef(null);

  const suggestions = AI_SUGGESTIONS[stepId] || [];

  // Hydrate Lucide icons whenever AskAI's own state changes (panel opens, history updates, listening toggles)
  useEffect(() => {
    const t = setTimeout(() => window.lucide && window.lucide.createIcons(), 30);
    return () => clearTimeout(t);
  }, [open, history, listening, stepId]);

  // Reset history when step changes (each step gets a fresh assistant context)
  useEffect(() => {
    setHistory([]);
    setInput("");
    setOpen(false);
  }, [stepId]);

  const ask = async (q) => {
    if (!q || !q.trim()) return;
    const question = q.trim();
    setInput("");
    setHistory(h => [...h, { q: question, a: "", loading: true }]);
    let answer = AI_FALLBACKS[question] || "";
    try {
      if (window.claude && typeof window.claude.complete === "function") {
        const ctx = `You are PANDA, an AR assistant guiding a novice through a Bambu X1 Carbon 3D print. The user is currently at step "${stepId}" of phase 3 (Printing & Monitoring). Reply in 1-2 short sentences, calm and specific, second-person. No emoji. No markdown.`;
        const res = await window.claude.complete({
          messages: [
            { role: "user", content: `${ctx}\n\nUser asks: ${question}` }
          ]
        });
        if (res && typeof res === "string" && res.trim()) answer = res.trim();
      }
    } catch (e) {
      // fall through to fallback
    }
    if (!answer) {
      answer = "I'll help with that — keep an eye on the printer and follow the on-screen prompts. If anything looks off, tap Call Staff.";
    }
    setHistory(h => h.map((it, i) => i === h.length - 1 ? { q: question, a: answer, loading: false } : it));
  };

  const onMic = () => {
    setListening(l => !l);
    // Simulate voice capture for demo
    if (!listening) {
      setTimeout(() => {
        setListening(false);
        if (suggestions[0]) ask(suggestions[0]);
      }, 1400);
    }
  };

  const onKey = (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      ask(input);
    }
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
          <i data-lucide={listening ? "mic" : "mic"} width="16" height="16"></i>
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

// ============ Main App ============
const App = () => {
  const [stepId, setStepId] = useState("starting");
  const [visited, setVisited] = useState(new Set(["starting"]));
  const [railVisible, setRailVisible] = useState(true);

  // Live state
  const [bedTemp, setBedTemp] = useState(24);
  const [nozzleTemp, setNozzleTemp] = useState(24);
  const [heatProgress, setHeatProgress] = useState(0);
  const [printProgress, setPrintProgress] = useState(0);
  const [silent, setSilent] = useState(true);
  const [staffNotified, setStaffNotified] = useState(false);
  const [staffSeconds, setStaffSeconds] = useState(120);
  const [fixChecks, setFixChecks] = useState([
    { id: "clean", label: "Wipe build plate with isopropyl", done: false },
    { id: "level", label: "Auto-level confirmed", done: false },
    { id: "temp",  label: "Bed temp set to 65°C", done: false },
  ]);
  const [fixAnim, setFixAnim] = useState(null);
  const fixAnimTimer = useRef(null);

  // Mark visited
  useEffect(() => {
    setVisited(prev => {
      const next = new Set(prev); next.add(stepId); return next;
    });
  }, [stepId]);

  // Heating animation while in 'starting'
  useEffect(() => {
    if (stepId !== "starting") return;
    const t = setInterval(() => {
      setBedTemp(b => Math.min(60, b + 1.6));
      setNozzleTemp(n => Math.min(220, n + 6.5));
      setHeatProgress(p => Math.min(100, p + 2.4));
    }, 100);
    return () => clearInterval(t);
  }, [stepId]);

  // Print progress animation while in monitoring/finishing/resumed
  useEffect(() => {
    if (stepId === "monitoring") {
      const t = setInterval(() => {
        setPrintProgress(p => {
          if (p >= 28) return 28; // pause at the anomaly trigger zone
          return Math.min(28, p + 0.6);
        });
      }, 200);
      return () => clearInterval(t);
    }
    if (stepId === "first-passed") {
      const t = setTimeout(() => setPrintProgress(p => Math.max(p, 6)), 200);
      return () => clearTimeout(t);
    }
    if (stepId === "resumed") {
      const t = setInterval(() => {
        setPrintProgress(p => Math.min(85, p + 1.2));
      }, 180);
      return () => clearInterval(t);
    }
    if (stepId === "finishing") {
      const t = setInterval(() => {
        setPrintProgress(p => Math.min(99, p + 0.8));
      }, 160);
      return () => clearInterval(t);
    }
    if (stepId === "complete") {
      setPrintProgress(100);
    }
  }, [stepId]);

  // Re-render lucide icons after each step / state change
  useEffect(() => {
    const t = setTimeout(() => window.lucide && window.lucide.createIcons(), 60);
    return () => clearTimeout(t);
  }, [stepId, fixChecks, silent, printProgress, heatProgress, bedTemp, nozzleTemp, railVisible]);

  const advance = (id) => setStepId(id);

  const restart = () => {
    setStepId("starting");
    setVisited(new Set(["starting"]));
    setBedTemp(24); setNozzleTemp(24); setHeatProgress(0); setPrintProgress(0);
    setSilent(true);
    setStaffNotified(false); setStaffSeconds(120);
    setFixChecks(c => c.map(x => ({ ...x, done: false })));
    setRailVisible(true);
  };

  // Staff ETA countdown
  useEffect(() => {
    if (!staffNotified) return;
    const t = setInterval(() => setStaffSeconds(s => Math.max(0, s - 1)), 1000);
    return () => clearInterval(t);
  }, [staffNotified]);

  // Map step → printer state for SVG
  const printerState = useMemo(() => {
    if (stepId === "starting") return "heating";
    if (stepId === "anomaly" || stepId === "fix") return "paused";
    if (stepId === "complete") return "done";
    return "printing";
  }, [stepId]);

  // Fix-step checklist toggle — triggers a timed printer animation per check
  const handleFixToggle = (id) => {
    const check = fixChecks.find(c => c.id === id);
    setFixChecks(cs => cs.map(c => c.id === id ? { ...c, done: !c.done } : c));
    if (fixAnimTimer.current) clearTimeout(fixAnimTimer.current);
    if (check && !check.done) {
      setFixAnim(id);
      const dur = id === "clean" ? 3500 : id === "level" ? 4200 : 3200;
      fixAnimTimer.current = setTimeout(() => setFixAnim(null), dur);
    } else {
      setFixAnim(null);
    }
  };

  // Nozzle sweep speed: fast while silent (Step 9 default), slow after switching to Standard
  const printerSpeed = useMemo(() => {
    if (stepId === "first-passed") return silent ? "slow" : "fast";
    if (stepId === "monitoring" || stepId === "resumed" || stepId === "finishing") return "fast";
    return "normal";
  }, [stepId, silent]);

  // Printer animation props driven by active fix checklist item
  const printerPlateAnimating = fixAnim === "clean";
  const printerHighlight =
    fixAnim === "level" ? "auto-level" :
    fixAnim === "temp"  ? "bed-temp"   :
    stepId === "fix"    ? "plate"      : "none";

  const layer = Math.max(1, Math.round(printProgress * 3.12));
  const minutesLeft = Math.max(2, Math.round(134 - printProgress * 1.32));
  const timeLeft = `${Math.floor(minutesLeft/60)}h ${(minutesLeft%60).toString().padStart(2,"0")}m`;

  // Printer screen content per step — drives the touchscreen UI on the printer body
  const screenInfo = (() => {
    switch (stepId) {
      case "starting":
        return { status: "Heating…",    detail: `Bed ${Math.round(bedTemp)}°C · Nozzle ${Math.round(nozzleTemp)}°C`, color: "orange" };
      case "first-watch":
        return { status: "Printing…",   detail: "Layer 1 — Watch closely",             color: "green"  };
      case "first-passed":
        return { status: "Layer 1 OK",  detail: "Mode: " + (silent ? "Silent" : "Standard"),  color: "green"  };
      case "monitoring":
        return { status: "Printing…",   detail: `${printProgress.toFixed(0)}%  ·  Layer ${layer} / 312`, color: "green"  };
      case "anomaly":
        return { status: "Paused",      detail: "Anomaly — Layer 24",                  color: "red"    };
      case "fix":
        return { status: "Paused",      detail: "Recovery mode",                       color: "red"    };
      case "resumed":
        return { status: "Printing…",   detail: `${printProgress.toFixed(0)}%  ·  Resumed`,  color: "green"  };
      case "finishing":
        return { status: "Finishing…",  detail: `${printProgress.toFixed(0)}%  ·  Final layers`, color: "green"  };
      case "complete":
        return { status: "Complete",    detail: "Print done · Cooling down",           color: "blue"   };
      default:
        return { status: "Printing…",   detail: "cat_figure.gcode.3mf",                color: "green"  };
    }
  })();

  const card = (() => {
    switch (stepId) {
      case "starting":
        return <Card_Starting progress={heatProgress} bedTemp={bedTemp} nozzleTemp={nozzleTemp} onAdvance={() => advance("first-watch")} />;
      case "first-watch":
        return <Card_FirstWatch silent={silent} onToggleSilent={setSilent} onAdvance={() => advance("first-passed")} />;
      case "first-passed":
        return <Card_FirstPassed silent={silent} onToggleSilent={setSilent} onAdvance={() => advance("monitoring")} />;
      case "monitoring":
        return <Card_Monitoring progress={printProgress} layer={layer} totalLayers={312} timeLeft={timeLeft}
                  onTriggerAnomaly={() => advance("anomaly")} onComplete={() => advance("complete")} />;
      case "anomaly":
        return <Card_Anomaly onFix={() => advance("fix")} onCallStaff={() => setStaffNotified(true)} staffNotified={staffNotified} />;
      case "fix":
        return <Card_Fix
                  checks={fixChecks}
                  onToggle={handleFixToggle}
                  onResume={() => advance("resumed")} />;
      case "resumed":
        return <Card_Resumed progress={printProgress} onAdvance={() => advance("finishing")} />;
      case "finishing":
        return <Card_Finishing progress={printProgress} onComplete={() => advance("complete")} />;
      case "complete":
        return <Card_Complete />;
      default: return null;
    }
  })();

  const idx = stepIndex(stepId);
  const phaseChipTone = (stepId === "anomaly" || stepId === "fix") ? "error" : (stepId === "complete" ? "success" : "");

  return (
    <div className="stage" data-screen-label="Phase 3 · Printing & Monitoring">
      <div className="scene-bg"></div>
      <div className="scene-shelf"></div>
      <div className="scene-bench"></div>

      <PrinterScene
        progress={printProgress}
        state={printerState}
        speed={printerSpeed}
        sdInserted={true}
        plateAnimating={printerPlateAnimating}
        highlight={printerHighlight}
        screenStatus={screenInfo.status}
        screenDetail={screenInfo.detail}
        screenColor={screenInfo.color}
        statusPin={PINS[stepId]?.[0]}
      />

      {/* Floor anchor under printer */}
      <div className="floor-anchor">
        <span className="glow"></span>
        Bambu Lab X1 Carbon · The Bust
      </div>


      {/* Phase navigation */}
      <div className="phase-nav">
        <a href="Phase 1 Prototype.html">Phase 1</a>
        <a href="Phase 2 Prototype.html">Phase 2</a>
        <a href="Phase 3 Prototype.html" className="active">Phase 3</a>
        <a href="Phase 4 Prototype.html">Phase 4</a>
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
          Phase 3 · Printing &amp; Monitoring
        </div>
      </div>

      {/* Step rail */}
      {railVisible
        ? <StepRail currentId={stepId} visited={visited} onSelect={(id) => setStepId(id)} onDismiss={() => setRailVisible(false)} />
        : <button className="step-rail-restore" onClick={() => setRailVisible(true)} aria-label="Show steps">
            <i data-lucide="panel-left" width="20" height="20"></i>
          </button>}

      {/* Card cluster (right) — shows the active step's card */}
      <div className="card-cluster">
        {card}
        <AskAI stepId={stepId} isErrorContext={stepId === "anomaly" || stepId === "fix"} />
      </div>

      {/* Staff notified callout (left side, aligned with Step 11 anomaly card) */}
      {staffNotified && stepId === "anomaly" && (
        <StaffNotifiedCard
          secondsLeft={staffSeconds}
          onDismiss={() => { setStaffNotified(false); setStaffSeconds(120); }}
        />
      )}

      {/* Bottom controls */}
      <div className="controls">
        <span className="ctrl-label">Demo</span>
        <button className="ctrl-btn" disabled={idx === 0}
                onClick={() => setStepId(STEPS[Math.max(0, idx - 1)].id)}>
          <i data-lucide="chevron-left" width="14" height="14"></i> Prev
        </button>
        <button className="ctrl-btn primary" disabled={idx === STEPS.length - 1}
                onClick={() => setStepId(STEPS[Math.min(STEPS.length - 1, idx + 1)].id)}>
          Next <i data-lucide="chevron-right" width="14" height="14"></i>
        </button>
        <button className="ctrl-btn" onClick={restart}>
          <i data-lucide="rotate-ccw" width="14" height="14"></i> Restart
        </button>
      </div>
    </div>
  );
};

// Expose components for reuse (e.g. paper-prototype tile sheet)
Object.assign(window, {
  Card_Starting, Card_FirstWatch, Card_FirstPassed, Card_Monitoring,
  Card_Anomaly, Card_Fix, Card_Resumed, Card_Finishing, Card_Complete,
  StaffNotifiedCard, AskAI, AI_SUGGESTIONS, LiveFeed,
  PhaseApp: App,
});

// Only auto-mount the full prototype if the host page provides #root
const rootEl = document.getElementById("root");
if (rootEl) {
  const root = ReactDOM.createRoot(rootEl);
  root.render(<App />);
}
