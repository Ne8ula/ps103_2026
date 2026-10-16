# iPhone material redesign — r2

> Capture update, 16 October 2026: superseded app screenshots were deleted at the user's request. This report describes the historical run. [View the current branded demo and new captures](../../../evidence/brand-refresh/review.html).

**Implemented and checked. Reference selected by agent; owner acceptance pending.** The three later peach/blue references are recorded separately in the [r3 proposal](../benchmate-20261013-opal-r3/BRIEF.md).

- [Labeled contact sheet](references/contact-sheet.png)
- [Actual selected Weave image](references/images/img-01-ios-material-board.png)
- [Exact prompt](prompt.json), [provenance](provenance.json), [six-reference brief](BRIEF.md)
- Video: none; discrete camera presets, no new temporal choreography.

## Before and after

| Before | Implemented r2 |
|---|---|
| Earlier mobile entry (historical capture removed) | iPhone entry (historical capture removed) |
| Previous document layout, captured in a 393 × 852 viewport as a full-page image | New viewport-height app, captured at 393 × 852; capture extent therefore differs |

Desktop phone preview (historical capture removed) · 3D material detail (historical capture removed) · First layer (historical capture removed) · Recovery (historical capture removed) · Completion (historical capture removed) · Help sheet (historical capture removed)

The actual generated board was viewed before UI edits. Selected: iPhone proportions, large celadon object, matte lower sheet, charcoal/lime action, sparse sans-serif hierarchy and compact phase rail. All six then-available references informed the prompt; the main material reference was the matte green tile study. Fine fluting is limited to decorative edges.

Rejected: generated technical claims, inconsistent cats across screens, a generic black plate, inadequate contrast and missing help controls. Equipment facts and the recovery logic remain separately sourced. A reusable live 3D cat was created in code; the generated bitmap is never used as the application screen. No physical print validation is implied.

## Implemented material and behavior

- Original procedural cat, plate, spool, schematic printer and recovery props.
- Satin physical material, custom fine-layer/grain shader, studio environment and soft contact shadow.
- Perspective, Front and Detail camera presets. Rendering on demand; no animation loop.
- Dense matte glass with pale edges, subtle fluting and grain; lower action dock and aligned native bottom sheets.
- Existing project state, explicit completion, help, recovery, local save/resume and downloads retained.

## Checks and limitations

Seven reducer/persistence tests and the production build passed. Actual Chrome checks covered 3D views, complete journey, both recovery branches, pause/reload, restart, help/focus return, Back without invented completion, checkbox gates, reset and the actual personalized text download. Mobile 393 × 852 and 320 × 740 and desktop 1440 × 1000 were checked. A focus-triggered layout shift affecting checkboxes and decorative horizontal overflow were fixed and rechecked.

Entry, detail, recovery, completion and desktop captures were inspected. The build has a nonblocking renderer chunk-size warning. Physical iOS/Safari, touchscreen, virtual keyboard, screen-reader and forced GPU-failure checks remain unperformed. The 3D geometry is a visualization, not a print-ready asset.

One approved run completed at 5 credits. No uploads or automatic reruns. Source snapshots and hashes precede the pass; final owned-file hashes accompany the provenance. Historical r1 remains separately retained. Full implementation verification is in [planning.md](../../../../planning.md).
