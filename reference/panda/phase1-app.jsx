// phase1-app.jsx — Phase 1 · Pre-Print Preparation (anchored next to laptop)
const { useState, useEffect, useMemo } = React;

const PH1_STEPS = [
  { id: "welcome",    tag: "Step 1 · Welcome",          name: "Welcome to MakerLAB" },
  { id: "open-app",   tag: "Step 2 · Open Bambu Studio",name: "Open Bambu Studio" },
  { id: "pair",       tag: "Step 3 · Pair with Laptop", name: "Confirm pairing code" },
  { id: "new-proj",   tag: "Step 4 · New Project",      name: "Create a new project" },
  { id: "import",     tag: "Step 5 · Import File",      name: "Import your 3D model" },
  { id: "printer",    tag: "Step 6 · Select Printer",   name: "Pick the printer" },
  { id: "filament",   tag: "Step 7 · Filament",         name: "Filament recommendation" },
  { id: "support",    tag: "Step 8 · Support",          name: "Enable support" },
  { id: "slice",      tag: "Step 9 · Slice Plate",      name: "Slice the plate" },
  { id: "export",     tag: "Step 10 · Export File",     name: "Export sliced file" },
  { id: "sd-locate",  tag: "Step 11 · SD Card",         name: "Locate SD card + reader" },
  { id: "sd-save",    tag: "Step 12 · Save & Eject",    name: "Save to SD card" },
  { id: "complete",   tag: "Step 13 · Phase Complete",  name: "Ready for the printer" },
];
const idxOf = (id) => PH1_STEPS.findIndex(s => s.id === id);

