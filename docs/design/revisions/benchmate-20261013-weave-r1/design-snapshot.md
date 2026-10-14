# Benchmate — design and implementation

**Implemented visual demo, 13 October 2026.** Start with the [review gallery](../../../../docs/design-board.html), [actual Weave reference](../../../../docs/design/revisions/benchmate-20261013-weave-r1/references/images/img-01-benchmate-state-board.png), or [runnable local preview](http://127.0.0.1:5173/). Functional verification is recorded in [planning.md](../../../../planning.md). Owner design acceptance is pending; software checks do not imply product or physical-print validation.

## Actual Figma Weave process

The installed workflow was located at `C:/Users/alexx/Documents/ClaudeAgent/GenUI_Agent/docs/design/FIGMA_WEAVE.md` after the user directed the search to GenUI_Agent. It explicitly allows the official Figma MCP **direct-model route** for a one-off study. An empty `weave_list_tools` result means no published graph tools, not that direct generation is unavailable.

The initial implementation preceded locating that guide. That was a process deviation, not a Weave-backed initial design. The actual generated reference was then inspected, a provenance packet was saved before further UI edits, and it governed one bounded final visual refinement. No retroactive compliance is claimed.

1. Defined a static board covering entry, first-layer observation, adhesion recovery, personalized finish and a narrow mobile layout. Only synthetic design instructions were sent; no private documents, project files or images were uploaded.
2. `weave_find_model` resolved **Nano Banana 2.1**, model record `bebebed5-50c1-4701-98b3-86929db21585`, provider model `fal-ai/nano-banana-2/edit`.
3. Quoted one run at **5 Weave credits**. The user explicitly approved the quote in the structured confirmation. Submitted exactly once with the acknowledged cost; no automatic reruns or inherited allowance.
4. Settings: 2K, 16:9, PNG, High thinking, seed 103, web search off, no image inputs. Prediction `b36e46c3-bd90-4859-9311-d14b40099557` completed, reported cost 5, and returned a **2752 × 1536 PNG**.
5. Downloaded and viewed the actual output. Selected material, hierarchy, phase underline and amber recovery treatment; rebuilt everything as native React/CSS/SVG. The generated board's wording and schematic hardware were never equipment authority.
6. Applied and checked the final static pass: terracotta print lines, 8 px visual-stage corners, stronger text contrast, a cleaning-specific illustration and completion headed with the user's chosen name. No new choreography or motion study was needed for this static refinement.

Artifacts:

- [Review and matching before/after](../../../../docs/design/revisions/benchmate-20261013-weave-r1/REVIEW.md)
- [Exact prompt/settings](../../../../docs/design/revisions/benchmate-20261013-weave-r1/prompt.json), [provenance](../../../../docs/design/revisions/benchmate-20261013-weave-r1/provenance.json), [labeled candidate sheet](../../../../docs/design/revisions/benchmate-20261013-weave-r1/references/contact-sheet.png)
- [Original provider output](https://media.weavy.ai/image/upload/v1791939120/uploads/RjA4KfH9v0eVz56zC2LruMUpYXG2/w6z2byvhifiv36o5d2yx.png)

There is no native Figma file or editable frame link, graph execution, frame synchronization or exported Weave code. The deliverable is a retained bitmap reference plus the independently implemented application. Existing configuration and credentials were preserved. This app has no runtime Weave dependency.

## Direction: the object holds the story together

Warm paper, dark olive type and a terracotta cat create a small creative workspace. The original smiling cat gives the object an identity without introducing an assistant character or a chat conversation. Its print-line texture suggests additive manufacture without asserting printable geometry. Close-up plate, spool, first-layer and cleaning illustrations direct attention to the current task.

The large left-hand object field and right-hand action area remain spatially stable on desktop. Instructions change within that frame. Thin rules organize information; there is no card dashboard, faux camera feed, glass overlay or permanent checklist. The generated board's heavy presentation frame, texture, faceless cat and misspelled text were rejected.

## Tokens and layout

| Role | Implemented value / rule |
|---|---|
| Paper / ink | `#f6f4ee` / `#34392e` |
| Primary action | Forest `#485d3d`, warm-white text `#fffdf5` |
| Muted text | Base `#69705e`; contextual secondary text darkened in `src/refinement.css` |
| Rule / visual stage | `#dedfd3` / `#edece2` |
| Material | Terracotta gradients around `#d5916b`, fine horizontal print lines |
| Recovery | Warm field `#eee5d6`, amber inset rule `#b17d55`; words and icons also signal the issue |
| Display type | Locally hosted Fraunces Variable; approximately 35–56 px desktop headlines, 38–45 px mobile |
| Interface type | Locally hosted DM Sans Variable; 13–15 px task body, smaller metadata, comfortable line height |
| Shape | 8 px object-stage corners; 7–9 px controls/insets; round progress markers |
| Width / spacing | 1440 px maximum shell; 64 px desktop gutters and column gap; 24 px or 17 px mobile gutters |
| Control targets | Primary action at least 54 px tall; icon buttons at least 44 × 44; help/back at least 44 px; check/radio labels are full-row targets |

At widths above 780 px, the object uses about 55% of the two-column workspace. Under 1120 px, gutters and gap tighten. At 780 px and below, the illustration stacks above the task, secondary header copy disappears and phase labels remain compact. Non-entry illustrations use a shallower 1.55 aspect ratio to limit scrolling beside a printer. No fixed bottom panel covers instructions. At 390 px and below, typography and gutters tighten further; content remains in document flow and long names wrap.

## Components and states

| Element | Behavior |
|---|---|
| Four-phase progress | Prepare → At the printer → Print → Finish. Current phase is underlined and identified with `aria-current`; completed markers derive from explicit checkpoints. Detail ledger opens on demand. |
| Task panel | One main action; one short instruction and explanation; details only for the current physical object. Back never invents completion. |
| Focus illustration | Original SVGs with accessible descriptions. Local “illustration” or “demonstration” labels distinguish examples from observation. |
| Contextual help | At most two initially collapsed questions, keyed to current task or recovery state. Scripted and source-linked, with project name/context retained. |
| Sources / setup | On-demand native dialog with current official links, selected equipment and applicability limits. |
| Recovery | One observation question → end failed attempt → cool/clean → review new setup. Amber treatment persists while issue is open. Restart differs explicitly from machine resume. |
| Unknown issue | Keeps the issue open; previews and downloads a contextual handoff. Opening official support does not submit data. |
| Guide pause | Dedicated saved-place view. Text explicitly states that the machine has not been paused. Resume preserves both checkpoint and unresolved issue. |
| Completion | Name and desk/gift purpose, restart summary, one optional note and one main action to download the text record. |
| Demo menu | Persistent discreet indicator; expected/lifting examples and a confirmed local reset. No accelerated clock or simulated temperature feed. |

## Continuity and choice reduction

The three product layers have separate modules: equipment and citations in `src/data/equipment.js`; authored project content in `src/data/project.js`; personal choices, completions, issue and history in `src/state.js`. A versioned local record saves after state changes. No account, catalog, device pairing, arbitrary settings or mandatory chat is introduced.

Only name and purpose are chosen before the journey. A single documented Wi-Fi route carries the Studio handoff; the SD alternative stays in help. Existing matching filament stays loaded. A single first-layer observation opens the bounded recovery branch; unfamiliar issues get an honest escalation boundary. The user never re-enters the whole project to ask for help or resume.

## Accessibility, motion and copy

Native buttons, labeled inputs, a skip link, logical headings, visible focus outlines and native modal dialogs provide keyboard operation. A checkpoint change focuses its heading. Dialog dismissal returns focus to the opener. Checkboxes gate the final action and explanatory text describes the disabled state. Color is supported by words, numbers, checks and icons. Text contrast was spot-checked on rendered entry/completion; muted text failures were corrected. This is not an exhaustive accessibility certification.

Motion is limited to 160 ms color/press feedback and disclosure indicators. No autoplay, countdown, staged sensing or decorative animation. `prefers-reduced-motion: reduce` removes transitions/animations and press scaling. Reduced-motion rules were inspected in code; the preference was not toggled on physical mobile hardware.

Copy uses plain actions and names the external owner of physical controls. “Review,” “check” and “demonstration” describe what a click actually records. Unknown temperature and diagnosis stay unknown. A source-linked explanation defines slicing, build plate and first layer when requested. Completion celebrates the demo journey without certifying a physical object.

## Departures from PANDA

PANDA supplied the end-to-end arc, contextual questions, focused equipment attention and first-layer recovery opportunity. Spatial pins became annotations; floating XR panels became a stable workspace; walking became “At the printer”; long rails became four phases and an on-demand ledger. Headset pairing, pinch/gaze interactions, decorative rooms, simulated sensing and staff-arrival promises were removed.

The failed-print sequence was reauthored from current official guidance: stop is distinct from pause; cleaning requires an ended job and cool hardware; a fresh attempt revisits setup. Hardcoded time/temperature claims and the missing `cat_figure.3mf` were not reused. Original PANDA files remain intact under `reference/panda/`.

## Final evidence and limits

[Desktop entry](../../../../docs/design/revisions/benchmate-20261013-weave-r1/implementation/after/desktop-entry.jpg), [mobile entry](../../../../docs/evidence/mobile-final.jpg), [mobile recovery](../../../../docs/evidence/mobile-recovery-final.jpg), [desktop recovery](../../../../docs/evidence/recovery-final.jpg), [named completion](../../../../docs/evidence/completion-final.jpg).

Chrome checks covered the connected journey, recovery, persistence, help, keyboard activation, focus restoration, disabled completion, reset and actual text download. Desktop and 390 px layouts were inspected. No app-origin console error appeared in the sampled log; unrelated extension messages were present. Real touch hardware, assistive technology, other browsers, printer operation and physical project validation remain untested.

