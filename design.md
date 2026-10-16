# Benchmate — R9 Implementation

Implemented 14 October 2026 in the existing React/Vite/Three.js project, following the user's explicit approval to move from concepts to working UI. Branding refreshed on 16 October 2026 against [the supplied guide](BenchMate_Brand_Guide.html). This document describes the current app. The [previous R2 design document](docs/evidence/r9-implementation/baseline/design.md) is retained as history, including prior reference roles and generation provenance.

## Reference And Appearance

All eight **selected final** R9 boards were opened and inspected, along with REVIEW.md, screen-map.json and generation-inputs.json. Superseded `*-initial.png` files were not used as implementation targets. The [original reference packet](docs/design/revisions/benchmate-20261014-workflow-r9/review.html) is unchanged; its pending-implementation statements describe that historical concept pass. No new design generation, paid service, screenshot-based control or whole-screen image background was introduced.

| Token | Value / Treatment |
|---|---|
| Purple | `#7146AE` — navigation, current state, links and focus |
| Citron | `#CCDE72` — action end-caps and selected phase rings |
| Cloud / White / Graphite | `#F3F4F8` / `#FFFFFF` / `#292733` |
| Typography | Locally hosted DM Sans, 24px page headings, 15–16px body/controls, approximately 12px metadata |
| Glass | Translucent Cloud/White/Blue layers, visible art beneath captions, soft double highlights, backdrop blur and restrained edge fluting |
| Matrix | Ordered dot fields and small ASCII glyph patches on art; dot dividers, panel-edge gutters and selected navigation markers |
| Touch | At least 44px control/label targets; primary actions 54px |

Titles, headings and authored subtitles use initial capitals without periods. Technical casing is preserved. Body prose stays in sentence case. User-entered captions remain exactly as entered. Matrix patterns never cover the selected photo or first-layer evidence; panel dots are confined to the edge gutter away from text and input values.

## Layout And Components

`UI.jsx` supplies glass surfaces, dominant actions, contextual rows, disclosures, phase rails, segments and tabs. `Browse.jsx`, `GuideContent.jsx`, `PhotoHelp.jsx` and `Sheets.jsx` separate destinations from task guidance. The shell keeps a scrollable content region between the header and dock. The dock occupies layout space; it does not overlay the scroll region. Narrow screens fill the viewport; desktop uses a 393px interior phone presentation with optional surrounding captions. Dynamic viewport height and safe-area insets are supported.

Home, Collection, Community and Profile share four browsing tabs. Bambu Projects remains nested under Home. Active guidance replaces browsing tabs with Back, Help, state-derived phases, one dominant action and Save And Pause. Detail disclosures and source-linked sheets preserve the checkpoint. Native dialogs trap focus, Escape closes them and focus returns to the opener.

Small milestones use a restrained check token. There are no streaks, points, fake progress percentages or timers for the printer. The brief photo-processing animation is explicitly a scripted demonstration; reduced motion removes it and other interface motion.

## Original 3D Representation

The original reusable cat retains its rounded head, pointed ears, paws and curved tail, with closed-eye details and a cloud-blue physical material. Fine layer banding, local studio lighting and a contact shadow provide depth. It is original visualization geometry, not a validated printable model.

Task views include a procedural spool, schematic printer, seated gold plate with alignment stops, thin first-layer lines, cleaning props and a cat on the plate. The printer has a dark enclosure, gantry and illustrative toolhead; these are not dimensionally accurate X1 parts. The plate is shown **seated**, correcting the reference's floating placement. Ripple Tray and Cable Pebble use original preview geometry and explicitly have no working guides.

Three.js remains lazy-loaded. Rendering occurs only on initial mount, resize and camera-preset changes. GPU resources and contexts are released on teardown. No requestAnimationFrame loop or idle scene animation runs. Pixel ratio is capped. The non-WebGL path provides accessible original vector illustrations and retains all workflow controls.

## State, Persistence And Honesty

The reducer retains navigation-independent completion. Phase markers derive from actual completed checkpoints. End-job and cooling confirmations gate cleaning. Reviewed setup clears the issue only after an explicit action; downstream preparation must then be repeated. A pause freezes the exact issue stage, selected photo, confirmations and task, independently of browsing navigation.

Storage version 2 keeps the original key and explicitly migrates version 1. Backups and recovery notices protect legacy or unreadable data. Completed records, saved ideas, identity, settings and local social drafts are distinct from the current guide. No remote service is contacted by these interactions.

Photo selection normalizes browser-decodable JPEG/PNG/WebP files into a bounded local JPEG. HEIC support depends on browser decoding and provides a useful fallback error. Camera streams are stopped on capture, cancel, navigation and unmount; late permission responses are discarded safely. The built-in synthetic SVG is reliable without camera access. Uploaded photographs are never diagnosed: their review screen says **Your Photo Has Not Been Analyzed**. The demo image alone illustrates a possible lifting edge, without a cause or confidence claim.

## Verification And Scope

[Actual Implementation Gallery](docs/evidence/brand-refresh/review.html) · [Brand Refresh And Test Results](docs/evidence/brand-refresh/REVIEW.md)

The implementation was inspected against each of the eight R9 boards. State tests, a production build and real headless-Chromium renders verify software behavior. Camera media tests use a synthetic stream, not physical camera evidence. No native iOS, real printer, physical print, remote community, automatic vision or validated print profile is claimed. The equipment source register remains authoritative; generated hardware and copy are not procedure authority.