// ============ Step Rail ============
const StepRail = ({ currentId, visited, onSelect, onDismiss }) => (
  <div className="step-rail">
    <div className="rail-title">Phase 1 · Pre-Print</div>
    <button className="step-rail-dismiss" onClick={onDismiss} aria-label="Dismiss panel">
      <i data-lucide="x" width="12" height="12"></i>
    </button>
    {PH1_STEPS.map((s, i) => {
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

// ============ Bambu Studio mock window — drawn on laptop screen ============
const BambuMock = ({ stage, slicedView = false }) => {
  // stage: "off" | "desktop" | "done" | "open" | "pair" | "paired" | "new" | "import" | "printer" | "filament" | "support" | "slice" | "export"
  if (stage === "off") return null;

  // ── Dark macOS desktop (Steps 1 & 2 — app not yet open) ──
  if (stage === "desktop" || stage === "desktop-open") {
    const showOpenRing = stage === "desktop-open";
    return (
      <div className="bambu-window">
        <div className="bd-screen bd-desktop">
          <div className="bd-menubar">
            <span className="bd-apple">⌘</span>
            <span>Finder</span><span>File</span><span>Edit</span><span>Go</span>
            <div style={{marginLeft:"auto",display:"flex",gap:10}}>
              <span>Wi-Fi</span><span>Mon 10:42 AM</span>
            </div>
          </div>
          <div className="bd-wallpaper-body">
            <div className="bd-ambient-ring bd-r1"></div>
            <div className="bd-ambient-ring bd-r2"></div>
          </div>
          <div className="bd-dock-row">
            <div className="bd-dock">
              <div className={`bd-dock-app bd-bambu ${showOpenRing ? "bd-bambu-ring" : ""}`}>
                <span style={{fontSize:9,fontWeight:800,letterSpacing:"-0.5px"}}>BS</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // ── Phase-complete screen (Step 13) ──
  if (stage === "done") {
    return (
      <div className="bambu-window">
        <div className="bd-screen bd-done">
          <div className="bd-menubar">
            <span className="bd-apple">⌘</span>
            <span>Finder</span>
            <div style={{marginLeft:"auto",display:"flex",gap:10}}>
              <span>Mon 10:58 AM</span>
            </div>
          </div>
          <div className="bd-done-body">
            <div className="bd-done-ring">✓</div>
            <div className="bd-done-title">File exported</div>
            <div className="bd-done-sub">cat_figure.gcode.3mf · ready for SD card</div>
          </div>
          <div className="bd-dock-row">
            <div className="bd-dock">
              <div className="bd-dock-app bd-bambu bd-bambu-done">
                <span style={{fontSize:9,fontWeight:800,letterSpacing:"-0.5px"}}>BS</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  const showImportRing = stage === "import";
  const showPrinterRing = stage === "printer";
  const showFilamentRing = stage === "filament";
  const showSupportRing = stage === "support";
  const showSliceRing = stage === "slice";
  const showExportRing = stage === "export";
  const showModel = ["import","printer","filament","support","slice","export"].includes(stage);
  const showSliced = slicedView;

  return (
    <div className="bambu-window">
      <div className="bambu-titlebar">
        <span className="dots"><span className="dot r"></span><span className="dot y"></span><span className="dot g"></span></span>
        <span className="ttl">Bambu Studio — {stage === "open" ? "Welcome" : "cat_figure.3mf"}</span>
      </div>
      <div className="bambu-toolbar" style={{ position: "relative" }}>
        <span className={`bambu-tool ${stage === "new" ? "highlight" : ""}`}>New Project</span>
        <span className={`bambu-tool ${stage === "import" ? "highlight" : ""}`} style={{ position: "relative" }}>
          File › Import
          {showImportRing && <div className="ar-ring green" style={{ position: "absolute", inset: "-4px -6px", width: "auto", height: "auto" }}></div>}
        </span>
        <span className="bambu-tool">Edit</span>
        <span className="bambu-tool">View</span>
        <span className="bambu-tool active">Prepare</span>
        <span className="bambu-tool">Preview</span>
      </div>
      <div className="bambu-canvas">
        {stage === "open" && (
          <div style={{textAlign:"center", color:"#3a3a40"}}>
            <div style={{fontSize:18, fontWeight:700, color:"#1a1a20"}}>Bambu Studio</div>
            <div style={{fontSize:10, marginTop:4}}>v1.9 · Loading workspace…</div>
          </div>
        )}
        {(stage === "pair" || stage === "paired") && (
          <div style={{textAlign:"center", color:"#3a3a40", padding:"14px"}}>
            <div style={{fontSize:11, fontWeight:600, color:"#0a84ff", letterSpacing:"0.08em", textTransform:"uppercase"}}>PANDA Headset Pairing</div>
            <div style={{fontSize:13, fontWeight:600, color:"#1a1a20", marginTop:8}}>
              {stage === "paired" ? "Headset connected" : "Confirm this code on your headset"}
            </div>
            <div className="bambu-pair-digits">
              {PAIRING_CODE.map((d,i)=>(<span key={i} className={`bambu-pair-d ${stage === "paired" ? "ok" : ""}`}>{d}</span>))}
            </div>
            <div style={{fontSize:9, marginTop:8, color: stage === "paired" ? "#1a7a3c" : "#6a6a72"}}>
              {stage === "paired" ? "✓ Tiffany's headset · ready" : "Waiting for headset confirmation…"}
            </div>
          </div>
        )}
        {stage === "new" && (
          <div style={{textAlign:"center", color:"#3a3a40", padding:"20px"}}>
            <div style={{fontSize:14, fontWeight:600, color:"#1a1a20"}}>Start a new project</div>
            <div style={{fontSize:9, marginTop:6, color:"#6a6a72"}}>An empty plate is ready. Import your model to begin.</div>
          </div>
        )}
        {showModel && (
          <div className="bambu-plate">
            {showSliced ? (
              <svg style={{position:"absolute", left:"50%", top:"38%", transform:"translate(-50%,-50%)"}} width="60" height="50" viewBox="0 0 60 50">
                {Array.from({length:14}).map((_,i)=>(
                  <ellipse key={i} cx="30" cy={48-i*3} rx={20-i*0.4} ry={3-i*0.05} fill="none" stroke="#0a84ff" strokeWidth="0.5" opacity={0.5+i*0.03}/>
                ))}
              </svg>
            ) : (
              <div className="bambu-model" role="img" aria-label="3D model preview">🐱</div>
            )}
          </div>
        )}
        {showModel && (
          <div className="bambu-rightpanel">
            <div className="label">Printer</div>
            <div className={`field ${showPrinterRing ? "highlight" : ""}`}>Bambu Lab X1 Carbon ▾</div>
            <div className="label">Filament</div>
            <div className={`field ${showFilamentRing ? "highlight" : ""}`}>PLA Basic — White ▾</div>
            <div className="label">Quality</div>
            <div className="field">0.20mm Standard ▾</div>
            <div className="label">Support</div>
            <div className={`field ${showSupportRing ? "highlight" : ""}`} style={showSupportRing ? {color:"#003a7a", fontWeight:700} : null}>
              {stage === "support" || stage === "slice" || stage === "export" ? "✓ Auto support" : "Off"}
            </div>
            <button className={`bambu-slice-btn ${showSliceRing ? "highlight" : ""}`} style={{ position: "relative" }}>
              {stage === "export" ? "Export .gcode.3mf" : "Slice Plate"}
              {showExportRing && <div className="ar-ring green" style={{ position: "absolute", inset: "-4px -6px" }}></div>}
            </button>
          </div>
        )}

        {/* AR rings */}
      </div>
    </div>
  );
};

// ============ Cards ============
const Card_Welcome = ({ onStart, onSkip }) => (
  <GlassCard>
    <StepTag>Step 1 · Welcome</StepTag>
    <CardTitle>Welcome to MakerLAB</CardTitle>
    <CardBody>First time printing? I'll guide you through the full workflow — file prep, printer setup, and the first layer.</CardBody>
    <div style={{ marginTop: 10 }}>
      <Tag tone="purple" icon="hand">Pinch <strong>Start</strong> to begin</Tag>
    </div>
    <div className="btn-row">
      <GlassButton variant="primary" icon="sparkles" onClick={onStart} full>Start Guided Setup</GlassButton>
    </div>
    <div className="btn-row" style={{ marginTop: 6 }}>
      <GlassButton variant="ghost" onClick={onSkip}>Skip to Printing Set Up</GlassButton>
    </div>
  </GlassCard>
);

const Card_OpenApp = ({ opened, onOpen, onAdvance }) => (
  <GlassCard>
    <StepTag>Step 2 · Open Bambu Studio</StepTag>
    <CardTitle>Open Bambu Studio</CardTitle>
    <CardBody>Find <strong>Bambu Studio</strong> in your dock or applications. I've highlighted it on your laptop screen.</CardBody>
    <ul className="step-list" style={{marginTop:10}}>
      <li className={opened ? "done" : "active"}>
        <span className="step-num">1</span><span>Open <strong>Bambu Studio</strong></span>
      </li>
    </ul>
    <div className="btn-row">
      {!opened
        ? <GlassButton variant="primary" icon="play" onClick={onOpen} full>Simulate Opening App</GlassButton>
        : <GlassButton variant="primary" icon="chevron-right" onClick={onAdvance} full>Continue</GlassButton>}
    </div>
  </GlassCard>
);

const PAIRING_CODE = ["7", "3", "1", "4"];

const Card_Pair = ({ confirmed, onConfirm, onAdvance }) => (
  <GlassCard>
    <StepTag>Step 3 · Pair with Laptop</StepTag>
    <CardTitle>Confirm pairing<br/>with your laptop</CardTitle>
    <CardBody>I detected Bambu Studio on a nearby laptop. Confirm the four-digit code matches what you see on the laptop screen.</CardBody>
    <div className="pair-digits" aria-label="Pairing code">
      {PAIRING_CODE.map((d, i) => (
        <div key={i} className="pair-digit">{d}</div>
      ))}
    </div>
    {!confirmed ? (
      <div className="pair-status waiting">
        <span className="pair-spinner" aria-hidden="true"></span>
        <span>Waiting for confirmation on laptop…</span>
      </div>
    ) : (
      <AlertBox tone="success" icon="check-circle-2">
        Paired with <strong>Tiffany's MacBook</strong>. PANDA can now ring UI on the screen.
      </AlertBox>
    )}
    <div className="btn-row">
      {!confirmed
        ? <GlassButton variant="primary" icon="link" onClick={onConfirm} full>Codes Match · Confirm Pair</GlassButton>
        : <GlassButton variant="primary" icon="chevron-right" onClick={onAdvance} full>Continue</GlassButton>}
    </div>
  </GlassCard>
);

const Card_NewProject = ({ created, onCreate, onAdvance }) => (
  <GlassCard>
    <StepTag>Step 4 · New Project</StepTag>
    <CardTitle>Create a new project</CardTitle>
    <CardBody>Click <strong>New Project</strong> in the toolbar — I'll ring it on your screen.</CardBody>
    <ul className="step-list" style={{marginTop:10}}>
      <li className="done"><span className="step-num">1</span><span>Open Bambu Studio</span></li>
      <li className="done"><span className="step-num">2</span><span>Pair headset with laptop</span></li>
      <li className={created ? "done" : "active"}><span className="step-num">3</span><span>Click <strong>New Project</strong></span></li>
    </ul>
    <div className="btn-row">
      {!created
        ? <GlassButton variant="primary" icon="plus" onClick={onCreate} full>Project Created</GlassButton>
        : <GlassButton variant="primary" icon="chevron-right" onClick={onAdvance} full>Continue</GlassButton>}
    </div>
  </GlassCard>
);

const Card_Import = ({ imported, onImport, onAdvance }) => (
  <GlassCard>
    <StepTag>Step 5 · Import File</StepTag>
    <CardTitle>Import your 3D model</CardTitle>
    <CardBody>Use <strong>File › Import</strong> and choose your <strong>.stl</strong> or <strong>.3mf</strong> file.</CardBody>
    {imported && (
      <AlertBox tone="success" icon="check-circle-2">
        File format verified. <strong>cat_figure.3mf</strong> loaded.
      </AlertBox>
    )}
    {!imported && (
      <AlertBox tone="info" icon="info">
        I check the file type to catch a common novice mistake. Only <strong>.stl</strong> and <strong>.3mf</strong> are supported here.
      </AlertBox>
    )}
    <div className="btn-row">
      {!imported
        ? <GlassButton variant="primary" icon="upload" onClick={onImport} full>Import cat_figure.3mf</GlassButton>
        : <GlassButton variant="primary" icon="chevron-right" onClick={onAdvance} full>Continue</GlassButton>}
    </div>
  </GlassCard>
);

const PRINTERS = [
  { id: "x1", name: "Bambu Lab X1 Carbon", loc: "The Bust", available: true },
  { id: "h2", name: "Bambu Lab H2S",      loc: "Station B", available: true },
  { id: "p1", name: "Bambu Lab P1S",      loc: "Bay 4",     available: false },
];

const Card_Printer = ({ selected, onSelect, onAdvance }) => (
  <GlassCard>
    <StepTag>Step 6 · Select Printer</StepTag>
    <CardTitle>Pick an available printer</CardTitle>
    <CardBody>I scanned the lab. Available printers are highlighted in 3D space — pick one to set the slicer profile.</CardBody>
    <div className="printer-list">
      {PRINTERS.map(p => (
        <div key={p.id} className={`printer-option ${selected === p.id ? "sel" : ""}`}
             onClick={() => p.available && onSelect(p.id)}
             style={!p.available ? {opacity:0.4, cursor:"not-allowed"} : null}>
          <span className={`p-dot ${p.available ? "on" : ""}`}></span>
          <div style={{flex:1}}>
            <div className="p-name">{p.name}</div>
            <div className="p-sub">{p.loc} · {p.available ? "Available" : "In Use"}</div>
          </div>
          {selected === p.id && <i data-lucide="check" width="16" height="16" style={{color:"#1a7a3c"}}></i>}
        </div>
      ))}
    </div>
    <div className="btn-row">
      <GlassButton variant="primary" icon="chevron-right" disabled={!selected} onClick={onAdvance} full>
        {selected ? "Continue" : "Select a Printer"}
      </GlassButton>
    </div>
  </GlassCard>
);

const FILAMENTS = [
  { id: "pla-w", name: "PLA Basic", color: "White", swatch: "#ffffff" },
  { id: "pla-b", name: "PLA Basic", color: "Black", swatch: "#1a1a20" },
  { id: "pla-g", name: "PLA Basic", color: "Grey",  swatch: "#9a9aa0" },
  { id: "petg",  name: "PETG",      color: "Clear", swatch: "rgba(180,210,220,0.6)" },
  { id: "abs",   name: "ABS",       color: "White", swatch: "#f5f5f5" },
];

const Card_Filament = ({ selected, onSelect, onApply, applied, onAdvance }) => (
  <GlassCard>
    <StepTag>Step 7 · Filament</StepTag>
    <CardTitle>Recommended filament</CardTitle>
    <CardBody>Based on your model and the X1 Carbon, I recommend <strong>PLA Basic — White</strong>. It's in stock and forgiving for first prints.</CardBody>
    <div className="recommend-card">
      <div className="recommend-spool"></div>
      <div className="recommend-info">
        <div className="lbl">Recommended</div>
        <div className="nm">PLA Basic — White</div>
        <div className="reason">Best for your model + Bambu X1 Carbon. Skips a step that confuses most beginners.</div>
      </div>
    </div>
    <div className="fil-list">
      {FILAMENTS.map(f => (
        <div key={f.id} className={`fil-item ${selected === f.id ? (f.id==="pla-w" ? "recommended" : "sel") : ""}`}
             onClick={() => onSelect(f.id)}>
          <span className="fil-swatch" style={{background:f.swatch}}></span>
          <span className="fil-name"><strong>{f.name}</strong> — {f.color}</span>
          {f.id === "pla-w" && <span className="fil-badge">Recommended</span>}
          {f.id !== "pla-w" && <span className="fil-badge">In Stock</span>}
        </div>
      ))}
    </div>
    <div className="btn-row">
      {!applied
        ? <GlassButton variant="primary" icon="check" disabled={!selected} onClick={onApply} full>Apply Filament</GlassButton>
        : <GlassButton variant="primary" icon="chevron-right" onClick={onAdvance} full>Continue</GlassButton>}
    </div>
  </GlassCard>
);

const Card_Support = ({ enabled, onToggle, onAdvance }) => (
  <GlassCard>
    <StepTag>Step 8 · Support</StepTag>
    <CardTitle>Enable support material?</CardTitle>
    <CardBody>Your model has overhangs steeper than 45°. Auto-support helps them print cleanly. You can remove the support after.</CardBody>
    <div className="btn-row">
      <GlassButton variant={enabled ? "success" : "ghost"} icon={enabled ? "check" : "plus"} onClick={() => onToggle(true)} full>
        {enabled ? "Auto Support Enabled" : "Enable Auto Support"}
      </GlassButton>
    </div>
    <div className="btn-row" style={{marginTop:6}}>
      <GlassButton variant="ghost" onClick={() => onToggle(false)}>Skip Support</GlassButton>
      <GlassButton variant="primary" icon="chevron-right" onClick={onAdvance}>Continue</GlassButton>
    </div>
  </GlassCard>
);

const Card_Slice = ({ slicing, sliced, onSlice, onAdvance }) => (
  <GlassCard>
    <StepTag>Step 9 · Slice Plate</StepTag>
    <CardTitle>Slice the plate</CardTitle>
    <CardBody>Click <strong>Slice Plate</strong>. I've ringed the button on your screen.</CardBody>
    {slicing && <AlertBox tone="info" icon="loader-2">Slicing… 312 layers · ~32g filament</AlertBox>}
    {sliced && (
      <div className="sliced-summary">
        <div className="row"><span>Layers</span><strong>312</strong></div>
        <div className="row"><span>Estimated time</span><strong>2h 14m</strong></div>
        <div className="row"><span>Filament needed</span><strong>32g</strong></div>
        <div className="row file"><span>Output</span><strong>cat_figure.gcode.3mf</strong></div>
      </div>
    )}
    <div className="btn-row">
      {!sliced
        ? <GlassButton variant="primary" icon="layers" disabled={slicing} onClick={onSlice} full>
            {slicing ? "Slicing…" : "Slice Plate"}
          </GlassButton>
        : <GlassButton variant="primary" icon="chevron-right" onClick={onAdvance} full>Continue</GlassButton>}
    </div>
  </GlassCard>
);

const Card_Export = ({ exported, onExport, onAdvance }) => (
  <GlassCard>
    <StepTag>Step 10 · Export File</StepTag>
    <CardTitle>Export sliced file</CardTitle>
    <CardBody>Choose <strong>Export plate sliced file</strong>. The button is highlighted with an attention ring on your screen.</CardBody>
    {exported && (
      <AlertBox tone="success" icon="check-circle-2">
        Exported <strong>cat_figure.gcode.3mf</strong> · ready to copy to SD card.
      </AlertBox>
    )}
    <div className="btn-row">
      {!exported
        ? <GlassButton variant="primary" icon="download" onClick={onExport} full>Export .gcode.3mf</GlassButton>
        : <GlassButton variant="primary" icon="chevron-right" onClick={onAdvance} full>Continue</GlassButton>}
    </div>
  </GlassCard>
);

const Card_SDLocate = ({ onAdvance }) => (
  <GlassCard>
    <StepTag>Step 11 · SD Card</StepTag>
    <CardTitle>Get the SD card + reader</CardTitle>
    <CardBody>I've pinned the SD card station in your view. Walk over and grab a card and reader.</CardBody>
    <AlertBox tone="info" icon="map-pin">
      SD card station highlighted in your AR view — <strong>Shelf B, left side</strong>.
    </AlertBox>
    <div style={{marginTop:8}}>
      <Tag tone="green" icon="check-circle-2">Pinned in 3D space</Tag>
    </div>
    <div className="btn-row">
      <GlassButton variant="primary" icon="chevron-right" onClick={onAdvance} full>I Have It</GlassButton>
    </div>
  </GlassCard>
);

const Card_SDSave = ({ checks, onToggle, onAdvance }) => {
  const allDone = checks.every(c => c.done);
  return (
    <GlassCard>
      <StepTag>Step 12 · Save & Eject</StepTag>
      <CardTitle>Save to SD card</CardTitle>
      <CardBody>Plug the reader into your laptop. Drag the file across, then eject before pulling it out.</CardBody>
      <ul className="checklist">
        {checks.map((c, i) => (
          <li key={c.id} className={c.done ? "done" : ""}>
            <Checkbox checked={c.done} onChange={() => onToggle(c.id)} />
            <span><strong>{i + 1}.</strong> {c.label}</span>
          </li>
        ))}
      </ul>
      <AlertBox tone="warn" icon="alert-triangle">
        Always eject before removing the reader — pulling it out live can corrupt the file.
      </AlertBox>
      <div className="btn-row">
        <GlassButton variant="primary" icon="chevron-right" disabled={!allDone} onClick={onAdvance} full>
          {allDone ? "Phase 1 Complete" : `${checks.filter(c=>c.done).length}/${checks.length} complete`}
        </GlassButton>
      </div>
    </GlassCard>
  );
};

const Card_Complete = () => (
  <GlassCard tint="green">
    <StepTag>Step 13 · Phase Complete</StepTag>
    <CardTitle>Phase 1 complete</CardTitle>
    <CardBody>Your file is ready. I'll guide you to your printer next.</CardBody>
    <ul className="checklist" style={{marginTop:6}}>
      <li className="done"><Checkbox checked={true}/><span>File prepared</span></li>
      <li className="done"><Checkbox checked={true}/><span>File saved to SD</span></li>
      <li className="done"><Checkbox checked={true}/><span>Eject before removing</span></li>
    </ul>
    <div style={{marginTop:14, display:"flex", gap:8}}>
      <GlassButton variant="primary" icon="arrow-right" full onClick={() => location.href = "Phase 2 Prototype.html"}>Go to Phase 2 — Walk to Printer</GlassButton>
    </div>
  </GlassCard>
);

// ============ Laptop screen status bar (top-right of display) ============
const LaptopStatusPins = ({ pins }) => {
  if (!pins || pins.length === 0) return null;
  return (
    <div className="laptop-status-bar">
      {pins.map((p, i) => (
        <React.Fragment key={i}>
          <div className={`pin-target ${p.tone || "blue"}`}>
            {p.icon && <i data-lucide={p.icon} width="14" height="14"></i>}
          </div>
          {p.label && <div className={`pin-label ${p.tone || "blue"}`}>{p.label}</div>}
        </React.Fragment>
      ))}
    </div>
  );
};

// ============ Spatial pins per step ============
// All pins anchored to top-right of the laptop for consistency.
const LAPTOP_PIN = { tone: "purple", icon: "sparkles" };
const PINS = {
  "welcome":    [{ label: "Hi, Tiffany",     tone: "green", icon: "sparkles" }],
  "open-app":   [{ label: "Bambu Studio",    tone: "green", icon: "app-window" }],
  "pair":       [{ label: "Pair laptop",     tone: "green", icon: "link" }],
  "new-proj":   [{ label: "New Project",     tone: "green", icon: "plus" }],
  "import":     [{ label: "File › Import",   tone: "green", icon: "upload" }],
  "printer":    [{ label: "Printer profile", tone: "green", icon: "printer" }],
  "filament":   [{ label: "Filament",        tone: "green", icon: "circle" }],
  "support":    [{ label: "Auto support",    tone: "green", icon: "triangle" }],
  "slice":      [{ label: "Slice Plate",     tone: "green", icon: "layers" }],
  "export":     [{ label: "Export here",     tone: "green", icon: "download" }],
  "sd-locate":  [{ label: "SD station",      tone: "green", icon: "sd-card" }],
  "sd-save":    [{ label: "Eject safely",    tone: "green", icon: "alert-triangle" }],
  "complete":   [{ label: "Ready",           tone: "green", icon: "check" }],
};

// ============ Bambu mock stage per step ============
const BAMBU_STAGE = {
  "welcome":   "desktop",
  "open-app":  "desktop-open",
  "pair":      "pair",
  "new-proj":  "open",
  "import":    "import",
  "printer":   "printer",
  "filament":  "filament",
  "support":   "support",
  "slice":     "slice",
  "export":    "export",
  "sd-locate": "export",
  "sd-save":   "export",
  "complete":  "done",
};

// ============ Main App ============
const App = () => {
  const [stepId, setStepId] = useState("welcome");
  const [visited, setVisited] = useState(new Set(["welcome"]));
  const [railVisible, setRailVisible] = useState(true);

  // Per-step state
  const [appOpened, setAppOpened] = useState(false);
  const [paired, setPaired] = useState(false);
  const [projectCreated, setProjectCreated] = useState(false);
  const [imported, setImported] = useState(false);
  const [printer, setPrinter] = useState(null);
  const [filament, setFilament] = useState(null);
  const [filamentApplied, setFilamentApplied] = useState(false);
  const [support, setSupport] = useState(false);
  const [slicing, setSlicing] = useState(false);
  const [sliced, setSliced] = useState(false);
  const [exported, setExported] = useState(false);
  const [sdChecks, setSdChecks] = useState([
    { id: "save",  label: "Save .gcode.3mf to SD card", done: false },
    { id: "eject", label: "Eject SD card safely",       done: false },
  ]);

  useEffect(() => {
    setVisited(prev => { const next = new Set(prev); next.add(stepId); return next; });
  }, [stepId]);

  // Slice fake progress
  useEffect(() => {
    if (slicing && !sliced) {
      const t = setTimeout(() => { setSlicing(false); setSliced(true); }, 1400);
      return () => clearTimeout(t);
    }
  }, [slicing, sliced]);

  useEffect(() => {
    const t = setTimeout(() => window.lucide && window.lucide.createIcons(), 60);
    return () => clearTimeout(t);
  });

  const advance = (id) => setStepId(id);

  const restart = () => {
    setStepId("welcome");
    setVisited(new Set(["welcome"]));
    setAppOpened(false); setPaired(false); setProjectCreated(false); setImported(false);
    setPrinter(null); setFilament(null); setFilamentApplied(false);
    setSupport(false); setSlicing(false); setSliced(false); setExported(false);
    setSdChecks(c => c.map(x => ({...x, done:false})));
    setRailVisible(true);
  };

  const card = (() => {
    switch (stepId) {
      case "welcome":   return <Card_Welcome onStart={() => advance("open-app")} onSkip={() => advance("complete")}/>;
      case "open-app":  return <Card_OpenApp opened={appOpened} onOpen={() => setAppOpened(true)} onAdvance={() => advance("pair")}/>;
      case "pair":      return <Card_Pair confirmed={paired} onConfirm={() => setPaired(true)} onAdvance={() => advance("new-proj")}/>;
      case "new-proj":  return <Card_NewProject created={projectCreated} onCreate={() => setProjectCreated(true)} onAdvance={() => advance("import")}/>;
      case "import":    return <Card_Import imported={imported} onImport={() => setImported(true)} onAdvance={() => advance("printer")}/>;
      case "printer":   return <Card_Printer selected={printer} onSelect={setPrinter} onAdvance={() => advance("filament")}/>;
      case "filament":  return <Card_Filament selected={filament} onSelect={setFilament} applied={filamentApplied} onApply={() => setFilamentApplied(true)} onAdvance={() => advance("support")}/>;
      case "support":   return <Card_Support enabled={support} onToggle={setSupport} onAdvance={() => advance("slice")}/>;
      case "slice":     return <Card_Slice slicing={slicing} sliced={sliced} onSlice={() => setSlicing(true)} onAdvance={() => advance("export")}/>;
      case "export":    return <Card_Export exported={exported} onExport={() => setExported(true)} onAdvance={() => advance("sd-locate")}/>;
      case "sd-locate": return <Card_SDLocate onAdvance={() => advance("sd-save")}/>;
      case "sd-save":   return <Card_SDSave checks={sdChecks} onToggle={(id) => setSdChecks(cs => cs.map(c => c.id === id ? {...c, done: !c.done} : c))} onAdvance={() => advance("complete")}/>;
      case "complete":  return <Card_Complete/>;
      default: return null;
    }
  })();

  const idx = idxOf(stepId);
  const phaseChipTone = stepId === "complete" ? "success" : "";
  const bambuStage = BAMBU_STAGE[stepId];

  return (
    <div className="stage" data-screen-label="Phase 1 · Pre-Print Preparation">
      <div className="scene-bg"></div>
      <div className="scene-lamp"></div>

      {/* Perspective table surface — top of element = laptop base */}
      <svg className="scene-table" viewBox="0 0 1440 320" preserveAspectRatio="none"
           xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
        <defs>
          <linearGradient id="tableFade" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="rgba(255,255,255,0.05)"/>
            <stop offset="100%" stopColor="rgba(255,255,255,0.005)"/>
          </linearGradient>
        </defs>
        {/* Surface fill */}
        <rect x="0" y="0" width="1440" height="320" fill="url(#tableFade)"/>
        {/* Perspective lines from vanishing point (720, 0) downward */}
        {[0,144,288,432,576,720,864,1008,1152,1296,1440].map((x,i) => (
          <line key={i} x1={720} y1={0} x2={x} y2={320}
                stroke="rgba(255,255,255,0.05)" strokeWidth="0.7"/>
        ))}
        {/* Horizontal depth lines */}
        <line x1="0" y1="110" x2="1440" y2="110" stroke="rgba(255,255,255,0.04)" strokeWidth="0.6"/>
        <line x1="0" y1="220" x2="1440" y2="220" stroke="rgba(255,255,255,0.025)" strokeWidth="0.6"/>
        {/* Table front edge — top of SVG, aligns with laptop base */}
        <line x1="0" y1="1" x2="1440" y2="1" stroke="rgba(255,255,255,0.2)" strokeWidth="1.5"/>
      </svg>

      <LaptopScene/>
      <BambuMock stage={bambuStage} slicedView={sliced}/>

      <div className="floor-anchor">
        <span className="glow"></span>
        Cornell Tech · MakerLAB
      </div>

      <LaptopStatusPins pins={PINS[stepId] || []} />

      <div className="phase-nav">
        <a href="Phase 1 Prototype.html" className="active">Phase 1</a>
        <a href="Phase 2 Prototype.html">Phase 2</a>
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
          Phase 1 · Pre-Print Preparation
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
          <div className="sub">First-time user</div>
        </div>
      </div>

      <div className="controls">
        <span className="ctrl-label">Demo</span>
        <button className="ctrl-btn" disabled={idx === 0} onClick={() => setStepId(PH1_STEPS[Math.max(0, idx - 1)].id)}>
          <i data-lucide="chevron-left" width="14" height="14"></i> Prev
        </button>
        <button className="ctrl-btn primary" disabled={idx === PH1_STEPS.length - 1}
                onClick={() => setStepId(PH1_STEPS[Math.min(PH1_STEPS.length - 1, idx + 1)].id)}>
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
  root.render(<App />);
}
