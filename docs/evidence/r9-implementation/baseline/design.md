# Benchmate — iPhone design and implementation

**Implemented 13 October 2026; owner design acceptance pending.** [Open the running demo](http://127.0.0.1:5173/) or the [visual gallery](docs/design-board.html). The deliverable is an interactive browser mockup of an iPhone app. It is not a compiled SwiftUI application or proof of physical iOS behavior.

The [current r9 workflow review](docs/design/revisions/benchmate-20261014-workflow-r9/review.html) contains 24 screens across eight boards, covering discovery, preparation, printing, photo help, recovery, completion, Collection, Community, Profile and pause/resume. Headers and subtitles use Title Case without periods. The r8 purple/citron boards supplied the glass, cat and component-level matrix direction. Eight initial generations and seven targeted corrections were inspected; exact model version and cost are unexposed. **The user requested visual review before implementation, so application code remains unchanged.** These are static concepts, not implemented navigation, photo analysis, collections, community or accounts. The implementation described below remains celadon r2. [R8 is retained as design history](docs/design/revisions/benchmate-20261014-social-r8/review.html).

## Direction and the six references

Earlier [r6 inspection concepts](docs/design/revisions/benchmate-20261014-dither-r6/review.html) remain in the archive; their ivory/orange/serif direction was replaced by r7 at the user's request. The description below documents the existing r2 implementation.

The product occupies the center of the screen: an original, live 3D cat in satin celadon, lit like a small studio object. A quiet ice-gray field, cloudy green glass and one charcoal action keep attention on the object and the next physical task. The user's mobile valve reference supplied the principal proportions; the final green glass study supplied the principal material direction.

| User reference | Used for | Excluded |
|---|---|---|
| 1. Lavender 3D office | Spatial clarity and a prominent three-dimensional object | Room scene, camera feeds, sidebar and device dashboard |
| 2. Gray/yellow valve desktop | Technical precision, selective amber and object detail | Telemetry, dashboard grid and literal valve imagery |
| 3. Two mobile valve screens | Oversized object, sparse headline, lower contextual sheet | Dense controls and issue numbers unrelated to the project |
| 4. Exploded keyboard switch | Studio lighting, contrasting materials and quiet matte frame | Branding, exploded cat anatomy and unrelated hardware |
| 5. Cobalt/orange fluted glass | Narrow fluted edges and layered facets | Loud background blobs, subtitle and saturated palette |
| 6. Matte green tile study | Milky boundaries, cloudy celadon, restrained grain | A tiled card dashboard |

All six attachments were inspected in the conversation and individually described in the Weave prompt. They were not uploaded as image inputs. The result is one composition, not a collage of the references.

The glass is implemented with restrained backdrop blur, dense translucent fills, edge highlights, decorative fluting and static fractal-noise grain. It does not simulate physically accurate optical refraction. Text sits on relatively opaque surfaces; strong green coloration belongs primarily to the cat and small action accent.

## Actual Figma Weave workflow

The user-installed guide is `C:/Users/alexx/Documents/ClaudeAgent/GenUI_Agent/docs/design/FIGMA_WEAVE.md`. Its direct-model route is appropriate for this bounded study even though the connected workspace has no published graph tools. Existing configuration and credentials were preserved.

For this revision, the reference was generated, downloaded, visually inspected, and recorded in a review packet **before frontend edits**. The previous implementation was saved as source snapshots and hashes.

1. Used the already approved single iPhone-focused run. Incorporated the six newly supplied references, requoted at the same **5 credits**, and submitted once. No image uploads or automatic reruns.
2. Nano Banana 2.1, model record `bebebed5-50c1-4701-98b3-86929db21585`, provider `fal-ai/nano-banana-2/edit`; 2K, 16:9, PNG, High thinking, seed 104, web search off.
3. Prediction `1e3a139b-a00b-4574-ba21-e7a4114ed914` completed, reporting 5 credits and a 2752 × 1536 PNG.
4. Selected the iPhone proportions, celadon object, dense lower glass sheet, charcoal/lime action and sparse hierarchy. Rejected inconsistent cat geometry, unsupported saved-settings claims, generic black plate, weak text contrast and missing help controls.
5. Rebuilt the interface in React/CSS and created actual reusable Three.js meshes. Generated wording and equipment illustrations are not technical authority. Camera changes are discrete presets; there is no new animated choreography or video run.

Current artifacts:

- [Review and before/after evidence](docs/design/revisions/benchmate-20261013-ios-r2/REVIEW.md)
- [Six-reference brief](docs/design/revisions/benchmate-20261013-ios-r2/BRIEF.md), [exact prompt](docs/design/revisions/benchmate-20261013-ios-r2/prompt.json), [provenance](docs/design/revisions/benchmate-20261013-ios-r2/provenance.json)
- [Labeled candidate sheet](docs/design/revisions/benchmate-20261013-ios-r2/references/contact-sheet.png)
- [Actual provider output](https://media.weavy.ai/image/upload/v1791940743/uploads/RjA4KfH9v0eVz56zC2LruMUpYXG2/gzkrpxmbgvokgotp7duj.png)

The [earlier desktop pass](docs/design/revisions/benchmate-20261013-weave-r1/REVIEW.md) is retained as history. Its initial implementation preceded discovery of the installed guide; that deviation remains documented, and is not retroactively described as compliant. R1, r2 and the material-only r3 each used one approved 5-credit run; r4 added two specifically approved 5-credit concepts. Five completed runs total 25 credits, including 10 for the current comparison. No reruns were submitted. There is no native Figma frame synchronization or editable Figma file. The app has no runtime Weave dependency.

## Tokens and layout

| Role | Implemented value / rule |
|---|---|
| Base / ink | `#edf0ed` / `#252b28` |
| Primary action | Charcoal `#2e3630`, pale text, lime end-cap `#dbf5a0` |
| Secondary text | Base `#5c685f`, with contextual dark green variations |
| Cat material | Celadon `#739e83`, roughness 0.31, clearcoat 0.45, subtle iridescence |
| Glass | Dense pale-green translucent fills, 14–30 px backdrop blur, low-opacity grain |
| Recovery | Warm translucent field and amber `#f5d69b` action end-cap; explicit issue text |
| Typography | System Apple sans where available, locally hosted DM Sans fallback; 35 px principal heading, 15 px task body, 16 px form fields |
| Shape | 14–18 px controls; 27–30 px lower sheets; rounded silhouette and fine surface highlights |
| Touch | Primary action at least 55 px tall; visible mobile buttons at least 44 × 44 px; full-row choice/check targets |
| Progress | Four thin phase segments, with the completion ledger on demand |

On desktop, a 413 px phone frame is centered within an editorial preview, with small outer captions. On mobile, the frame becomes the viewport and the decorative status bar disappears. The implementation uses `100dvh`, safe-area insets and a flex layout. The header and lower action dock stay available while the task area scrolls independently; the dock does not cover task content. At narrow or short sizes the object field becomes shallower. Long names wrap.

The entry scene is about 330 px tall at the main mobile size, with 245 px compact scenes on tasks. Contextual sheets align with the actual phone rectangle on desktop and the viewport on mobile. This was checked at 393 × 852, 320 × 740 and 1440 × 1000. Hardware keyboard/viewport behavior on iOS remains untested.

## 3D rendering and materials

`src/scene/createScene.js` creates an original cat from lathed forms, rounded meshes and curved tube geometry. The same identity appears throughout the journey. Gold plate, spool, schematic printer, first-layer paths and cleaning props direct attention to the current physical task. These are schematic visualization assets, not dimensionally accurate manufacturer models or validated printable geometry.

The cat uses Three.js `MeshPhysicalMaterial`, a studio environment, key/rim lighting, soft contact shadow and a custom shader patch for fine print-layer banding and surface grain. The layer texture is decorative and does not assert a slicing layer height. Perspective, Front and Detail select discrete cameras; there is no continuous orbit or autoplay. Physical material parameters follow the [Three.js material API](https://threejs.org/docs/pages/MeshPhysicalMaterial.html).

The renderer is lazy-loaded, renders only for scene/view/size changes, caps pixel ratio at 1.75 and disposes GPU resources on teardown. This follows [Three.js rendering-on-demand guidance](https://threejs.org/manual/pages/rendering-on-demand.html). Models, fonts and textures require no external runtime fetch. The build reports a standard chunk-size warning for the approximately 130 KB gzip renderer module; it is not a build failure. A labeled SVG fallback is implemented for unavailable WebGL, but forced context-loss testing was not performed.

## Components, states and continuity

| Element | Behavior |
|---|---|
| Product scene | Actual 3D, accessible description and three camera presets; demonstration/schematic labels where needed |
| Current task | One heading, one primary action and a concise instruction; relevant detail expands on demand |
| Bottom action dock | Main action, Help and four-phase rail; amber treatment while a reported issue remains open |
| Contextual help | At most two collapsed suggestions, keyed to the current task or recovery branch; scripted and source-linked |
| Equipment / sources | Native modal sheets with selected configuration, assumptions and official links |
| Recovery | Observation question → end failed job → cool/clean → review setup for a new attempt; issue stays open until explicit review |
| Unknown issue | Honest boundary and preview/download of contextual support handoff; no automatic submission |
| Save / pause | Pauses the guide, retains task and unresolved issue, and never claims to pause the printer |
| Completion | Chosen name, desk/gift purpose, restart history, optional note and a real text-record download |
| Demo menu | Explicit expected/lifting examples and confirmed local reset; no telemetry or timers |

Equipment facts live in `src/data/equipment.js`; authored tasks in `src/data/project.js`; user choices, completions and issue history in `src/state.js`. The presentation rewrite preserves the existing reducer and versioned storage. Visiting or returning to a checkpoint does not mark it complete. Only a name and destination are chosen before the journey; arbitrary settings, accounts, catalogs and mandatory conversation are absent.

## Accessibility, motion and language

Native buttons, labeled fields, focus outlines, heading focus, a skip link and native modal dialogs support keyboard use. Escape closes Help and returns focus to its opener. Two quality/workspace checks gate completion. Active camera buttons use `aria-pressed`; current progress uses `aria-current`. Words and icons accompany color cues.

Motion is limited to existing press feedback and instant disclosure/camera state changes. Reduced-motion CSS removes scaling; reduced-transparency CSS supplies more opaque surfaces. There is no continuous render loop, autoplay, staged sensing or animated camera. A focus-driven scene resize that interfered with checkbox activation was removed and rechecked.

Copy describes the action actually recorded: review, confirm, observe or download. The official app owns physical printer controls. Unknown temperature and diagnosis remain unknown. Three-dimensional assets are labeled as studies or schematics without adding rendering implementation details to the task instructions. Accessibility was spot-checked; no screen-reader or comprehensive contrast certification is claimed.

## PANDA adaptation and verification

PANDA supplied the connected four-phase arc, relevant-object attention, contextual help and first-layer recovery opportunity. XR panels became a stable mobile task layout; pins became focused object views; walking became a simple phase transition; the long rail became four compact phases. Headset interaction, faux sensing, decorative rooms and staff-arrival promises were removed. The failed-print branch distinguishes stopping a failed attempt from resuming a paused print, using the official sources in the [source register](docs/source-register.md).

Seven state tests pass. The production build passes. Actual Chrome checks covered rendering and camera views, keyboard action, Help/focus return, Back without fabricated completion, both recovery branches, pause/reload, restart, gated completion, reset and a downloaded personalized record. Representative [entry](docs/design/revisions/benchmate-20261013-ios-r2/implementation/after/entry-393.jpg), [recovery](docs/design/revisions/benchmate-20261013-ios-r2/implementation/after/recovery-393.jpg), [finish](docs/design/revisions/benchmate-20261013-ios-r2/implementation/after/completion-393.jpg) and [desktop preview](docs/design/revisions/benchmate-20261013-ios-r2/implementation/after/desktop-phone.jpg) captures show the implemented app. Full results and limitations are in [planning.md](planning.md).
