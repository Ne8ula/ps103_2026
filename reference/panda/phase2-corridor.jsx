// phase2-corridor.jsx — Hallway / lab walking scene with 3D perspective
// Used only for Step 1: "Walking to the printer"

const CorridorScene = ({ targetVisible = true, approaching = false, onApproach }) => {
  return (
    <div className={`corridor-scene ${approaching ? "approaching" : ""}`}>
      {/* Perspective floor */}
      <div className="cor-floor">
        <div className="cor-floor-grid"></div>
      </div>
      {/* Ceiling */}
      <div className="cor-ceiling"></div>
      {/* Walls */}
      <div className="cor-wall left"></div>
      <div className="cor-wall right"></div>

      {/* Workbench surface — printers sit on this */}
      <div className="cor-bench">
        <div className="cor-bench-face"></div>
      </div>

      {/* Distant printers along the back wall — small */}
      <div className="bg-printer p1"></div>
      <div className="bg-printer p2"></div>
      <div className="bg-printer p3 target" onClick={onApproach} style={{cursor: onApproach ? "pointer" : "default"}}>
        {targetVisible && (
          <>
            <div className="target-glow"></div>
            <div className="target-label">
              <span>Bambu Lab X1 Carbon</span>
              <span className="sub">The Bust · 18m</span>
            </div>
          </>
        )}
      </div>
      <div className="bg-printer p4"></div>

      {/* Floor arrow path — chevrons leading toward target */}
      <svg className="cor-arrow-path" viewBox="0 0 800 500" preserveAspectRatio="none">
        <defs>
          <linearGradient id="arrowGrad" x1="0" y1="1" x2="0" y2="0">
            <stop offset="0%" stopColor="#0a84ff" stopOpacity="0.85"/>
            <stop offset="100%" stopColor="#0a84ff" stopOpacity="0.05"/>
          </linearGradient>
        </defs>
        {/* Three chevrons in perspective */}
        <path d="M 380 470 L 400 450 L 420 470" stroke="url(#arrowGrad)" strokeWidth="6" fill="none" strokeLinecap="round" strokeLinejoin="round" opacity="0.95"/>
        <path d="M 388 410 L 400 396 L 412 410" stroke="url(#arrowGrad)" strokeWidth="5" fill="none" strokeLinecap="round" strokeLinejoin="round" opacity="0.85"/>
        <path d="M 392 360 L 400 350 L 408 360" stroke="url(#arrowGrad)" strokeWidth="4" fill="none" strokeLinecap="round" strokeLinejoin="round" opacity="0.75"/>
        <path d="M 394 320 L 400 313 L 406 320" stroke="url(#arrowGrad)" strokeWidth="3.5" fill="none" strokeLinecap="round" strokeLinejoin="round" opacity="0.6"/>
        <path d="M 396 290 L 400 285 L 404 290" stroke="url(#arrowGrad)" strokeWidth="3" fill="none" strokeLinecap="round" strokeLinejoin="round" opacity="0.45"/>
      </svg>

      {/* Distance counter pip */}
      <div className="distance-pip">
        <i data-lucide="footprints" width="14" height="14"></i>
        <span><strong>18m</strong> · 25 steps</span>
      </div>
    </div>
  );
};

window.CorridorScene = CorridorScene;
