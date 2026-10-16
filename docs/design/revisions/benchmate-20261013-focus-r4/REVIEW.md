# Focused progression — choose the visual direction

> Capture update, 16 October 2026: superseded app screenshots were deleted at the user's request. This report describes the historical run. [View the current branded demo and new captures](../../../evidence/brand-refresh/review.html).

**Both actual candidates generated and inspected. User selected B / Pocket Quest. No app code changed.** Later feedback requested smaller type, expandable descriptions and photo help using two new glass UI references. See the [refined r5 interface review](../benchmate-20261014-interface-r5/review.html); its visual review remains open before implementation.

- [Comparison contact sheet](references/contact-sheet.png)
- [A — Guided studio](references/images/img-01-guided-studio.png)
- [B — Pocket quest](references/images/img-02-pocket-quest.png)
- [Open the comparison gallery](review.html)
- [Brief](BRIEF.md) · [Prompt A](prompt-a.json) · [Prompt B](prompt-b.json) · [Provenance](provenance.json)
- Static concepts only. No video, new animation or implemented transition.

## What the two boards demonstrate

Both reduce the screen to a task/object, a clear instruction and one dominant action. Small back/help controls remain available; camera presets, equipment cards, persistent source/save rows and the detailed progress menu leave the main decision path. Dark type and saturated teal actions create a stronger hierarchy than the current pale-green app.

| | A — Guided studio | B — Pocket quest |
|---|---|---|
| Character | Calm, precise studio | More playful, encouraging progression |
| Hierarchy | Heading and action grouped in a low frosted sheet | Bolder centered task, strong separated action |
| Progress / reward | Thin milestone path; large faceted seal | Compact dots; smaller earned check token |
| Material | Soft frosted lower surface | More dimensional plinth and icy/peach edges |
| Main refinement | Reduce competing chapter heading and oversized reward | Correct progress dots and soften excess rim/button gloss |

**User selection: B.** The focused progression and action hierarchy were selected, then refined by feedback that the text was too large and the composition felt like an advertisement. The r5 boards address that feedback; the r4 output is not an approved pixel-exact implementation target.

## Corrections required whichever is selected

- Generated progress indicators are not state logic. They must derive from explicit reviewed checkpoints; the completion state must visibly be complete.
- The floating/exploded plate in B is an attractive graphic but contradicts the instruction to check a seated plate. Rebuild the scene as a clear schematic, with the plate visibly seated where that matters.
- A reward acknowledges a user's recorded check. It does not certify machine readiness, cooling, safety or a successful physical print.
- Preserve stop → cool/clean → reviewed setup → new attempt. Generated recovery screens are illustrative, not a complete or independent procedure.
- Rewrite completion wording to describe the guided demo and user's saved project. Do not carry over “ready to be born,” inferred notes or unsupported physical-success claims.
- Keep the original cat identity consistent and rebuild the opal material in live 3D. The reference images are never used as flat application screens.
- Glass texture and color support readability. Reduce glossy button/rim effects where they compete with the main task.

## Proposed workflow interpretation

Five concise chapters can group setup, printer readiness, start/observe, remove/check and a personal finish. Each chapter can contain necessary microsteps; this does not mean five clicks or omitted hardware checks. The visible screen shows only the current microstep. Personalization is deferred or optional so it does not block starting. Contextual help collects sources, save and secondary details.

Gamification uses meaningful progress, a small earned mark and a personal finish. No streak pressure, points, penalties, fake telemetry or extra acknowledgement screens after every tap. Milestone feedback can share the next actionable screen.

## Actual generation and unchanged implementation

Nano Banana 2.1 through the official Figma Weave direct-model route. Each board: 2K, 16:9, PNG, High thinking, web search off, no image uploads. A seed 106, B seed 107. Both returned 2752 × 1536 images. Each cost 5 credits; **10 credits total**, explicitly approved together as two specified runs. Exactly two submissions, no automatic reruns.

All nine user references were inspected inline and given individual use/avoid roles in both prompts. Both generated files were downloaded and visually inspected. A source-hash baseline is retained; [integrity verification](source-integrity.json) confirms the renderer, presentation, state and task sources remain unchanged. Application changes are held pending the user's review request. Tests/build were not repeated because no application code changed.

Existing app captures: entry (historical capture removed), recovery (historical capture removed), completion (historical capture removed), all from the r2 Chrome pass at 393 × 852. They are before-state evidence, not implementations of these new concepts.
