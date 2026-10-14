# Benchmate

A runnable **iPhone app mockup** centered on an original 3D cat, satin celadon material, and matte glass task surfaces. On desktop it appears inside a phone frame; on a narrow screen the app fills the viewport. The connected **Prepare → At the printer → Print → Finish** journey retains contextual help, adhesion recovery and local continuity from the PANDA adaptation.

Independent prototype. Bambu Lab is the equipment manufacturer, not a sponsor or partner. The manufacturer-funded business model is a product hypothesis; no commercial relationship is implied.

![Benchmate iPhone mockup with live 3D cat](docs/design/revisions/benchmate-20261013-ios-r2/implementation/after/desktop-phone.jpg)

This is an interactive React browser mockup, not a compiled SwiftUI app or an iOS Simulator recording. The cat and task objects are real Three.js geometry rendered locally. Their visual materials do not predict the appearance or physical properties of a real print.

## Run

Use Node 22.12+ or Node 24 LTS and npm. Verified here with Node 24.14.0 / npm 11.9.0 on Windows.

```powershell
cd C:\Users\alexx\Documents\ClaudeAgent\ps103_2026
npm ci
npm run dev -- --port 5173 --strictPort
```

Open **http://127.0.0.1:5173/**. No credentials, environment variables, paid AI service or printer are required. Install needs registry access; afterward runtime fonts, illustrations and application code are local. Official-source links open external sites only when clicked.

```powershell
npm test
npm run build
npm run preview -- --port 4173 --strictPort
```

The build goes to `dist/`; production preview uses **http://127.0.0.1:4173/**. Local project state belongs to the origin, so changing the port starts a separate browser-local record. This is a local demo, not a published deployment or installable offline PWA.

## Try the journey

1. Choose **Make this project**, name the cat (for example, Miso), and choose desk or gift.
2. Confirm the example Studio setup, then inspect the plate and existing external spool.
3. Enter the explicitly labeled print demonstration. Use **Help** in the bottom dock or **Sources** in the task without leaving the checkpoint. Help and setup open as bottom sheets.
4. For the happy path, accept the illustrated first layer, continue to the demo finish, review cooling/removal, and check both object/workspace items.
5. See the name and purpose on completion, add a note, and **Save project record** to download a real `.txt` file.

To try recovery, select **Something looks wrong** at the first layer. Report lifting/loose material, review ending the failed attempt and cleaning, then return through Studio and the preparation checks. The restart count reaches the completion record. The **I’m not sure / something else** branch keeps an unresolved issue and offers a downloadable support handoff; nothing is sent automatically.

Use **Save & pause guide**, close/reload, and resume at the same checkpoint with the open issue preserved. Saving or pausing never controls the printer. There is no cross-device synchronization. The **Perspective / Front / Detail** controls select actual 3D camera views, without autoplay or continuous rendering.

## Reset and presenter controls

Open the **Demo** menu in the header. Choose the connected-first-layer or lifting-edge example, or **Reset this demo** and confirm **Reset project**. Reset clears only Benchmate’s local project, including the note and unresolved issue. Storage key: `benchmate.project.v1`. Browser site-data removal also clears it. Export a record first if you want to keep it.

## Implemented versus simulated

| Implemented | Deliberately illustrative / unavailable |
|---|---|
| Connected task journey and explicit completion ledger | Cat meshes are original visualization geometry, not a print-ready model |
| Name/purpose/note and versioned browser persistence | No `.3mf`, STL, print profile or machine-ready G-code |
| Source-linked scripted help, max two suggestions | No live chatbot, diagnosis, sensing or temperature |
| Bounded recovery, unknown-issue handoff and real text download | No printer connection; no slicing, file sending, starting or stopping |
| Phone-first shell, persistent action dock, native dialogs styled as bottom sheets, keyboard/focus and reduced-motion CSS | No physical print validation or validated success-rate claim |
| Three.js 3D cat, plate, spool and schematic printer; custom layer shader, physical material, studio lighting and shadows | No native iOS build, continuous orbit gesture, physically calibrated material or CAD editor |
| Five completed Weave runs, each specifically approved at 5 credits; r2 drives the app, r3/r4 remain design studies | No native Figma file/frame sync or runtime Weave integration |

The selected example is X1 Carbon / assumed 0.4 mm nozzle / Bambu PLA Basic external spool / gold Textured PEI X1 256 × 256 mm plate. Initial onboarding is complete and material is already loaded. Real use of the chosen Studio Wi-Fi route needs the official network plug-in and configured connection. The authored project template needs a reviewed model, profile and physical testing before real deployment.

## Project structure

