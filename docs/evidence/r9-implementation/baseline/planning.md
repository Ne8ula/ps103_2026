# Benchmate — implementation and verification plan

## Objective

Build an independent vertical-slice companion that helps a novice move from preparation to a completed personal project. Manufacturers are the proposed paying customer; their equipment owners are the end users. This demo illustrates that business direction without representing Bambu Lab as a sponsor, partner or customer. The user's subsequent direction makes this an interactive iPhone app mockup, centered on actual 3D models and distinctive matte glass. The desktop browser presents that same app inside a phone frame.

The supplied product documents are authoritative for product direction; PANDA is prior design work; current official Bambu documentation is the authority for equipment facts. See the complete [source register](docs/source-register.md), including access dates, supported claims and exclusions.

## Input inventory

The starting workspace contained only `.git`, with no stack or application to preserve. Both Google Docs were retrieved as full text through the connected Drive tool; their snapshots are in `docs/evidence/`. The 92,457-byte PANDA ZIP was extracted into `reference/panda/`, separate from new code. Its original SHA-256 is `7EA5BD6F7E71BBE3AE0A99A3F7F07485EBC20BCD2283B246CA55DF20D4162AC2`.

Confirmed actual HTML script relationships:

| User-facing phase | Entry | Application | Shared dependencies |
|---|---|---|---|
| Studio preparation | `Phase 1 Prototype.html` | `phase1-app.jsx` | `phase1-bits.jsx`, `phase1-laptop.jsx`, `colors_and_type.css` |
| Printer preparation | `Phase 2 Prototype.html` | `phase3-app.jsx` | `phase2-bits.jsx`, `phase2-corridor.jsx`, `phase2-printer.jsx`, shared CSS |
| Print and monitoring | `Phase 3 Prototype.html` | `phase4-app.jsx` | `phase4-bits.jsx`, `phase2-printer.jsx`, shared CSS |
| Completion and post-print | `Phase 4 Prototype.html` | `phase5-app.jsx` | `phase4-bits.jsx`, `phase2-printer.jsx`, shared CSS |

Inspected actual step arrays, contextual responses, component illustrations, timers, recovery logic and post-print handling. The archive includes no accompanying research and no actual `cat_figure.3mf`, despite the code naming it. The hosted URL was inaccessible to the web fetch tool; the code was used regardless. Research excerpts reported inside the supplied business document remain secondary evidence, not independently verified interviews.

## PANDA adaptation matrix

| Decision | PANDA element / evidence | Benchmate treatment |
|---|---|---|
| Keep | Four HTML phases and post-print inspection/reseat in `phase5-app.jsx` | Connected Prepare → At the printer → Print → Finish, including cooling, quality and restoring the workspace. |
| Keep | Short GlassCard task text and contextual questions in each app | One task heading, short instruction and optional detail; no mandatory conversation. |
| Keep | Printer pins and illustrated parts | Original 3D plate, spool, printer and first-layer schematics; SVG fallback. |
| Keep | `first-watch`, anomaly and recovery states in `phase4-app.jsx` | First-layer observation plus a complete user-reported poor-adhesion branch. |
| Keep | Plain-language contextual explanations | At most two scripted suggested questions initially; sources and current project context attached. |
| Keep | Cat and completion recognition | Original reusable 3D cat; project name and desk/gift purpose persist to final record. |
| Adapt | XR spatial pins | Annotations inside one bounded illustration; no room-coordinate claims. |
| Adapt | Glass panels / per-phase long step rails | Matte glass action dock and four-phase summary; detailed completion ledger in a sheet on demand. |
| Adapt | `walk` / corridor / Bay A | Direct transition to “At the printer”; no tracking or directions. |
| Adapt | “SD detected”, file imported/exported, remaining PLA estimates | Explicit example setup and user checks. No operation or measurement is claimed. |
| Adapt | Ask AI / fallback strings | Clearly labeled scripted source-linked help; no paid model needed at runtime. |
| Adapt | Staff-notified timer | Reviewable local support handoff with equipment, checkpoint, issue and history; no send or arrival promise. |
| Adapt | `visited` marks done in old rails | Separate `completed[]`; navigation cannot create completion. |
| Adapt | SD transfer | Verified X1 Wi-Fi Studio route in core; SD alternative linked from help. |
| Remove | Headset pairing, gaze/pinch cursor effects, corridor navigation | Standard responsive keyboard and pointer interaction. |
| Remove | Persistent faux camera, progress/temperature simulation | No live feed, countdown, estimated progress or telemetry. Scenario is labeled illustration. |
| Remove | Printer/material catalogs and forced filament swap | Fixed X1/PLA/PEI configuration; optional official loading guide only if needed. |
| Remove | Repeated acknowledgements, silent-mode speed change, invented staff arrival | Each confirmation records a useful project checkpoint or observation. |
| Verify | Hardcoded 60°C/220°C, duration/weight, support-angle recommendation | None reused. No print profile/model exists to justify them. |
| Verify | Isopropyl wipe and “cool enough to touch” fallback | E6 supports detergent cleaning; safe-touch sensing removed. |
| Verify | Clean/relevel/“resume” and “layer 24 reprinted” | End failed attempt, cool, clean, review Studio setup, new attempt. Exact reconstruction/repair success not claimed. |
| Verify | “Most failures happen here” / automatic fault diagnosis | Removed; image interpretation is the user's observation. |
| Verify | Cooling 52/42/32°C and two-minute stuck-model wait | No invented safe threshold or timer; refer to actual hardware and official plate guidance. |

