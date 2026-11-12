# Learner Assistant (Design, Not Implemented)

Status: **designed 12 Nov 2026, not built.** Implementation waits until the current data run and push are done.

The tutorial pipeline already produces everything a learner-facing assistant needs: steps with time ranges and sub-steps, SOP passages with an index, the transcript with timestamps, the expert's answers, and hand-pose data. Today that material is only used while generating the tutorial. This assistant puts it in front of the learner in two ways:

1. **On request (Q&A):** the learner asks a question at any point and gets a grounded answer.
2. **Proactive (checks):** the tutorial asks the learner questions at step boundaries, in three tunable categories.

Both follow the pipeline's existing rules: typed outputs, citations the code verifies, numbers that must appear in a cited source, and "I don't know" instead of a guess.

## 1. Learner Q&A

**Endpoint:** `POST /projects/{id}/ask` with `{question, step_id?, t?}` (the learner's current step and video time).

**Evidence index**, built once per project (`learner/index/`, rebuilt when its inputs change), reusing `tutorialgen/rag` (BM25 + embeddings, reciprocal-rank fusion, reranker):

| Source | Record id | From |
|---|---|---|
| Tutorial steps: title, instruction, details, cautions, sub-step captions | `step:s05` | `refine/steps.json` |
| SOP passages | `sop:d01:12` | `compliance/index/` |
| Compliance notes | `note:c-s05-1` | `compliance/compliance.json` |
| Transcript lines, with source time | `say:s05@171.2` | Whisper word timestamps (same lines as the subtitles) |
| Expert answers | `expert:a-q002-…` | `refine/steps.json` answer log |

The current step and its neighbours are always included, whatever the search returns.

**LLM call** (`learner_answer`, strict structured output):

- `answer`, `citations: [{source_id, quote}]`, `show_me: [{step_id, t}]`, `confidence`, `needs_expert`.
- Code validates every citation: the id must be one that was offered and the quote must appear in that record (`rag.text.quote_in_text`). Invalid citations are dropped.
- Number guard (`steps/guards.py`): a number in the answer that no cited record contains is removed and the answer is flagged.
- No valid citation and not `needs_expert`: the answer is replaced with "This tutorial doesn't cover that" and the question is routed to the expert.

**Expert loop:** every question and answer is logged (`learner/qa_log.jsonl`). Unanswered or low-confidence questions appear for the tutorial maker (`GET /projects/{id}/learner/questions?unresolved=true`); their answer can be added to the tutorial like the existing question loop.

## 2. Proactive Checks

A new pipeline stage, `checks`, after `edit` (it needs the kept times to place checks), writing `checks/checks.json`.

### Categories

| Category | Candidate facts (collected in code, no keyword lists) |
|---|---|
| **Safety-critical** | Compliance notes of kind requirement / caution / conflict with severity warning or critical; step cautions; expert answers to safety gaps (e.g. "power the printer off before reaching inside") |
| **Easy to mess up** | Stated sizes, counts and settings (1/8″, M3×6); sub-step emphasis ("do not over-tighten"); gaps the expert had to fill; low-confidence steps; order-sensitive steps |
| **Comprehension** | Each step's purpose and expected result; how to tell the step worked |

### Generation

1. Code collects candidate facts per step, each with an id and its source.
2. One LLM call per batch of steps (`learner_checks`) writes a **pool** of questions larger than needed. Each question has: category (enum), the fact ids it tests (offered ids only), the question, a format (multiple choice / true-false / short answer), the correct answer, distractors, an explanation citing its facts, and a suggested placement (before or after the step).
3. Validation in code: fact ids exist; numbers in the answer and explanation appear in the cited facts; a multiple-choice question has exactly one correct option; invalid questions are dropped.
4. **Selection is plain code**, so the tutorial maker can retune it without new LLM calls.

### Tutorial-maker controls (`checks:` config section and API)

| Setting | Meaning | Example default |
|---|---|---|
| `mix` | Share of each category | safety 0.40, pitfall 0.35, comprehension 0.25 |
| `max_per_step`, `max_total` | Caps | 2, 20 |
| `cover_all_critical` | Every critical safety fact gets a check regardless of the mix | true |
| `placement` | Per category: before or after the step | safety before, pitfall before, comprehension after |
| `gate_safety` | The learner must answer a safety check correctly before the step plays | true |
| `formats` | Allowed formats | multiple choice, true/false |
| Per-check overrides | Enable, disable or edit a single check (`PATCH /projects/{id}/checks/{check_id}`), stored in `inputs/checks_overrides.json` | none |

Selection order: critical safety checks first (when `cover_all_critical`), then fill by `mix` round-robin across steps, respecting the caps and overrides.

## 3. Player And Studio (Demo)

- **Our tutorial tab:** checks appear at step boundaries; gated safety checks pause the video until answered; feedback shows the explanation, its citation and a "show me" jump. An **Ask** panel sits with the step sidebar.
- **Expert studio:** a "Learner checks" panel with the mix sliders, caps and per-check toggles, recomputing the selection live from the pool (the same selection code, mirrored in the page).
- The published demo cannot call the API, so it replays real recorded answers for a set of sample learner questions, labelled as recorded, the same way the studio replays the expert session.

## 4. Evaluation

- **Q&A:** a small set of learner questions per sample video with expected source ids; measure citation validity, answer support, and correct "not covered" refusals.
- **Checks:** for each video, does every critical safety fact get a check; are the mix and caps respected; are answers supported by their cited facts; a manual review of question quality on the X1C sample.

## 5. Order Of Work

1. Evidence index and `ask` (backend, API, tests with the fake provider).
2. `checks` stage: candidate facts, pool generation, validation, selection, overrides (tests).
3. Demo: checks in the player, Ask panel with recorded answers, tuning panel in the studio.
4. Live run on the X1C sample (Gemini free tier: about one call per batch of steps for checks, one per question for Q&A) and evaluation.
