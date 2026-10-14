# iPhone / matte glass / real 3D — bounded redesign

Retained pre-implementation brief. The pass is now implemented; see [REVIEW.md](REVIEW.md) for actual results and later-reference status.

User direction, 13 October 2026: mobile app or iOS app mockup; current UI is too generic; use actual 3D product models with aesthetic shaders and materials; prefer fractal/fluted glass or very matte glass. This pass replaces the desktop-first presentation while retaining the tested project logic.

## Six reference roles

All six inline attachments were visually inspected. They have no available local attachment paths. The Weave prompt describes each explicitly; no image upload or private file transmission occurs.

1. **Lavender 3D office:** legible spatial object as the organizing element. Avoid room scenes, camera panels and dashboard chrome.
2. **Gray/yellow valve desktop:** technical precision, selective wireframe and one highlighted concern. Avoid numeric telemetry and multi-card density.
3. **Two mobile valve screens:** primary layout reference, large 3D object, sparse title, lower contextual sheet. Avoid oversized machinery or fake diagnostics.
4. **Exploded Keychron switch:** strong studio material rendering, contact/depth, matte translucent frame. Do not explode a solid cat or borrow branding.
5. **Fluted cobalt/orange glass:** refracted ribs and recursive facets at glass edges. Keep high-chroma color away from readable text; do not copy the caption.
6. **Matte green tile study:** primary material reference, cloudy green diffusion, milky edge highlights and soft grain. Avoid a tiled dashboard.

Synthesis: an ice-gray iPhone surface, charcoal type, frosted contextual sheet, small lime accents, sculptural satin celadon cat. The same object appears across preparation and completion. Recovery uses amber sparingly.

## Scope and boundaries

- Original Three.js 3D cat geometry, studio lighting, custom micro-layer material shader, subtle environmental reflection, real dimensional views. This is visualization geometry, not manufacturing geometry.
- Discrete camera presets and static material presentation; no autoplay, orbit animation, new motion choreography or animated screen transitions. Thus this pass requests a still-image reference only.
- iPhone layout first: compact navigation, four-phase rail, scrollable task content, persistent bottom action area, modal bottom sheets, safe-area spacing, 44 px controls.
- Desktop presents the same app inside a phone-sized frame. Browser-based interactive mockup; not a compiled SwiftUI app or claimed iOS simulator test.
- Preserve current equipment facts, recovery, local persistence and explicit completion. Source/support/help remain available without leaving the task.
- Retain a clearly labeled non-WebGL fallback. The core guide must work even if rendering fails.

## Planned ownership

`src/main.jsx`, new `src/mobile.css`, new `src/components/ProductScene.jsx`, new `src/scene/` modules, `src/components/Dialog.jsx`, project illustration wording in `src/data/project.js`, `index.html`, dependencies and required documentation. Existing styles/illustrations may be reused for the fallback only. Source snapshots and hashes precede edits.

## Run

Model: Nano Banana 2.1. One 2K 16:9 PNG, High thinking, seed 104, web search off, no image inputs. User approved 5 credits, then supplied the visual direction. Requoted revised prompt: still 5 credits. Exactly one run submitted: `1e3a139b-a00b-4574-ba21-e7a4114ed914`. Implementation awaits actual output inspection and completed provenance.
