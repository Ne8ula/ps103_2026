# Structured AI Engineering Plan

Techniques to improve each stage, beyond what is built today. Status: **A** = in progress by the RAG agent, **B** = in progress by the steps/render agent, blank = not started. Every technique is measured with `tutorialgen.eval` before it is kept.

The common pattern: let the LLM make **small, typed, verifiable choices**, and let code do the bookkeeping. Wherever possible the model picks from options code generated (ids, enums, boxes), cites evidence by id, and has its output checked before it is used.

## Perception And Transcript

| Technique | What it fixes | Status |
|---|---|---|
| **ROI re-inference**: crop around a detected or tracked hand, upscale, run the landmarker again | Small or distant hands; about half the sampled frames of the main sample have no detection | |
| **Track-level hand identity** (Hungarian matching + Kalman filter across frames) | Handedness label swaps, one-frame dropouts | |
| **Adaptive sampling**: 15 fps baseline, 30 fps around motion and grip changes, 5 fps when idle | Missed fast actions; wasted work on idle footage | |
| **Domain-primed transcription**: pass SOP vocabulary (terms from the indexed manual) as Whisper `hotwords` / `initial_prompt` (both supported in faster-whisper) | Misheard technical terms, tool and chemical names | |
| **Explicit enumeration parsing**: detect "Step 2", "first/next/finally" in the transcript deterministically | Gives segmentation strong, cheap boundary priors | |

## Gesture Text (GestLLM)

| Technique | What it fixes | Status |
|---|---|---|
| **Action primitives**: a small state machine maps feature sequences to a fixed verb vocabulary (rub, press, pinch-and-place, twist, pour, wipe), each with time span and confidence | The LLM gets semantic tokens instead of low-level finger geometry | |
| **Per-video normalization**: speed and size thresholds relative to the video's own distribution | Thresholds tuned on one camera distance fail on another | |
| **Interval summaries** instead of raw keyframe lines; keyframes mapped to numbered images | Prompt bloat; text not linked to images | B |
| **Set-of-mark prompting**: numbered hand/interaction boxes drawn on frames, referenced in text | The LLM can point at regions by id | B |

## Segmentation

| Technique | What it fixes | Status |
|---|---|---|
| **Constrained decoding with dynamic enums**: the output schema's boundary field is generated per window as an enum of the real candidate ids | The model cannot invent timestamps (today code snaps them afterwards) | |
| **Score-then-decode**: the LLM rates each candidate boundary (new step vs. same step, typed reason, confidence); a dynamic program with a step-length prior picks the global segmentation | Window-by-window decisions disagree; overlap merging is heuristic | |
| **Self-consistency**: 3 samples, keep boundaries a majority agree on | Unstable boundaries (costs 3× calls, so use only on low-confidence windows) | |
| **Hierarchical pass**: chapters (prep / main procedure / alternatives / outro) first, then steps within | Intro/outro and "alternative" advice counted as steps (seen on the sample) | |

## Drafting

| Technique | What it fixes | Status |
|---|---|---|
| **Field-level evidence pointers**: every claim (instruction, tool, caution, expected result) carries ids of the transcript segments / keyframes / images that support it; code verifies the ids and drops unsupported claims into `missing_info` | Hallucinated tools and claims; extends the number guard to all content | |
| **Chain-of-verification**: a second, cheap call lists checkable claims from the draft and answers each against the evidence only; failing claims are removed | Plausible but unsupported details | |
| **Controlled vocabulary**: tools and materials canonicalized against a glossary built from the SOP index | "paper towel" vs. "towel" vs. "single-use towel" drift; better compliance matching | |
| **One worked example in the prompt** (from a labelled video other than the one being processed) | Inconsistent granularity and tone | |
| **Sub-steps with time ranges, focus box, callouts** for layout | Unstructured video formatting | B |

## RAG And Compliance

| Technique | What it fixes | Status |
|---|---|---|
| Faceted sub-queries, sentence-id citations, neighbour expansion, typed claims, extracted SOP procedure | Retrieval misses; quote-mismatch drops | A |
| **Cross-encoder reranking** of the fused top 30 (`BAAI/bge-reranker-base` via fastembed, local and free) | Weak dense ranks (§2-301.12 is rank 21 for "rinse" today) | |
| **Contextual chunk headers**: prepend document > chapter > section path to each chunk before embedding | Chunks that are meaningless without their heading | |
| **Obligation table at index time**: extract atomic requirements (modality shall/must/should, action, object, parameter + unit, conditions, exceptions, citation) once per document; match steps to requirements, not raw chunks | Compliance becomes a structured comparison, with conflicts computed in code where values are numeric | |
| **Entailment check per note** (supports / contradicts / not addressed), separate from generation | Notes that cite real text but misstate it | |

## Questions And Answers

| Technique | What it fixes | Status |
|---|---|---|
| **Value-of-information ranking**: priority = blocking × safety weight × steps affected × (1 − confidence) | Arbitrary question order; important gaps capped out | |
| **Typed answer slots**: each question declares the expected type (duration, quantity + unit, choice from SOP values, yes/no); answers are parsed and validated before refine | Free-text answers misread; numbers lost | |
| **SOP-sourced choices**: for conflicts, options come from cited SOP values ("at least 20 s (Food Code §2-301.12)", "other") | Uploader has to guess what the system wants | |
| **Patch-based refine**: the LLM returns typed edits (set field / add caution / resolve gap id) applied by code, instead of rewriting the step | Unrelated fields changing when an answer is merged | |

## Cross-Cutting

| Technique | Why | Status |
|---|---|---|
| **Model routing**: lite model for phrasing questions and query rewrites, flash for segmentation and drafting | Halves free-tier quota use | |
| **Batching**: draft 3–4 adjacent steps per call | ~40 calls per video → ~20; free-tier daily caps | |
| **Deterministic settings**: temperature 0 where supported, prompts and schemas versioned (already in cache keys) | Reproducible demos and evaluations | |
| **LLM-as-judge with a rubric**: structured scores (actionable, complete, grounded, safe) per step on the eval set, with a different model as judge | Measures instruction quality, not just boundaries | |
| **Per-call telemetry** in `llm_cache` (latency, tokens, served model, retries) | Find the slow and expensive stages | partly (served model) |

## Suggested Order

1. Evidence pointers + constrained enums (segment, draft): the biggest grounding gains, cheap.
2. Cross-encoder reranking + obligation table (compliance): measurable retrieval and conflict gains.
3. Typed answer slots + patch-based refine: makes the question loop reliable.
4. Batching + model routing: fits the free tier.
5. Perception: ROI re-inference and track identity, then action primitives.
6. LLM-as-judge rubric, to keep all of the above honest.