## Selected configuration and assumptions

X1 Carbon with assumed installed 0.4 mm nozzle; Bambu PLA Basic on an external spool; Bambu gold Textured PEI plate, 256 × 256 mm X1 variant. Assembly and onboarding are complete, Studio is installed, and material is already loaded. A physical Wi-Fi handoff additionally requires Bambu's network plug-in and a configured printer connection. No credentials or integration are needed for this demo.

The model is an original **3D visualization**, not a downloadable manufacturing mesh. The project sequence is an authored prototype template, **not a physically validated printing process**. Selecting this equipment establishes demo applicability, not a certified operating profile. Real model validation is outside this slice. Shader colors and layers are an aesthetic study, not a material/color recipe or promise that one PLA spool prints multiple colors.

Personalization is limited to a 48-character optional name and desk/gift purpose. No CAD editor or arbitrary settings. Optional final note is limited to 500 characters.

## Journey and state transitions

`intro → personalize → studio → plate → filament → start → firstLayer → printing → cooling → quality → complete`

- Prepare: start, name/destination, inspect the illustrative Studio configuration.
- At the printer: clean/dry/seated plate; matching external spool and PLA top-cover condition.
- Print: physical start remains in Studio; labeled first-layer example; explicit observation; finish demonstration at the user's pace.
- Finish: room-temperature cooling/removal guidance; two quality/workspace checks; personalized completion and optional note; download a real text record.

Recovery: `firstLayer → question → stop → clean → restart review → studio (issue still open) → confirm reviewed setup → plate → filament → start → firstLayer`. Returning to Studio invalidates downstream completion and clears quality checks. The issue resolves only after setup is explicitly reviewed. The record retains the recovery and restart count.

Unknown: `question → support`. It remains unresolved across pause/reload. User can download the contextual handoff and open official support. An explicit “reported by mistake” action withdraws the report and records that correction; it does not pretend a fix happened.

Pause is orthogonal to the checkpoint. It preserves the current step and issue and prevents advancement. It never operates or represents a paused machine. Resume restores exactly the saved task. LocalStorage uses a versioned, namespaced record with shape checks and sensible recovery for corrupt/unsupported data. No cross-device sync. When storage fails, the app displays a warning and offers a text record.

Back changes the visible checkpoint only. Completed checkpoints remain explicitly completed; visiting a future checkpoint is not available. The two final checkboxes gate completion. Choosing a lifting demonstration disables the “looks good” action until the issue is addressed or a different scenario is deliberately selected.

## Implementation

Small React 19 / Vite 7.3.7 / Three.js 0.180.0 app; no backend or runtime service calls. Dependencies and fonts are locked locally. Equipment/source facts, authored content, reducer state, reusable sheets, renderer and presenter controls are separate modules. Original 3D geometry and shader code provide the primary visuals; original SVGs remain as fallback. PANDA files are retained intact and do not run as part of Benchmate. The renderer loads lazily, renders on demand and disposes GPU resources.

Execution plan and status:

