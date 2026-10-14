// phase3-app.jsx — Phase 2 · On-Site Printer Interaction (Steps 1–7)
// Merged from former Phase 2 (walk step) + former Phase 3 (SD insert through start print)
const { useState, useEffect } = React;

// ============ Step definitions ============
const STEPS = [
  { id: "walk",       tag: "Step 1 · Walking",          name: "Walk to the printer" },
  { id: "sd-insert",  tag: "Step 2 · Insert SD",        name: "Insert SD card · correct orientation" },
  { id: "sd-confirm", tag: "Step 3 · Confirmed",        name: "SD card detected" },
  { id: "plate",      tag: "Step 4 · Build Plate",      name: "Clean the build plate" },
  { id: "fil-check",  tag: "Step 5 · Filament Check",   name: "Filament status — short on PLA" },
  { id: "fil-unload", tag: "Step 6 · Unload & Reload",  name: "Swap filament — guided" },
  { id: "start",      tag: "Step 7 · Start Print",      name: "All checks complete · start" },
];
const idxOf = (id) => STEPS.findIndex(s => s.id === id);

// ============ Step rail ============
const StepRail = ({ currentId, visited, onSelect, onDismiss }) => (
  <div className="step-rail">
    <div className="rail-title">Phase 2 · On-Site Printer</div>
    <button className="step-rail-dismiss" onClick={onDismiss} aria-label="Dismiss panel">
      <i data-lucide="x" width="12" height="12"></i>
    </button>
    {STEPS.map((s, i) => {
      const isActive = s.id === currentId;
      const isDone = visited.has(s.id) && !isActive;
      return (
        <div key={s.id} className={`rail-step ${isActive ? "active" : ""} ${isDone ? "done" : ""}`} onClick={() => onSelect(s.id)}>
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

// ============ Step 1 — Walk to Printer ============
const Card_Walk = ({ onArrived }) => (
  <GlassCard>
    <StepTag>Step 1 · Walking</StepTag>
    <CardTitle>Walk to your printer</CardTitle>
    <CardBody>Follow the floor arrows to <strong>Bay A</strong>. The target printer glows green.</CardBody>
    <div style={{marginTop:10}}>
      <Tag tone="green" icon="map-pin">18m · 25 steps</Tag>
    </div>
    <div className="btn-row" style={{marginTop:14}}>
      <GlassButton variant="primary" icon="check" onClick={onArrived} full>I've Arrived</GlassButton>
    </div>
  </GlassCard>
);

// ============ Step 2 — Insert SD with orientation guard ============
const Card_SDInsert = ({ orientation, onSetOrientation, inserted, onInsert, onAdvance }) => {
  const wrong = orientation === "wrong";
  return (
    <GlassCard tint={wrong ? "red" : ""}>
      <StepTag>Step 2 · Insert SD Card</StepTag>
      <CardTitle>Insert the SD card</CardTitle>
      <CardBody>
        <strong>Label side up, gold contacts first.</strong>
      </CardBody>

      <div className={`sd-diagram ${wrong ? "wrong" : "right"}`}>
        <div className="sd-card-vis">
          <span className="sd-corner"></span>
          <span className="sd-label-line"></span>
          <span className="sd-label-line short"></span>
          <span className="sd-pins"></span>
        </div>
        <div className="sd-arrow">
          <i data-lucide={wrong ? "arrow-up-from-line" : "arrow-down-to-line"} width="18" height="18"></i>
        </div>
        <div className={`sd-slot-vis ${wrong ? "rejected" : "ready"}`}>
          <span className="slot-mouth"></span>
          <span className="slot-label">Slot</span>
        </div>
      </div>

      <div className="orient-toggle">
        <span className="lbl">Try inserting:</span>
        <button className={`pill ${!wrong ? "on" : ""}`} onClick={() => onSetOrientation("right")}>
          <i data-lucide="check" width="11" height="11"></i> Label up
        </button>
        <button className={`pill ${wrong ? "on" : ""}`} onClick={() => onSetOrientation("wrong")}>
          <i data-lucide="x" width="11" height="11"></i> Upside down
        </button>
      </div>

      {wrong && (
        <AlertBox tone="error" icon="alert-triangle">
          <strong>Flip the card</strong> — label must face you.
        </AlertBox>
      )}

      <div className="btn-row">
        {!inserted ? (
          <GlassButton
            variant={wrong ? "danger" : "primary"}
            icon={wrong ? "alert-triangle" : "arrow-down"}
            disabled={wrong}
            onClick={onInsert}
            full
          >
            {wrong ? "Won't Fit — Flip First" : "Simulate Insert"}
          </GlassButton>
        ) : (
          <GlassButton variant="primary" icon="chevron-right" onClick={onAdvance} full>
            Continue
          </GlassButton>
        )}
      </div>
    </GlassCard>
  );
};

// ============ Step 3 — SD Detected ============
const Card_SDConfirm = ({ onAdvance }) => (
  <GlassCard tint="green">
    <StepTag>Step 3 · Confirmation</StepTag>
    <CardTitle>SD card detected</CardTitle>
    <CardBody><strong>cat_figure.gcode.3mf</strong> is ready to print.</CardBody>
    <div style={{display:"flex", gap:8, marginTop:10, flexWrap:"wrap"}}>
      <Tag tone="green" icon="check-circle-2">Visual ✓</Tag>
      <Tag tone="purple" icon="volume-2">Audio ✓</Tag>
      <Tag tone="blue" icon="vibrate">Haptic ✓</Tag>
    </div>
    <div className="btn-row" style={{marginTop:14}}>
      <GlassButton variant="primary" icon="chevron-right" onClick={onAdvance} full>Continue</GlassButton>
    </div>
  </GlassCard>
);

// ============ Step 4 — Build Plate ============
const Card_Plate = ({ wiped, animating, onWipe, onAdvance }) => (
  <GlassCard>
    <StepTag>Step 4 · Build Plate</StepTag>
    <CardTitle>Wipe the build plate</CardTitle>
    <CardBody>A clean plate ensures your print sticks.</CardBody>
    <ul className="checklist" style={{marginTop:10}}>
      <li className={wiped ? "done" : animating ? "active" : ""}>
        <Checkbox checked={wiped || animating} onChange={!animating ? onWipe : undefined}/>
        <span>Open the door, wipe with isopropyl, close it</span>
      </li>
    </ul>
    {animating && (
      <div className="loading-strip" style={{marginTop:8}}>
        <span className="spinner"></span>
        <span>Wiping plate…</span>
      </div>
    )}
    <div className="btn-row" style={{marginTop:12}}>
      <GlassButton variant="primary" icon="chevron-right" disabled={!wiped} onClick={onAdvance} full>
        {wiped ? "Continue" : animating ? "Wiping…" : "Wipe to Continue"}
      </GlassButton>
    </div>
  </GlassCard>
);

// ============ Step 5 — Filament Status ============
const Card_FilCheck = ({ onAdvance, onSkip }) => (
  <GlassCard tint="orange">
    <StepTag>Step 5 · Filament Check</StepTag>
    <CardTitle>Not enough filament</CardTitle>
    <CardBody>Spool has <strong>~20g</strong> — print needs <strong>32g</strong>. Swap now to avoid a failed print.</CardBody>

    <div className="fil-gauge">
      <div className="gauge-label">
        <span className="lbl">Spool remaining</span>
        <span className="val">20g</span>
      </div>
      <div className="gauge-bar">
        <div className="gauge-fill" style={{width: "20%"}}></div>
        <div className="gauge-need" style={{left: "32%"}}></div>
      </div>
      <div className="gauge-detail">
        <span>Print needs <strong>32g</strong></span>
        <span className="neg">Short by 12g</span>
      </div>
    </div>

    <div className="btn-row" style={{marginTop:14}}>
      <GlassButton variant="primary" icon="package" onClick={onAdvance} full>Swap Filament</GlassButton>
    </div>
    <div className="btn-row" style={{marginTop:6}}>
      <GlassButton variant="ghost" onClick={onSkip}>Skip (not recommended)</GlassButton>
    </div>
  </GlassCard>
);

// ============ Step 6 — Filament Unload (multi-substep) ============
const UNLOAD_STEPS = [
  { id: "tap-tab",   label: "Tap the Filament tab on the printer screen",   highlight: "tabs" },
  { id: "pull-back", label: "Confirm \"Pull back current filament\" prompt", highlight: "tabs" },
  { id: "unload",    label: "Tap Unload — wait for the motor to retract",   highlight: "tabs" },
  { id: "tft-pull",  label: "Pull filament out of the TFT tube (highlighted)", highlight: "spool-dock" },
  { id: "load-new",  label: "Mount new spool, feed into the tube, purge",   highlight: "spool-dock" },
  { id: "store-old", label: "Return old spool to the rack labeled PLA-W",   highlight: "spool-dock" },
];

const Card_FilUnload = ({ done, onToggle, subStepIdx, onAdvance }) => {
  const allDone = done.length === UNLOAD_STEPS.length;
  const completedCount = done.length;
  return (
    <GlassCard>
      <StepTag>Step 6 · Unload &amp; Reload</StepTag>
      <CardTitle>Swap to a fresh spool</CardTitle>
      <CardBody>Tap each step as you complete it.</CardBody>

      <ol className="step-list step-list-tight">
        {UNLOAD_STEPS.map((s, i) => {
          const isDone = done.includes(s.id);
          const isCurrent = !isDone && i === completedCount;
          return (
            <li
              key={s.id}
              className={`${isDone ? "done" : ""} ${isCurrent ? "active" : ""}`}
              onClick={() => onToggle(s.id, i)}
            >
              <span className="step-num">{isDone ? "✓" : String.fromCharCode(97 + i)}</span>
              <span dangerouslySetInnerHTML={{__html: s.label.replace(/Filament tab|Unload|TFT tube|PLA-W/g, m => `<strong>${m}</strong>`)}}></span>
            </li>
          );
        })}
      </ol>

      <div className="btn-row" style={{marginTop:12}}>
        <GlassButton variant="primary" icon="chevron-right" disabled={!allDone} onClick={onAdvance} full>
          {allDone ? "Continue" : `${completedCount} / ${UNLOAD_STEPS.length} done`}
        </GlassButton>
      </div>
    </GlassCard>
  );
};

// ============ Step 7 — Start Print ============
const Card_Start = ({ checks, onToggle, starting, onStart, started }) => {
  const allDone = checks.every(c => c.done);
  return (
    <GlassCard tint={started ? "green" : ""}>
      <StepTag>Step 7 · Start Print</StepTag>
      <CardTitle>{started ? "Print started" : "All checks complete"}</CardTitle>
      <CardBody>
        {started ? <>Print is running.</> : <>Confirm all systems before starting.</>}
      </CardBody>
      <ul className="checklist" style={{marginTop:10}}>
        {checks.map((c, i) => (
          <li key={c.id} className={c.done ? "done" : ""}>
            <Checkbox checked={c.done} onChange={() => !started && onToggle(c.id)}/>
            <span>{c.label}</span>
          </li>
        ))}
      </ul>
      {starting && (
        <div className="loading-strip">
          <span className="spinner"></span>
          <span>Heating up…</span>
        </div>
      )}
      <div className="btn-row" style={{marginTop:14}}>
        {!started ? (
          <GlassButton variant="primary" icon="play" disabled={!allDone || starting} onClick={onStart} full>
            {starting ? "Starting…" : allDone ? "Start Print" : `${checks.filter(c=>c.done).length}/${checks.length} checked`}
          </GlassButton>
        ) : (
          <GlassButton variant="primary" icon="arrow-right" full
            onClick={() => location.href = "Phase 3 Prototype.html"}>
            Continue to Phase 3
          </GlassButton>
        )}
      </div>
    </GlassCard>
  );
};

// ============ Spatial pins per step ============
const PRINTER_PIN = { x: 70, y: 20 };
const WALK_PIN = { x: 62, y: 80 };
const PINS = {
  "walk":       [{ ...WALK_PIN,    label: "Bay A · X1C",  tone: "blue",   icon: "navigation-2" }],
  "sd-insert":  [{ ...PRINTER_PIN, label: "Insert here",  tone: "blue",   icon: "arrow-down" }],
  "sd-confirm": [{ ...PRINTER_PIN, label: "Detected",     tone: "green",  icon: "check" }],
  "plate":      [{ ...PRINTER_PIN, label: "Wipe plate",   tone: "green",  icon: "spray-can" }],
  "fil-check":  [{ ...PRINTER_PIN, label: "Low: 20g",     tone: "orange", icon: "alert-triangle" }],
  "fil-unload": [{ ...PRINTER_PIN, label: "Swap spool",   tone: "orange", icon: "package" }],
  "start":      [{ ...PRINTER_PIN, label: "Tap Start",    tone: "green",  icon: "play" }],
};

// ============ Main App ============
const App = () => {
  const [stepId, setStepId] = useState("walk");
  const [visited, setVisited] = useState(new Set(["walk"]));
  const [railVisible, setRailVisible] = useState(true);

  const [orientation, setOrientation] = useState("right");
  const [sdInserted, setSdInserted] = useState(false);
  const [showConfirmToast, setShowConfirmToast] = useState(false);
  const [plateWiped, setPlateWiped] = useState(false);
  const [plateAnimating, setPlateAnimating] = useState(false);
  const [corridorApproaching, setCorridorApproaching] = useState(false);
  const [unloadDone, setUnloadDone] = useState([]);
  const [unloadCurrent, setUnloadCurrent] = useState(0);
  const [readyChecks, setReadyChecks] = useState([
    { id: "file",     label: "File loaded: cat_figure.gcode.3mf", done: false },
    { id: "filament", label: "Filament loaded and feeding",       done: false },
    { id: "plate",    label: "Build plate clean and seated",      done: false },
  ]);
  const [starting, setStarting] = useState(false);
  const [started, setStarted] = useState(false);

  useEffect(() => {
    setVisited(prev => { const next = new Set(prev); next.add(stepId); return next; });
  }, [stepId]);

  useEffect(() => {
    if (stepId === "sd-confirm") {
      setShowConfirmToast(true);
      const t = setTimeout(() => setShowConfirmToast(false), 2400);
      return () => clearTimeout(t);
    } else {
      setShowConfirmToast(false);
    }
  }, [stepId]);

  useEffect(() => {
    if (starting && !started) {
      const t = setTimeout(() => { setStarting(false); setStarted(true); }, 1800);
      return () => clearTimeout(t);
    }
  }, [starting, started]);

  useEffect(() => {
    if (stepId === "start") {
      setReadyChecks(cs => cs.map(c => ({
        ...c,
        done: c.id === "file"     ? true
            : c.id === "plate"    ? plateWiped
            : c.id === "filament" ? unloadDone.length === UNLOAD_STEPS.length
            : false
      })));
    }
  }, [stepId, plateWiped, unloadDone]);

  useEffect(() => {
    const t = setTimeout(() => window.lucide && window.lucide.createIcons(), 60);
    return () => clearTimeout(t);
  });

  const restart = () => {
    setStepId("walk");
    setVisited(new Set(["walk"]));
    setOrientation("right");
    setSdInserted(false);
    setPlateWiped(false);
    setPlateAnimating(false);
    setCorridorApproaching(false);
    setUnloadDone([]); setUnloadCurrent(0);
    setReadyChecks(cs => cs.map(c => ({...c, done: false})));
    setStarting(false); setStarted(false);
    setRailVisible(true);
  };

  const showCorridor = stepId === "walk";
  const showPrinter  = stepId !== "walk";

  const printerHighlight =
    stepId === "sd-insert"  ? "sd" :
    stepId === "sd-confirm" ? "screen-confirm" :
    stepId === "plate"      ? "plate" :
    stepId === "fil-check"  ? "spool-dock" :
    stepId === "fil-unload" ? (unloadCurrent < 3 ? "tabs" : "spool-dock") :
    stepId === "start"      ? (started ? "none" : "tabs") :
    "none";

  const sdShownInScene =
    sdInserted || (stepId !== "sd-insert" && stepId !== "walk");

  const oldFilamentRemoved =
    stepId === "fil-unload" && unloadDone.includes("tft-pull") && !unloadDone.includes("load-new");

  const newFilamentLoaded =
    started ||
    stepId === "start" ||
    (stepId === "fil-unload" && unloadDone.includes("load-new"));

  const card = (() => {
    switch (stepId) {
      case "walk":
        return <Card_Walk onArrived={() => setStepId("sd-insert")}/>;
      case "sd-insert":
        return <Card_SDInsert
                  orientation={orientation}
                  onSetOrientation={setOrientation}
                  inserted={sdInserted}
                  onInsert={() => orientation === "right" && setSdInserted(true)}
                  onAdvance={() => setStepId("sd-confirm")}/>;
      case "sd-confirm":
        return <Card_SDConfirm onAdvance={() => setStepId("plate")}/>;
      case "plate":
        return <Card_Plate
                  wiped={plateWiped}
                  animating={plateAnimating}
                  onWipe={() => {
                    if (!plateWiped && !plateAnimating) {
                      setPlateAnimating(true);
                      setTimeout(() => {
                        setPlateWiped(true);
                        setPlateAnimating(false);
                      }, 3200);
                    }
                  }}
                  onAdvance={() => setStepId("fil-check")}/>;
      case "fil-check":
        return <Card_FilCheck
                  onAdvance={() => setStepId("fil-unload")}
                  onSkip={() => setStepId("start")}/>;
      case "fil-unload":
        return <Card_FilUnload
                  done={unloadDone}
                  subStepIdx={unloadCurrent}
                  onToggle={(id, i) => {
                    setUnloadDone(prev => {
                      if (prev.includes(id)) {
                        const ix = prev.indexOf(id);
                        return prev.slice(0, ix);
                      }
                      if (i === prev.length) {
                        setUnloadCurrent(i + 1);
                        return [...prev, id];
                      }
                      return prev;
                    });
                  }}
                  onAdvance={() => setStepId("start")}/>;
      case "start":
        return <Card_Start
                  checks={readyChecks}
                  onToggle={(id) => setReadyChecks(cs => cs.map(c => c.id === id ? {...c, done: !c.done} : c))}
                  starting={starting}
                  started={started}
                  onStart={() => setStarting(true)}/>;
      default: return null;
    }
  })();

  const idx = idxOf(stepId);
  const phaseChipTone = started ? "success" :
    (stepId === "fil-check" || (stepId === "sd-insert" && orientation === "wrong")) ? "warn" : "";

  return (
    <div className="stage" data-screen-label="Phase 2 · On-Site Printer Interaction">
      {showCorridor && (
        <CorridorScene
          approaching={corridorApproaching}
          onApproach={() => {
            if (corridorApproaching) return;
            setCorridorApproaching(true);
            setTimeout(() => {
              setCorridorApproaching(false);
              setStepId("sd-insert");
            }, 3200);
          }}
        />
      )}
      {showPrinter && (
        <PrinterScene
          highlight={printerHighlight}
          sdInserted={sdShownInScene}
          plateClean={plateWiped}
          plateAnimating={plateAnimating}
          showBackCue={stepId === "fil-check"}
          unloadSubStep={stepId === "fil-unload" ? (UNLOAD_STEPS[unloadCurrent]?.id ?? null) : null}
          oldFilamentRemoved={oldFilamentRemoved}
          newFilamentLoaded={newFilamentLoaded}
          printing={started}
          statusPin={PINS[stepId]?.[0]}
        />
      )}

      {stepId === "sd-insert" && orientation === "wrong" && (
        <div className="sd-reject-fx">
          <div className="sd-reject-ring"></div>
          <div className="sd-reject-label">
            <i data-lucide="x" width="14" height="14"></i>
            <span>Won't fit — flip it</span>
          </div>
        </div>
      )}

      {showConfirmToast && (
        <div className="confirm-toast">
          <span className="check">✓</span>
          <span>SD Card Detected · cat_figure.3mf</span>
          <span className="audio-pulse"><i data-lucide="volume-2" width="12" height="12"></i></span>
        </div>
      )}


      {showCorridor && (PINS[stepId] || []).map((p, i) => <SpatialPin key={i} {...p}/>)}

      <div className="phase-nav">
        <a href="Phase 1 Prototype.html">Phase 1</a>
        <a href="Phase 2 Prototype.html" className="active">Phase 2</a>
        <a href="Phase 3 Prototype.html">Phase 3</a>
        <a href="Phase 4 Prototype.html">Phase 4</a>
      </div>

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
          Phase 2 · On-Site Printer
        </div>
      </div>

      {railVisible
        ? <StepRail currentId={stepId} visited={visited} onSelect={setStepId} onDismiss={() => setRailVisible(false)} />
        : <button className="step-rail-restore" onClick={() => setRailVisible(true)} aria-label="Show steps">
            <i data-lucide="panel-left" width="20" height="20"></i>
          </button>}

      <div className="card-cluster">{card}</div>

      <div className="user-pip">
        <div className="user-pip-avatar">T</div>
        <div>
          <div className="nm">Tiffany</div>
          <div className="sub">At the printer</div>
        </div>
      </div>

      <div className="controls">
        <span className="ctrl-label">Demo</span>
        <button className="ctrl-btn" disabled={idx === 0} onClick={() => setStepId(STEPS[Math.max(0, idx - 1)].id)}>
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

const rootEl = document.getElementById("root");
if (rootEl) {
  const root = ReactDOM.createRoot(rootEl);
  root.render(<App/>);
}
