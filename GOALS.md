# Demo Video → Stepwise Tutorial Pipeline — Goals

Working document for a long, multi-stage implementation. Update the status column as milestones land. Nothing is committed until the user says so.

## Functionality 1 — Unstructured Demo → Compliant Stepwise Tutorial

**Inputs**

1. An unstructured demo video. YouTube URL first; must also accept any local recording (phone, screen-capture, webcam).
2. Optional reference documents: compliance manual, SOPs, safety sheets, etc. (PDF, DOCX, TXT/MD).
3. The uploader's answers to questions the software asks about missing step information.

**Output**

A tutorial package containing:

- A rendered tutorial video: original footage cut into steps, with hand-pose skeletons overlaid, interlaced with text instruction cards/captions per step.
- The saved hand-pose data (per-frame landmarks, per-step gesture summaries) so poses can be replayed or reused later (e.g. for a future "compare my hands to the demo" feature).
- A structured tutorial document (JSON + human-readable view): ordered steps, time ranges, instruction text, tools/materials, cautions, and compliance notes with citations to the uploaded SOP/manual.

**Hard requirements**

- **Not a one-shot LLM call.** Processing is a staged pipeline; each stage has a typed input/output, is cached on disk, and can be re-run on its own.
- **MediaPipe Hands** (Hand Landmarker) provides hand poses from the video.
- **GestLLM** bridges hand poses and language: landmark sequences become textual gesture/action descriptions the LLM can reason over.
- **GPT-5.4 mini** (with GestLLM output, keyframes and transcript) segments the video into steps and drafts the instructions.
- **RAG** over the compliance manual / SOPs grounds compliance and safety notes; every such note cites the source chunk.
- **Human-in-the-loop:** the system identifies missing or ambiguous step information and asks the uploader targeted questions; answers are merged and only affected steps are regenerated.

**Guardrails**

- The LLM must not invent numeric safety values, settings, or compliance claims. Anything not grounded in the video, the documents or the uploader's answers becomes a question, not an assertion.
- Every step records its provenance: which frames, gestures, transcript spans, document chunks and user answers it came from.
- Low-confidence segmentations and SOP conflicts are surfaced to the uploader, not silently resolved.

## Functionality 2

_Learner assistant: on-request Q&A over the tutorial, SOP, transcript and expert answers, plus proactive checks (safety-critical, easy to mess up, comprehension) that the tutorial maker can tune. Designed, not built: see [pipeline/LEARNER_ASSISTANT.md](pipeline/LEARNER_ASSISTANT.md)._

## Decisions (29 Oct 2026)