```text
src/main.jsx                   App entry
src/MobileApp.jsx              iPhone screens, action dock and recovery
src/mobile.css                 Matte glass, phone frame and responsive layout
src/components/ProductScene.jsx  Lazy 3D loading, view presets and fallback
src/scene/createScene.js       Original meshes, physical material and custom shaders
src/data/equipment.js          Equipment configuration and source references
src/data/project.js            Authored project steps and scripted help
src/state.js                   Reducer, persistence validation, record export
src/components/               Sheet content, native dialog, demo controls, SVG fallback
src/styles.css                 Retained old desktop styles; no longer imported
src/refinement.css             Retained first-pass styles; no longer imported
tests/state.test.js            Seven state and persistence tests
reference/panda/               All 22 original archive files, unchanged
docs/source-register.md        Official pages, dates, applicability and limits
docs/design-board.html         Standalone visual review gallery
docs/design/revisions/         Weave prompt, output, provenance and comparison
docs/evidence/                 Screenshots, document snapshots, archive integrity
public/licenses/              Font and Three.js license notices
```

## Documentation and sources

- [Current Visual Review: Complete Workflow](docs/design/revisions/benchmate-20261014-workflow-r9/review.html) — 24 screens across eight boards, from Home and Bambu Projects through preparation, photo help, recovery, completion, Collection, Community and Profile. Title Case headers and period-free titles/subtitles. Static purple/citron concepts; app code is unchanged.
- [Previous purple/citron, Community and Profile review](docs/design/revisions/benchmate-20261014-social-r8/review.html) — four screens used as visual references for r9.
- [Earlier Home, Bambu projects, detail and Collection review](docs/design/revisions/benchmate-20261014-collection-r7/review.html) — four screens in pearl/graphite/violet, with stronger glass and character-matrix artwork. Static concepts; no application code changed.
- [Latest fresh direction: warm glass and matrix inspection](docs/design/revisions/benchmate-20261014-dither-r6/review.html) — only the latest two images/video used; previous visual references excluded. One new generated board; no application code changes.
- [Planning, PANDA matrix and verification](planning.md)
- [Design, actual Weave process and artifacts](design.md)
- [Visual review gallery](docs/design-board.html) — open directly or at `/docs/design-board.html` on the development server; documentation is not part of the production app build.
- [Current iPhone Weave reference and review](docs/design/revisions/benchmate-20261013-ios-r2/REVIEW.md), including all six reference roles
- [Latest interface review: smaller type, expandable detail and photo help](docs/design/revisions/benchmate-20261014-interface-r5/review.html). Two built-in image-generation boards are inspected; review remains open before application edits. The user selected [Pocket Quest from the earlier concepts](docs/design/revisions/benchmate-20261013-focus-r4/review.html), then refined its typography and requested these new states. [Opal-frost material research](docs/design/revisions/benchmate-20261013-opal-r3/REVIEW.md) is also retained.
- [Full source register](docs/source-register.md), including official X1, Studio, plate-cleaning and adhesion pages read on 13 October 2026.
- Product direction: [Benchmate Value Creation Analysis](https://docs.google.com/document/d/1MlFYdx6BnDHWLtPpfbylJ8nDJC2myUmwPBikmnAP3Q8) and [Product Vision and Feasibility](https://docs.google.com/document/d/1io-KpTpRBQfNR-hlaYrN1Pf2lz3BsYL_QEGLxlGWVxU/edit).

Both supplied documents were read as full text. PANDA code was inspected; the hosted flow was not independently exercised. No accompanying research files or actual cat model existed in the ZIP. Reported interview excerpts in the business document are secondary evidence, not a new user study.

## Verification and limits

`npm test`: **7 passed**. `npm run build`: **passed**. The redesigned app was checked in Chrome at **393 × 852**, **320 × 740**, and **1440 × 1000**. Checks covered real 3D rendering/camera presets, completion, contextual help and focus return, Back without fabricated completion, pause/reload, both issue branches, restart checkpoint, reset and a 700-byte downloaded record containing Miso, the gift choice, one restart and the note. No horizontal overflow remained; sampled visible buttons were at least 44 × 44 px. A checkbox focus/layout shift found during testing was fixed and rechecked.

The 3D renderer is a lazy chunk of about 130 KB gzip. Vite reports its standard 500 KB uncompressed chunk-size warning; the build succeeds. Rendering is on demand with pixel ratio capped at 1.75, no external model/texture fetch and explicit GPU-resource disposal. A labeled SVG fallback preserves the guide if WebGL fails; forced GPU-context-loss testing was not performed. Vite was updated within version 7 to 7.3.7 after a concrete dependency advisory; the resulting npm audit reported zero vulnerabilities.

No physical printer, iPhone/Safari, mobile touchscreen, virtual keyboard, screen reader or cross-browser testing was performed. CSS safe-area and dynamic-viewport handling are implemented; physical iOS behavior remains unverified. Browser-local data can be lost if storage is blocked or cleared; the app warns if saving fails. No synchronization, support submission, manufacturer integration or remote telemetry is implemented. Third-party browser extensions can appear in screenshots and logs; they are not part of Benchmate.
