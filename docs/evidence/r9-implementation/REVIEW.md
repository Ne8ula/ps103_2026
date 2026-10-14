# R9 Implementation Evidence

14 October 2026 · Actual React/Vite/Three.js browser implementation

[Open The Screenshot Gallery](review.html) · [Browser Results](verification.json) · [Original R9 Reference Gallery](../../design/revisions/benchmate-20261014-workflow-r9/review.html)

## Result

All 24 concept screens are connected in the running mockup, with additional private post preview, reviewed-setup checkpoint, local discussion, preferences, notification/privacy explanations and record detail. Native components provide every control and text element. None of the generated reference screens or screenshot slices are bundled into the application.

The reference packet remains untouched. `baseline/` preserves the original R2 source and documentation before implementation; `baseline-hashes.json` records the inspected source files. The workspace was already entirely untracked, so no Git baseline or committed diff is claimed.

## Verification Results

| Check | Actual Result |
|---|---|
| `npm test` | 17 passed, 0 failed |
| `npm run build` | Passed; lazy Three.js module about 131 KB gzip, with nonblocking chunk-size warning |
| `node scripts/verify-r9.mjs` | Passed against production preview on port 4174 |
| Development server | Started on port 5174; actual app opened and inspected in connected Chrome |
| Browser exceptions | None captured by the verification page's `pageerror` listener |
| Main path | Home, catalog, detail, personalization, setup, plate, material, handoff, first layer, printing, cooling, both checks, completion |
| Persistence | Names, purpose, notes, independent collection records, profile, preferences, saved ideas, community drafts and sharing draft retained locally |
| Photo flow | File selection, invalid-file handling, demo image, processing/cancel and unchanged image across review |
| Camera flow | Simulated permission denial; synthetic media-stream capture/cancel; tracks ended afterward |
| Recovery | End-job/cooling gates, cleaning, reviewed setup, issue retained across reload until setup review, repeated preparation |
| Unknown issue | Unanalyzed selected image, unresolved support state after pause/reload, actual summary download |
| Exports | Real text files captured and content read back: project record and support summary |
| Navigation | Back does not create completion; active guide omits browsing tabs; nested Bambu Projects under Home |
| Help/focus | Expanded contextual help and source links; Escape closes dialog and returns focus |
| Responsive | 393×852, 320×740, 430×932, 1440×1000; no document horizontal overflow at checked widths |
| Accessibility spot checks | Keyboard focus, labeled controls, gated checkbox actions, long unbroken profile name and long bio |
| Reduced motion | System preference and local preference disable interface animation |
| WebGL unavailable | Forced failure displays vector fallback and remains navigable |

Unit tests cover version 1 migration, legacy completions, unreadable-data recovery copies, failed-backup overwrite protection, exact paused issue state, photo honesty/continuity, restart invalidation and independent records. Browser migration UI was not separately exercised; the loader/reducer are verified by these unit tests.

Browser automation uses an isolated headless Chromium profile and software WebGL. The selected-photo fixture is an implementation screenshot, not a person's photograph. `photo-320.png` intentionally shows the purple synthetic camera frame used by the capture test. Camera evidence does **not** establish physical camera, iPhone or Safari compatibility. Software checks do not establish physical printer safety or print success.

## Comparison Against All Eight Selected Reference Boards

| Reference | Implementation Evidence | Comparison And Corrections |
|---|---|---|
| 01 Discover | [Board 1](board-1.png) | Three connected browsing destinations; pearl/orchid cat, dark studio stage, glass art captions, citron actions and four tabs. Preview projects have explicit unavailable-guide labels and working save controls. |
| 02 Prepare | [Board 2](board-2.png) | Editable name/purpose, setup facts, plate detail and true phase completion. The plate sits on a platform against rear stops rather than floating as an installation instruction. Long detail scrolls. |
| 03 Start Print | [Board 3](board-3.png) | Procedural spool, official-control handoff, first-layer-only illustration. No material sensor, print timer or actual start control. Print remains current until explicitly completed. |
| 04 Photo Help | [Board 4](board-4.png) | The same selected synthetic first-layer image appears in capture, processing and finding. Pattern overlays stay out of evidence. Selected photographs get a distinct Unanalyzed Photo review, never the scripted finding. |
| 05 Recovery | [Board 5](board-5.png) | Independent recovery rail, unchecked end/cooling confirmations, cleaning, unresolved support summary. No false success marks or claim that a physical job was stopped. |
| 06 Finish | [Board 6](board-6.png) | Printing remains in Print; cooling and quality are in Finish; both object/workspace checks gate completion. Expanded More Detail changes to Less Detail with an upward chevron. |
| 07 Complete/Share | [Board 7](board-7.png) | All four phases complete only after explicit checks. A local record opens and downloads. Share composer fits Preview Post at 393px and leads to an additional [private preview](22-post-preview-393.png). |
| 08 Supporting | [Board 8](board-8.png) | Clearly fictional Community; editable local Profile; paused first-layer issue with Prepare and At Printer complete, Print current. Pausing explicitly does not pause the printer. |

The implementation intentionally uses a coherent original procedural cat instead of generated photorealistic cat variations. The printer and task props are readable schematic geometry, not manufacturer CAD. A consistent 24px title/15–16px body system replaces the variable generated typography. The original synthetic first-layer illustration is clearly labeled. Text, fields, sources, progress and actions are all real DOM components.

Observed refinements made during visual review: printer enclosure/gantry improved; foreground cat enlarged on Home; gold plate grain added; spool spokes expose the material; phase connectors made visible; obsolete download toasts cleared on navigation; fallback notice moved away from the glass caption; share art shortened to keep Preview Post reachable; decorative panel matrix moved into the edge gutter to avoid text and inputs. Source/help content remains scrollable above the fixed dock.

## Capture Index

- 25 numbered captures cover the main and branch destinations, with private preview as an extra screen
- Additional 320px, 430px and desktop views, long profile content, empty photo capture and forced fallback
- `board-1.png` through `board-8.png` group actual screenshots for comparison; they are evidence only and are not app assets
- [Downloaded Project Record](downloaded-project-record.txt) and [Downloaded Support Summary](downloaded-support-summary.txt)

## Limits

No physical camera, iPhone/Safari, virtual keyboard, screen reader or physical printer test. No remote post, real account, backend diagnosis, printer integration, validated model/profile, machine-ready file, timing estimate, temperature measurement or physical success claim. Official equipment source content retains the prior 13 October 2026 access date and was not newly fetched during this implementation.