| Topic | Decision |
|---|---|
| GestLLM | No public release exists: no Hugging Face model or Space, and the paper ([arXiv 2501.07295](https://arxiv.org/abs/2501.07295)) links no code or weights. **We reimplement its approach** as our own `gesture_text` module: MediaPipe landmarks → noise/confidence filtering → keyframe features (per-finger extended/curled, finger direction as an angle plus one of 8 compass words, adjacent-finger grouping, hand trajectory between keyframes) → text. Following the paper, the LLM first names and describes the gesture/action, and only then interprets it in task context. We extend it with object-manipulation cues (grip type, two-hand interaction, idle vs. active) because demo videos are manipulation, not command gestures. |
| Gesture text design | `gesture_text` is **LLM-agnostic**: it outputs a versioned schema plus a plain-text rendering, with no model-specific prompt in it. Thresholds live in one config file. It can be switched off per run, to compare segmentation with and without it. Hands occluded by tools or objects produce an explicit `not_visible` / `low_confidence` state instead of guessed fingers. Keyframes are chosen where the hand state or speed changes. |
| LLM | Provider interface with adapters; **GPT-5.4 mini via the OpenAI SDK is the first and default adapter**. The model ID is config, not hard-coded. Other LLMs (Claude, Gemini, local models) are added later as adapters without touching the stages. A fixture/fake adapter backs tests. |
| API key / infra | Deferred. Code reads `OPENAI_API_KEY` from env; until then, LLM stages run against recorded fixtures. |
| Transcription | Yes, when the video has an audio track: Whisper (faster-whisper) with word timestamps. If there is no audio, skip it silently and mark `transcript: none`. |
| Compute | Heavy stages (MediaPipe, Whisper, rendering) target a **remote GPU**; the provider and deployment are decided later. Stages must be runnable as standalone jobs (inputs and outputs are files) so they can be moved to a remote worker without code changes. CPU fallback is kept for local development. |
| UI | **Out of scope for now.** Deliver data endpoints only (FastAPI): create a project, upload video/URL and documents, run/inspect stages, get questions, post answers, fetch the tutorial artifacts. |
| Samples | The user has none. We pick a short, permissively licensed public demo video with clear hands and narration, plus a public SOP/compliance document (e.g. a government safety procedure) relevant to it. Record both, with license and URL, in `pipeline/samples/README.md`. |

## Pipeline Stages

Each stage writes to `projects/<project_id>/<stage>/` so runs are resumable and debuggable.

| # | Stage | What it does | Key output |
|---|---|---|---|
| 0 | Ingest | Download (yt-dlp) or accept a local file; normalize with ffmpeg (fps, resolution, audio track) | `source.mp4`, `meta.json` |
| 1 | Perception | MediaPipe Hand Landmarker per frame (handedness, 21 landmarks, world coords); temporal smoothing; scene-cut detection; speech-to-text if narration exists | `landmarks.parquet`, `scenes.json`, `transcript.json` |
| 2 | Gesture text (GestLLM approach, our implementation) | Keyframe features per the paper (finger states, 8-way directions, finger groups, trajectory) plus manipulation cues (grip type, two-hand interaction, idle vs. active) rendered as text per window | `gestures.jsonl` |
| 3 | Candidate segmentation | Heuristic step boundaries from motion energy, hand-state changes, scene cuts and narration pauses | `candidates.json` |
| 4 | Step segmentation (LLM) | GPT-5.4 mini merges/splits candidates in windows using gesture text + keyframes + transcript; structured JSON output | `steps.v1.json` |
| 5 | Step drafting (LLM) | Per step: title, action, tools/materials, expected result, cautions, confidence, missing-info flags | `steps.v2.json` |
| 6 | Document RAG | Chunk + embed SOP/manual; retrieve per step; attach cited compliance notes; flag conflicts and required steps absent from the video | `index/`, `compliance.json` |
| 7 | Gap questions | Turn missing-info flags, low confidence and SOP gaps into prioritized questions for the uploader | `questions.json` |
| 8 | Answer merge | Ingest answers; regenerate only affected steps; loop back to 7 until no blocking questions remain | `answers.json`, `steps.vN.json` |
| 9 | Assembly | Render MP4: per-step clips with skeleton overlay, text cards, captions; export tutorial JSON and readable view | `tutorial.mp4`, `tutorial.json` |

## Milestones And Acceptance Criteria

| ID | Milestone | Done when | Status |
|---|---|---|---|
| M0 | Contracts and skeleton | Pydantic schemas for every stage artifact; `pipeline/` package; CLI `run --stage`; LLM provider interface with a fixture/fake backend; sample demo video and SOP chosen and documented | ☑ |
| M1 | Ingest + perception | YT URL and local file both produce normalized video, landmarks and transcript; debug render with skeletons matches the hands visually | ☑ |
| M2 | GestLLM gesture text | Finger state, 8-way direction, grouping, trajectory and manipulation cues produced at keyframes; occlusion handled explicitly; unit tests on synthetic landmark poses; spot-check on sample video reads correctly to a human | ☑ |
| M3 | Segmentation + drafting | Sample video yields an ordered step list with time ranges and drafted text; structured outputs validate against schemas | ☑ |
| M4 | RAG compliance | SOP indexed; each step has cited notes or an explicit "no relevant guidance"; at least one deliberate conflict is detected | ☑ |
| M5 | Question loop | Questions generated, answered via CLI/API, merged; only affected steps change | ☑ |
| M6 | Tutorial render | `tutorial.mp4` with overlays and text cards, plus `tutorial.json` with provenance | ☑ |
| M7 | Data endpoints | FastAPI covers the full flow (project → inputs → stages → questions → answers → artifacts) and is exercised end-to-end by tests; no UI | ☑ |
| M8 | Remote GPU | Heavy stages run on a remote GPU worker (provider TBD) with identical outputs to the local run | ◐ prepared: `run --only`, worker Dockerfile, REMOTE_GPU.md; not deployed |
| M9 | Evaluation | Small eval set (2–3 videos) with hand-labelled steps; report boundary accuracy and question usefulness, **with vs. without gesture text**, to confirm it earns its place | ◐ harness + labels for the SFDPH sample; real scores and the gesture-text comparison need the OpenAI key |

## Proposed Architecture

- **Backend:** Python 3.12 package `pipeline/` (MediaPipe, OpenCV, ffmpeg, yt-dlp, faster-whisper, OpenAI SDK, embeddings + local vector store), exposed via CLI and FastAPI data endpoints.
- **LLM calls:** small, typed prompts per stage using structured outputs (JSON schema); all prompts versioned in `pipeline/prompts/`; responses cached by input hash.
- **Compute:** every stage is a pure function of files in → files out, so GPU-heavy stages can be shipped to a remote worker later.
- **Frontend:** none for now. The existing Benchmate React app is left untouched.
- **Storage:** per-project folders on disk; no database needed until multi-user.

## Multi-Agent Plan

Agents only after **M0** is done serially, because every workstream depends on the shared schemas. Then, in isolated worktrees:

| Workstream | Scope | Depends on |
|---|---|---|
| A — Perception | Ingest, MediaPipe, smoothing, transcript, debug overlay | M0 |
| B — GestLLM | Landmark → gesture-text descriptors | M0 + fixture landmarks |
| C — RAG | Document parsing, chunking, embedding, retrieval, citation format | M0 only (fully independent) |
| D — LLM orchestration | Stages 4, 5, 7, 8 with prompts and caching, built against fixture inputs | M0 + fixtures |
| E — Render | Skeleton overlay, text cards, step clip assembly | M0 + fixture steps |
| F — API | FastAPI data endpoints and their tests | API contract from M0 |

Integration (wiring A→B→D→C→E end-to-end on the sample video) is done serially after the workstreams return.

## Status Notes (29 Oct 2026)

- M3–M5 are verified with the deterministic fake LLM, so structure, provenance, the number guard and the question loop work end to end; the *quality* of segmentation, drafted text and questions is unmeasured until GPT-5.4 mini runs.
- End to end on the SFDPH sample (CPU): ~100 s ingest→refine, ~5 min for the first compliance run (one-time index of the 668-page Food Code), ~45 s for a re-run from segment; answering a question re-runs only refine→render.
- First live run (30 Oct 2026, Gemini free tier, gemini-3.6-flash with fallback to gemini-3-flash-preview; ~18 calls): 4 steps, boundary F1 0.75 (precision 1.0, recall 0.6; fake LLM: 0.46), 6/6 key facts stated, both expected gaps (water temperature, soap amount) raised, Food Code §2-301.12 cited, 18 compliance notes with 2 dropped by quote validation. Weak spots: SOP missing-step questions ask the uploader for facts the SOP already states; "alternative" advice (door, home towel) merged into rinse/dry. The gesture-text comparison is still pending: the free tier allows 20 requests per model per day.
- First **unstructured** run (30 Oct 2026, uncut X1C livestream excerpt, 13.5 min, Bambu wiper SOP; 56 LLM calls, 42 of them on gemini-3.1-flash-lite after the 20/day caps): 22 steps vs. 7 labelled, boundary F1 0.32 at ±15 s (0.0 at ±5 s), 7/7 key facts, 2/2 expected questions, 2/2 expected SOP notes, power-off requirement flagged. Failures to fix: over-segmentation; narrated explanation and hypotheticals turned into steps (s17–s21); conflicts raised where the SOP is simply silent; questions bundling many gaps. The SFDPH scores (F1 0.75) reflect its narration and cuts, not the pipeline's ability on real demos.
- Edit stage (10 Nov 2026): the method used to keep 99% of the source and add cards, so the X1C tutorial (15:46) was longer than the raw excerpt (13:30). The new `edit` stage cuts idle and asides, speeds up long silent work 3x (muted), and guards spoken numbers and stated values. X1C: steps 803 s -> 520 s, tutorial 10:19, about 3 extra LLM calls. Not yet measured: whether learners still get every needed moment (no eval metric for that yet).
- Hands are detected in 54% of sampled frames on the sample; interlocked soapy hands mostly return no detection (reported as not visible, not guessed).

## Environment Gaps Found (29 Oct 2026)

- No `ffmpeg`, `yt-dlp` or GPU detected in this WSL environment; MediaPipe runs on CPU, which is fine for short demos.
- No `OPENAI_API_KEY` in the environment.
- Repo today is the Benchmate React/Vite mockup; there is no Python code yet.

## Open Items (Deferred)

- OpenAI API key provisioning.
- Remote GPU provider and job dispatch mechanism.
- Functionality 2.
- UI.
