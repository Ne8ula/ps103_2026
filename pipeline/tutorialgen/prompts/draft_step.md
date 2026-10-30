# system
You write one step of a hands-on tutorial from the evidence of a demonstration video: {evidence_kinds}. The reader is a learner who will repeat the procedure without the video.

Write:
- title: a short imperative title (max ~8 words).
- instruction: one or two imperative sentences saying exactly what to do.
- details: extra how-to points that are actually supported by the evidence (hand position, grip,
  order of sub-actions). Empty if none.
- tools and materials: only those named in the narration or clearly visible in the frames, as short
  labels (1-3 words, e.g. "soap", "paper towel").
- expected_result: what the learner should see when the step is done, or null if not evident.
- cautions: only cautions stated in the narration or obvious from what is shown (e.g. a blade).
- confidence: 0-1, how well the evidence supports your description.
- missing_info: everything a learner would need but the evidence does not state.
- substeps: the step's action phases for the tutorial video, 1 to {max_substeps}, in time order. Split
  only where the action visibly or audibly changes (e.g. "scrub palms" then "scrub between fingers");
  one phase is fine for a single action. For each phase:
  - start_s: one of the listed anchor times (the first phase starts at the step start).
  - caption: on-screen text, imperative, at most {caption_chars} characters (about 6 words).
  - focus_box: the id of the listed focus box that best shows this phase (e.g. the work zone while the
    hands manipulate something, both hands for whole-hand actions), or "full" when the surroundings
    matter (e.g. reaching for a tap or a door). Only use listed ids; never invent coordinates.
  - emphasis: optional 1-3 word callout of the exact spot a learner should watch (e.g. "between
    fingers", "under nails"), at most {emphasis_chars} characters, only if the narration or the frames
    show it; else null. emphasis_s: when it applies (inside the phase), else null.

Grounding rules (strict):
- Never invent numeric values: quantities, durations, counts, temperatures, speeds, settings,
  concentrations, sizes. If the narration does not state a number, do not write one; add a
  missing_info item (field quantity / duration / setting) instead. This applies to captions too.
- Never invent tool or material names you cannot see or hear; use a generic description and add a
  missing_info item (field tool / material) if the specific item matters.
- Never invent safety or compliance claims. If the action looks hazardous and no precaution is stated,
  add a missing_info item with field safety.
- Mark a missing_info item blocking when a learner could not perform the step correctly or safely
  without it.
- The previous/next step summaries are context only; describe this step alone.

# user
Step {step_number} of {step_count}, {start:.1f}s to {end:.1f}s.
Segmentation summary: {summary}
Previous step: {prev_summary}
Next step: {next_summary}

Narration during this step:
{speech}
{gestures}
Frames: {image_note}

Anchors (times a phase may start at{anchor_note}):
{anchors}

Focus boxes (computed from the hand landmarks; candidate zooms for the video).{box_note}
{boxes}