1. Read product documents, inspect actual PANDA code, discover design workflow — done; the specific GenUI_Agent direct-model workflow was identified after the user clarified its location.
2. Verify current official X1/plate procedures — done in Chrome after web-fetch failures.
3. Implement connected states and local persistence — done; state tests cover gates/recovery/reload.
4. Execute approved fresh Weave references, inspect actual outputs, implement bounded passes — done for r1 and r2, two separately approved runs at 5 credits each. R2 used all six then-available user references before implementation. Exact provenance and the initial r1 workflow-discovery deviation are recorded in [design.md](design.md).
5. Rebuild presentation as an iPhone mockup with real 3D and matte glass — done for r2, retaining the existing state/recovery logic. Further peach/blue material references produced a separately approved [r3 material board](docs/design/revisions/benchmate-20261013-opal-r3/REVIEW.md) for 5 credits. It was inspected, but no UI implementation followed: the user requested stronger contrast, fewer decisions and concept approval before further code edits.
6. Run build/tests; inspect desktop/mobile; record limitations and screenshots — done for r2, with results below. No physical-print or owner-design acceptance is asserted.
7. Develop two [focused-progression visual concepts](docs/design/revisions/benchmate-20261013-focus-r4/review.html) — both specifically approved 5-credit runs completed and actual images inspected. The user selected B / Pocket Quest, then requested smaller text and closer use of new glass UI references before code changes.
8. Generate [refined task/detail and photo-help boards](docs/design/revisions/benchmate-20261014-interface-r5/review.html) — two built-in image-generation calls completed and inspected. Includes collapsed/expanded guidance, photo capture, processing and a possible finding. Exact model version and cost are unexposed; no additional Weave spend. No application code changed; source hashes verified. These static concepts remain under user review before implementation. No live photo analysis is claimed.

## Current iPhone / 3D verification (r2)

Current visual review: [r9 complete workflow](docs/design/revisions/benchmate-20261014-workflow-r9/review.html). Eight selected boards show 24 screens with Title Case headers and period-free titles/subtitles, using r8 purple/citron references. Includes the main path, capture/processing/possible finding, recovery/support, completion/Collection/share preview, Community/Profile and pause/resume. Eight initial generations plus seven targeted corrections were inspected. All six tracked source hashes match the pre-concept baseline; no app implementation or runtime verification was added.

Previous visual review: [r8 purple/citron, Community and Profile](docs/design/revisions/benchmate-20261014-social-r8/review.html). The user liked purple and explicitly expanded design scope to a secondary accent, Profile, Community and component-level matrix effects. Two calls produced four inspected static screens. No community/account backend or app code changes were made.

Earlier visual review: [r7 Home, Bambu projects and Collection](docs/design/revisions/benchmate-20261014-collection-r7/review.html). Four generated screens show the proposed navigation, a pearl/graphite/violet palette and stronger glass/matrix artwork. Three calls include one targeted proportion correction. Collection and extra Preview projects remain concepts; app code is unchanged.

Latest design-only work: [r6 warm glass and matrix inspection](docs/design/revisions/benchmate-20261014-dither-r6/review.html). Fresh generation using only the newest two images and video; earlier references excluded. One board inspected; no app implementation, motion or camera/vision backend added. The results below still describe r2.

`npm test`: **7 passed**. `npm run build`: **passed**. Chrome on Windows was checked at **393 × 852**, **320 × 740**, and **1440 × 1000**. The production build emits a nonblocking 500 KB uncompressed chunk-size warning for the lazy renderer (about 130 KB gzip). A concrete advisory in the previous Vite dependency led to a same-major update to 7.3.7; the resulting npm audit reported zero vulnerabilities.

- Actual WebGL geometry, material and all three discrete camera presets rendered; screenshots show the real canvas output.
- Happy path reached named completion with Miso, gift purpose, note and one restart. Both final checkboxes gated completion.
- Enter activated the primary action. Help retained the checkpoint, displayed at most two collapsed suggestions, and returned focus after Escape.
- Back and the checkpoint sheet confirmed that visiting a plate step did not fabricate completion.
- Unknown issue survived save/pause/reload; resuming restored its support boundary. The contextual handoff was reviewed without submission.
- Adhesion recovery led through stop, cooling/cleaning and reviewed setup for a new attempt. Pending issue survived a Studio reload and cleared only after explicit review.
- An actual 700-byte `benchmate-project-record (1).txt` was downloaded and read from Downloads; it contained Miso, gift, one restart and the note. Reset returned to entry.
- A focus-dependent scene resize was found to interfere with checkbox activation. It was removed, and both checks were then exercised successfully.
- Narrow decorative overflow was clipped within the product scene; main content and document width then matched the 320 px viewport. Sampled visible mobile buttons were at least 44 × 44 px.
- Desktop modal positioning was verified against the phone frame's actual rectangle. Representative entry, detail, recovery and completion screenshots were visually inspected.
- The sampled final error/warning log contained only unrelated extension messages, with no app-origin error in that sample.

