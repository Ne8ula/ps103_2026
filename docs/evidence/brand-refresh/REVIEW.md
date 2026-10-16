# BenchMate Brand Refresh

16 October 2026 · Actual React/Vite/Three.js browser captures

[Open the showcase gallery](review.html) · [Desktop](showcase-home-1440.png) · [Phone](showcase-home-393.png)

The supplied [BenchMate brand guide](../../../BenchMate_Brand_Guide.html) is the current appearance authority. The existing R9 journey, state model, saved data, equipment guidance and interactions remain intact.

## Implemented

- Space Grotesk: bold headings; medium subtitles, section headings and controls.
- Space Mono: instructions, descriptions, inputs and reading text, with regular and bold font files.
- Silkscreen: short phase labels, scene labels and desktop accents. It is not used for paragraphs.
- Electric Blue `#3155D9`, Acid Lime `#D6E879`, Cloud `#F3F4F8`, White `#FFFFFF`, Graphite `#292733`, plus the guide's supporting shades. Blue primary actions, navigation and focus; lime accents; neutral reading surfaces.
- Exact supplied vector wordmark and Soft Joint logo in the header and desktop presentation; Soft Joint favicon. Original mark proportions and clear space are retained.
- Cloud-blue 3D materials, matching fallback vectors and synthetic first-layer filament; the illustrative gold PEI plate keeps its material identity.
- Font dependencies replaced with local guide assets and their OFL licenses. [Asset provenance](../../../public/brand/provenance.json) records source paths and SHA-256 hashes. All four font files and the wordmark match the guide's embedded bytes.

## Verification

- `npm test`: 17 state/persistence tests pass.
- `npm run build`: passes. The existing lazy Three.js chunk warning remains, approximately 131 KB gzip.
- `node scripts/verify-r9.mjs`: full main journey, recovery, file selection, photo continuity, synthetic camera, pause/reload, records, downloads, profile, community and private share preview pass; no application exceptions. See [workflow results](verification.json).
- `npm run test:brand`: 320 × 740, 393 × 852, 430 × 932 and 1440 × 1000; all three font families and both Space Mono weights load, logo/wordmark images resolve, primary blue matches, no document overflow, narrow guidance text is not horizontally clipped. See [brand results](brand-verification.json).
- Visual review covers all eight chapter boards, narrow guidance and help, fresh home views and desktop presentation. The main content remains scrollable above the action dock.

The gallery contains eight boards, 25 numbered journey screens, responsive showcase images, and additional recovery/accessibility checks. These are actual browser renders, not generated mockups. Showcase home images use a fresh isolated profile; additional responsive home checks include a paused project to exercise continuity.

## Screenshot Cleanup

Superseded app captures from `docs/evidence/`, `docs/evidence/r9-implementation/` and the R1–R4 `implementation/` folders were deleted after the replacement captures passed. [Cleanup manifest](removed-captures.json) lists their paths and hashes. Historical generated design references, the PANDA reference archive, supplied branding assets and brand-guide development evidence are retained.

Old gallery entry points redirect here. Historical test reports describe their original runs; they do not validate this refresh. Current results are linked above.

## Limits

Browser prototype, tested in headless Microsoft Edge with software WebGL. Camera checks use a synthetic stream. No physical camera, iPhone/Safari, screen reader, printer or print validation was performed. No remote publishing, account service, vision diagnosis or printer integration was added.
