// phase2-printer.jsx — Stylized Bambu X1 Carbon printer scene
// All highlights are driven by the `highlight` prop:
//   "none" | "screen" | "sd" | "plate" | "spool" | "spool-dock" | "screen-confirm" | "tabs"

const PrinterScene = ({ highlight = "none", sdInserted = false, plateClean = false, plateAnimating = false, showBackCue = false, unloadSubStep = null, oldFilamentRemoved = false, newFilamentLoaded = false, printing = false, progress = 0, state = null, speed = "normal", screenStatus = null, screenDetail = null, screenColor = null, statusPin = null, doorOpen = false, plateReseating = false, reseatDone = 0, modelRemoved = false }) => {
  // Backwards-compat: phase 4/5 pass `state` (idle | heating | printing | paused | error | done) and `progress` (0-100).
  // Map state → printing/highlight if `state` provided.
  const isPrinting = printing || state === "printing" || state === "heating";
  const isDone = state === "done";
  const filamentFeeding = newFilamentLoaded && !isPrinting;
  const isAlert = state === "error" || state === "paused";

  const showSdRing = highlight === "sd";
  const showPlateRing = highlight === "plate";
  const showSpoolRing = highlight === "spool";
  const showDockRing = highlight === "spool-dock";
  const showScreenRing = highlight === "screen" || highlight === "screen-confirm" || highlight === "tabs" || highlight === "bed-temp";

  return (
    <div className={`printer-scene ${isAlert ? "printer-alert" : ""} ${isDone ? "printer-done" : ""}`}>
      {/* Floor + perspective grid */}
      <div className="floor-grid"></div>

      {/* Printer body — front view, slightly 3/4 angle via skew */}
      <div className="printer-body">
        {/* Top filament spools — 3 across, centered above chassis */}
        <div className="top-spools" aria-hidden="true">
          <div className="ts-rail"></div>
          <div className="ts-spool"><div className="ts-hub"></div><div className="ts-feed"></div></div>
          <div className="ts-spool blue"><div className="ts-hub"></div><div className="ts-feed"></div></div>
          <div className="ts-spool gray"><div className="ts-hub"></div><div className="ts-feed"></div></div>
        </div>

        {/* Outer chassis */}
        <div className="chassis">
          {/* Bambu Lab branding strip top */}
          <div className="brand-strip">
            <span>The Bust</span>
            <span className="model">MakerLAB · Bay A</span>
          </div>

          {/* Glass enclosure / front door */}
          <div className="enclosure">
            {/* Top frame with LED bar */}
            <div className="led-bar"></div>

            {/* Build chamber — view inside */}
            <div className="chamber">
              {/* Back wall pattern */}
              <div className="chamber-back"></div>

              {/* Print head gantry (top) */}
              <div className="gantry">
                <div className="gantry-rail"></div>
                <div
                  className={`print-head ${isPrinting ? "printing" : ""} ${highlight === "auto-level" ? "leveling" : ""}`}
                  style={isPrinting ? { animationDuration: speed === "fast" ? "0.5s" : speed === "slow" ? "3s" : "2.4s" } : {}}
                >
                  <div className="ph-nozzle"></div>
                  {(filamentFeeding || unloadSubStep === "load-new") && <div className="ph-purge-drip"></div>}
                </div>
              </div>

              {/* Build plate — hidden while the plate is outside (reseat steps 0-1),
                  fades back in once the external plate slides home (step 2+) */}
              <div className={`build-plate ${plateClean ? "clean" : ""}`}
                   style={{
                     opacity: plateReseating && reseatDone < 2 ? 0 : 1,
                     transition: "opacity 300ms ease 700ms",
                   }}>
                <div className="plate-grid"></div>
                {plateAnimating && <div className="wipe-shine"></div>}
              </div>

              {/* Model cat — sits on build plate, scales with progress (hidden once removed) */}
              {!modelRemoved && !plateReseating && (printing || state === "printing" || state === "paused" || state === "error" || isDone) && (
                <div style={{
                  position: "absolute",
                  bottom: "26%",
                  left: "50%",
                  transform: "translateX(-50%)",
                  width: "38%",
                  height: (isDone ? "68%" : (Math.max(4, progress * 0.68) + "%")),
                  zIndex: 2,
                  transition: "height 350ms ease",
                  filter: "drop-shadow(0 0 6px rgba(255,255,255,0.25))",
                }}>
                  <svg viewBox="0 0 80 68" width="100%" height="100%"
                       preserveAspectRatio="xMidYMax meet" style={{ display: "block" }}>
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
              )}

              {/* Plate ring overlay */}
              {showPlateRing && <div className="ring ring-plate"></div>}
              {highlight === "auto-level" && <div className="ring ring-plate orange"></div>}

              {/* Wipe cloth — animated over the build plate */}
              {plateAnimating && <div className="wipe-cloth"></div>}
            </div>

            {/* Door handle */}
            <div className="door-handle"></div>

            {/* Glass reflection */}
            <div className="glass-reflection"></div>
          </div>

          {/* Door panel overlay — animated open/close when wiping, or swings open when doorOpen */}
          {plateAnimating && (
            <div className="door-panel animating">
              <div className="door-panel-handle"></div>
            </div>
          )}
          {!plateAnimating && doorOpen && (
            <div className="door-panel open">
              <div className="door-panel-handle"></div>
            </div>
          )}

          {/* Front bezel — controls below glass */}
          <div className="front-bezel">
            {/* Touchscreen display */}
            <div className={`touchscreen ${highlight === "screen-confirm" ? "confirm" : ""} ${highlight === "bed-temp" ? "bed-temp" : ""}`}>
              {highlight === "screen-confirm" && (
                <>
                  <div className="ts-icon-large">✓</div>
                  <div className="ts-text-large">SD Card Inserted</div>
                  <div className="ts-sub">cat_figure.gcode.3mf detected</div>
                </>
              )}
              {highlight === "tabs" && (
                <div className="ts-tabs">
                  {/* Step a: tap the Filament tab — show list + pulsing tap cursor */}
                  {(unloadSubStep === "tap-tab" || !unloadSubStep) && (
                    <>
                      {unloadSubStep === "tap-tab" && <div className="ts-tap-cursor"></div>}
                      <div className="ts-content">
                        <div className="ts-row">PLA Basic — White</div>
                        <div className="ts-row">PLA Basic — Black</div>
                        <div className="ts-row">PETG</div>
                      </div>
                    </>
                  )}
                  {/* Step b: confirm pull-back dialog */}
                  {unloadSubStep === "pull-back" && (
                    <div className="ts-content ts-dialog-content">
                      <div className="ts-dialog-msg">Pull back<br/>filament?</div>
                      <div className="ts-confirm-btn">Confirm ✓</div>
                    </div>
                  )}
                  {/* Step c: unloading in progress */}
                  {unloadSubStep === "unload" && (
                    <div className="ts-content ts-unloading-content">
                      <div className="ts-unload-label">Unloading…</div>
                      <div className="ts-unload-track"><div className="ts-unload-bar"></div></div>
                    </div>
                  )}
                </div>
              )}
              {highlight === "bed-temp" && (
                <div className="ts-bed-temp">
                  <div className="ts-temp-label">Bed Temp</div>
                  <div className="ts-temp-val">65°C</div>
                  <div className="ts-temp-sub">Setting temperature…</div>
                </div>
              )}
              {(highlight !== "screen-confirm" && highlight !== "tabs" && highlight !== "bed-temp") && (
                <>
                  {(() => {
                    const col = screenColor === "orange" ? "var(--orange)"
                              : screenColor === "red"    ? "var(--red)"
                              : screenColor === "blue"   ? "var(--blue)"
                              : "var(--green)";
                    return (
                      <div className="ts-status" style={{ color: col }}>
                        <span className="ts-dot" style={{ background: col, boxShadow: `0 0 6px ${col}` }}></span>
                        <span>{screenStatus || (isPrinting ? "Printing…" : sdInserted ? "Ready" : "Idle")}</span>
                      </div>
                    );
                  })()}
                  <div className="ts-line">{screenDetail || (sdInserted ? "cat_figure.gcode.3mf" : "Insert SD card")}</div>
                  <div className="ts-line dim">X1 Carbon · Bay A</div>
                </>
              )}
            </div>

            {/* SD card slot */}
            <div className={`sd-slot-wrap ${showSdRing ? "highlight" : ""}`}>
              <div className="sd-slot">
                <div className="sd-mouth"></div>
                {sdInserted && <div className="sd-card-inserted"></div>}
              </div>
              <div className="sd-label">SD</div>
            </div>

            {/* Power button */}
            <div className="power-btn"></div>
          </div>

          {/* Side: filament spool dock */}
          <div className={`spool-dock ${showDockRing ? "highlight" : ""}`}>
            <div className={`spool
              ${oldFilamentRemoved && !newFilamentLoaded ? "empty" : ""}
              ${newFilamentLoaded ? "new" : ""}
              ${filamentFeeding || unloadSubStep === "store-old" ? "feeding" : ""}
              ${unloadSubStep === "unload" ? "rewinding" : ""}
              ${unloadSubStep === "load-new" ? "spinning" : ""}
            `}>
              <div className="spool-hub"></div>
              {!oldFilamentRemoved || newFilamentLoaded ? <div className="spool-windings"></div> : null}
            </div>
            <div className="spool-shelf"></div>
            <div className={`filament-feed
              ${filamentFeeding ? "active" : ""}
              ${unloadSubStep === "unload" || unloadSubStep === "tft-pull" ? "retracting" : ""}
              ${unloadSubStep === "load-new" ? "loading" : ""}
            `}></div>
          </div>

          {statusPin && (
            <div style={{ position: 'absolute', bottom: '100%', marginBottom: '8px', right: 0, display: 'flex', alignItems: 'center', gap: '8px', flexDirection: 'row-reverse', pointerEvents: 'none', zIndex: 10 }}>
              <div className={`pin-target ${statusPin.tone}`}>
                {statusPin.icon && <i data-lucide={statusPin.icon} width="14" height="14"></i>}
              </div>
              <div className={`pin-label ${statusPin.tone}`}>{statusPin.label}</div>
            </div>
          )}
          {showSdRing && <div className="ar-bigring sd-bigring"></div>}
          {showScreenRing && <div className="ar-bigring screen-bigring"></div>}
          {/* Back-direction cue — anchored to right of chassis for Step 5 */}
          {showBackCue && (
            <div className="back-direction-cue">
              <div className="bdc-label">This is the Filament Component</div>
              <div className="bdc-arrow">
                <i data-lucide="arrow-right" width="24" height="24"></i>
              </div>
            </div>
          )}
          {/* Build plate sliding back in during reseat (Step 25) */}
          {plateReseating && (
            <div className={`plate-reseat-elem step${reseatDone}`}></div>
          )}

          {/* Base / feet */}
          <div className="printer-base"></div>
        </div>

        {/* Floor shadow */}
        <div className="floor-shadow"></div>
      </div>

      {/* AR rings */}
      {showSpoolRing && <div className="ar-bigring spool-bigring"></div>}

      {/* Printer label floating above */}
      <div className="printer-label">
        <span className="pl-name">Bambu Lab X1 Carbon</span>
        <span className="pl-loc">The Bust · Bay A</span>
      </div>
    </div>
  );
};

window.PrinterScene = PrinterScene;