Current captures: [desktop phone](docs/design/revisions/benchmate-20261013-ios-r2/implementation/after/desktop-phone.jpg), [entry](docs/design/revisions/benchmate-20261013-ios-r2/implementation/after/entry-393.jpg), [material detail](docs/design/revisions/benchmate-20261013-ios-r2/implementation/after/material-detail.jpg), [first layer](docs/design/revisions/benchmate-20261013-ios-r2/implementation/after/first-layer-393.jpg), [recovery](docs/design/revisions/benchmate-20261013-ios-r2/implementation/after/recovery-393.jpg), [completion](docs/design/revisions/benchmate-20261013-ios-r2/implementation/after/completion-393.jpg).

No physical iPhone/Safari, touchscreen, virtual keyboard, screen reader, 200% text-size or forced WebGL failure test was performed. Safe areas, dynamic viewport, reduced effects and SVG fallback are implemented, not certified on hardware. No real printer or physical print has been tested.

## Historical verification (r1, superseded presentation)

Tested with Node 24.14.0, npm 11.9.0 and connected desktop Chrome on Windows. `npm test`: **7 passed**. `npm run build`: **passed**, including after the Weave refinement. All 22 extracted PANDA files match the ZIP byte-for-byte; see [integrity evidence](docs/evidence/panda-integrity.json).

Observed in the actual rendered browser:

- Happy path completed with project “Miso”, gift destination and a saved note.
- Final completion button disabled until both quality/workspace checks were checked.
- Enter activated the task action; Escape dismissed the native help dialog and focus returned to the help opener.
- Help kept the same Studio checkpoint; Back plus the detail ledger confirmed an uncompleted plate visit stayed uncompleted.
- Save/pause and reload restored the printing checkpoint and retained name/purpose; guide pause boundary was visible.
- Adhesion issue survived reload, led through cleaning, returned to Studio with pending restart, then rejoined first-layer observation after new checks.
- Unknown issue generated a handoff containing current equipment, checkpoint, observation and recovery count. No support submission occurred.
- Completion download created an actual 599-byte `benchmate-project-record.txt` in Downloads, read back to verify name, purpose, nine completed checkpoints and note. The browser download-event listener timed out, but filesystem evidence confirmed the download succeeded.
- Reset returned to the entry state. Narrow viewport inspection at 390 × 844 showed no horizontal overflow.
- Desktop inspection at 1440 × 1000 showed the intended layout and locally hosted Fraunces / DM Sans computed font families.
- After the Weave pass, repeated mobile personalization/keyboard progression, adhesion recovery, restart-checkpoint reload, rejoining the journey and named completion. Both final checkboxes still gated completion. Name, gift purpose, note and one restart appeared together.
- Inspected final desktop entry, cleaning recovery, completion, mobile entry and mobile recovery captures. Narrow recovery document width matched the 390 px viewport. Original SVG artwork rendered without missing assets.
- Rendered entry/completion text contrast spot checks found and corrected muted text below 4.5:1. Main/icon/help/back targets meet the documented sizes; radio/checkbox labels provide larger clickable rows. This is not an exhaustive WCAG audit.
- Native Enter activation and Escape/focus-return were exercised. Reduced-motion handling was inspected in CSS; no physical touchscreen, system preference toggle or screen-reader test is claimed.
- Sampled final error/warning logs contained no app-origin error. The user's browser extensions produced unrelated messages and can add controls to text fields; extensions were not disabled.

Final screenshots: [desktop entry](docs/design/revisions/benchmate-20261013-weave-r1/implementation/after/desktop-entry.jpg), [mobile entry](docs/evidence/mobile-final.jpg), [mobile recovery](docs/evidence/mobile-recovery-final.jpg), [desktop recovery](docs/evidence/recovery-final.jpg), [completion](docs/evidence/completion-final.jpg). Earlier captures in [docs/evidence](docs/evidence) document the functional pass before visual refinement.

This is software/demo verification only. No real printing, physical touch safety, printer connection, firmware-specific operation, mobile hardware touch session, cross-browser/screen-reader certification or user research has been performed.

## Scope boundaries

No marketplace, activation paywall, open-ended chat, account, manufacturer dashboard, telemetry, camera, sensing, machine control, G-code, validated model/profile, remote sync or paid runtime AI. No sponsorship, content reuse license or manufacturer technical sign-off is claimed. A pilot would need reviewed assets, physical testing, source-maintenance ownership and research with novice owners and a manufacturer buyer.
