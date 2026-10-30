# tutorialgen

Turns an unstructured demo video plus optional SOPs/compliance manuals into a stepwise tutorial: per-step instructions with cited compliance notes, questions for the uploader about missing information, saved hand-pose data, and a rendered video with hand overlays and text cards. Goals and milestones: [`../GOALS.md`](../GOALS.md).

## Setup

```bash
python3 -m venv ../.venv && ../.venv/bin/pip install -e '.[dev]'
../.venv/bin/python samples/fetch.py          # development video + SOP
../.venv/bin/python -m pytest -q               # fast tests; -m slow runs media/model tests
```

## LLM Providers

`llm.provider: auto` (the default) uses GPT-5.4 mini if `OPENAI_API_KEY` is set, else Gemini if `GEMINI_API_KEY` is set, else the deterministic fake provider, whose text is clearly marked `[fake LLM]`.

| Provider | Set | Notes |
|---|---|---|
| `openai` | `OPENAI_API_KEY` | Responses API; default model `gpt-5.4-mini` |
| `gemini` | `GEMINI_API_KEY` (free key from Google AI Studio) | OpenAI-compatible endpoint; default `gemini-3.6-flash`; requests spaced 6 s apart for free-tier limits. The free tier's content is used to improve Google's products, so use it only with public material |
| `ollama` | a local Ollama server | Offline and private; default `qwen2.5vl:3b` |
| `chat` | `llm.base_url`, `llm.model`, `llm.api_key_env` | Any other OpenAI-compatible endpoint |

Chat providers try strict JSON-schema output and fall back to JSON mode with local validation if the endpoint rejects the schema.

## Demos Without Paying Per Run

Every LLM answer is cached in `<project>/llm_cache/`. Run a project once with a real provider, then demo it with replay, which never contacts a model and fails on any request that was not recorded:

```bash
GEMINI_API_KEY=... $tg run <project>                     # records answers (free tier)
printf 'llm:\n  provider: gemini\n  replay: true\n' > projects/<project>/config.yaml
$tg run <project>                                        # all stages skipped; no key needed
```

Answering a new question in a replayed project needs a live run, since that answer has not been recorded.

## Use

```bash
tg="../.venv/bin/python -m tutorialgen"
$tg new "Hand washing" --video samples/data/sfdph-wash-hands-en.webm --doc samples/data/fda-food-code-2022.pdf
$tg run <project>                 # runs every stage that is out of date
$tg questions <project>           # what the system needs from the uploader
$tg answer <project> q001 "Use warm water"
$tg run <project>                 # refine -> compliance -> questions -> render re-run; earlier stages are skipped
$tg status <project>
$tg serve --port 8000             # HTTP data endpoints; OpenAPI docs at /docs
```

`--video` accepts a YouTube (or any yt-dlp) URL or a local file. Projects live in `projects/` (override with `TUTORIALGEN_HOME`).

## Layout

| Path | Purpose |
|---|---|
| `tutorialgen/schemas/` | Typed contract for every artifact; one module per workstream |
| `tutorialgen/stages/` | One module per stage; registry and order in `stages/__init__.py` |
| `tutorialgen/runner.py` | Dependency-ordered execution with fingerprint-based skipping |
| `tutorialgen/llm/` | Provider-neutral interface, on-disk cache, OpenAI and fake adapters |
| `tutorialgen/prompts/` | Versioned prompt templates (`# system` / `# user`) |
| `tutorialgen/defaults.yaml` | Default config; per-project `config.yaml` and `TUTORIALGEN_*` env vars override |

## Structured Steps And Hand-Driven Focus

The LLM makes small choices from options that code generated; code does the bookkeeping.

- **Gesture text as summaries** (`segment.gesture_format`, `draft.gesture_format`: `summary` | `keyframes` | `both`): one computed line per interval from every landmark sample (share of time each hand is visible, dominant grip, hand contact, active share, back-and-forth vs. net motion, position) plus hand-state change events. Each interval names the image, or the panel of a labelled 2x2 contact sheet, that shows it (`segment.sheet_panels`).
- **Focus boxes** (`tutorialgen/focus/`, config section `focus`): per step and shot, B1 both hands, B2 work zone (where the hands touch or a pinch/power grip is held), B3/B4 single hands when they work apart. They are drawn and labelled on the draft keyframes (`draft/keyframes/<step>/k<n>_boxes.jpg`) and described per image; the model picks an id or `full`, and unknown ids fall back deterministically.
- **Sub-steps** (`Step.substeps`): action phases with starts snapped to anchors (step start, narration starts, hand-state changes), bounded captions (`draft.caption_max_chars`), a focus id and an optional emphasis callout. The number guard covers them.
- **Render**: per sub-step and shot, an aspect-preserving crop of the chosen box (`focus.max_zoom`, `focus.min_zoom_gain`, `focus.min_crop_frac`), eased pans within a shot (`focus.pan_s`), hard switches at cuts, kept off letterbox bars, grown when needed so no drawn hand is ever cropped out (eased over `focus.contain_ramp_s`). Sub-step captions, a step progress bar, a tools/materials chip, emphasis chips and safety callouts (compliance notes by id, verbatim) are added; no extra LLM call. `focus.enabled: false` or `render.substep_captions / progress_bar / callouts: false` switch parts off. `tutorial.json` records `crop_plan` and `callouts` per step.

## Stages

`ingest → perception → transcribe → gestures → candidates → segment → draft → refine → compliance → questions → render`

Each stage reads upstream files and writes its own folder in the project. A stage re-runs only when its config sections, upstream outputs or inputs change. Stages marked `gpu=True` are the ones intended for a remote GPU worker.
