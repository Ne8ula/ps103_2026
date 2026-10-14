// phase1-laptop.jsx — Stylized laptop with Bambu Studio mock screen
const LaptopScene = ({ stage = "intro" }) => {
  // stage drives what's shown on the laptop screen:
  // intro | studio-open | new-project | import | printer-select | filament-select | support | slice | export
  return (
    <svg className="scene-laptop" viewBox="0 0 720 460" xmlns="http://www.w3.org/2000/svg" aria-label="Laptop with Bambu Studio">
      <defs>
        <linearGradient id="lid" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#3a3d44"/>
          <stop offset="100%" stopColor="#22252b"/>
        </linearGradient>
        <linearGradient id="base" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#2a2c32"/>
          <stop offset="100%" stopColor="#15171b"/>
        </linearGradient>
        <linearGradient id="screen" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#f6f6f8"/>
          <stop offset="100%" stopColor="#e0e0e6"/>
        </linearGradient>
      </defs>
      {/* Screen back */}
      <rect x="60" y="20" width="600" height="350" rx="14" fill="url(#lid)" stroke="rgba(0,0,0,0.5)"/>
      {/* Bezel */}
      <rect x="74" y="34" width="572" height="322" rx="6" fill="#0a0b0d"/>
      {/* Display */}
      <rect x="80" y="40" width="560" height="310" rx="3" fill="url(#screen)"/>
      {/* Camera */}
      <circle cx="360" cy="28" r="2" fill="#0a0b0d"/>
      {/* Base / hinge */}
      <path d="M 30 370 L 690 370 L 666 410 L 54 410 Z" fill="url(#base)" stroke="rgba(0,0,0,0.5)"/>
      <rect x="280" y="370" width="160" height="6" rx="2" fill="#0a0b0d"/>
      {/* Trackpad hint */}
      <rect x="290" y="386" width="140" height="3" rx="1.5" fill="rgba(255,255,255,0.04)"/>
    </svg>
  );
};

window.LaptopScene = LaptopScene;
