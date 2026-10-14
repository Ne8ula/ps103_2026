# Smaller type, real app controls, and photo help

**Superseded for visual direction:** the user rejected the blue and condensed type and requested a fresh design. See [r6 warm glass and matrix inspection](../benchmate-20261014-dither-r6/review.html). These two earlier boards were inspected but never implemented; the running app still uses r2.

- [Open the review gallery](review.html)
- [Task and expanded guidance](references/images/img-01-expandable-guidance.png)
- [Photo capture, processing and possible finding](references/images/img-02-photo-assistance.png)
- [Brief](BRIEF.md) · [Task prompt](prompt-01-details.txt) · [Photo prompt](prompt-02-photo-help.txt) · [Provenance](provenance.json)

## What to carry forward

The new Nextly and Memories references guide the interface structure: compact navigation, translucent controls, layered matte cards, readable dark type, and color diffused beneath the glass. The previous nine references remain supporting material and 3D guidance. Pocket Quest contributes focused progression and one main action.

The task board shows a compact project/cat header, a modest left-aligned task heading, and optional detail in the current screen. The intended typography targets are 23–25px task headings, 15–16px body, 16px controls and 12px metadata at roughly 393px width. These are targets, not measured guarantees from raster generation. Actual implementation must support text scaling and retain adequate touch targets.

The photo board shows three proposed states:

1. **Capture:** frame the visible problem, keep the project context and provide one shutter action.
2. **Process:** retain the submitted photo, show received/reviewing status and allow cancellation. This is a static loading-state mockup; no timing or animation has been implemented.
3. **Possible finding:** identify a visible region, describe uncertainty, offer an optional explanation and one next step. A photo cannot confirm the physical cause or machine safety.

## Corrections before implementation

- Use the existing four phases, Prepare / At the printer / Print / Finish. The first board's generated labels and progress must not replace the authored state model. In particular, do not introduce a mandatory filament reload.
- Remove the first board's extra Demo play control. Use a quiet label for demo status; put presenter controls behind the existing menu.
- Keep the same original 3D cat identity and rebuild the materials in the live scene. The generated boards are references, not screenshots to place over working controls.
- Preserve strong ink/action contrast on dense enough glass surfaces. Contrast must be checked on actual components; a generated bitmap is not an accessibility test.
- Camera zoom controls are illustrative. Implement only capabilities that exist, or omit them. Do not add competing camera options to the initial photo task.
- Retain cautious result wording and the existing bounded recovery sequence. “End the job before cleaning” in the board is a summary, not a full procedure: end the failed attempt, cool, clean, review setup, then start a new attempt.
- The printer/plate pictures are synthetic and not mechanically verified. No actual user photo, live camera, vision backend or automatic diagnosis was used.

## Execution and verification

Two successful built-in image-generation calls, not Weave runs. This route followed the user's request to change generator after two Weave GPT-model lookups returned INVALID_ARGUMENT. The built-in tool does not expose its exact model version or monetary cost; neither a model ranking nor a specific GPT version is claimed. No additional Weave credits were spent. The previous five completed Weave runs remain 25 credits total.

Both originals were preserved under the tool's generated-images folder and copied into this project. Board 1 is 1312 × 1199; board 2 is 1474 × 1067. Both actual outputs were visually inspected. Exact prompts, dimensions and SHA-256 hashes are recorded in provenance.

[Source-integrity verification](source-integrity.json) confirms the six app/rendering/state files match the r4 baseline. No application code changed, so app tests/build were not repeated. Owner review of these revised boards remains open, as requested before further implementation.
