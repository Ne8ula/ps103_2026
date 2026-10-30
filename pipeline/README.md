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
| `gemini` | `GEMINI_API_KEY` (free key from Google AI Studio) | OpenAI-compatible endpoint; default `gemini-3.8-flash`; requests spaced 6 s apart for free-tier limits. The free tier's content is used to improve Google's products, so use it only with public material |
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

## Stages

`ingest → perception → transcribe → gestures → candidates → segment → draft → refine → compliance → questions → render`

Each stage reads upstream files and writes its own folder in the project. A stage re-runs only when its config sections, upstream outputs or inputs change. Stages marked `gpu=True` are the ones intended for a remote GPU worker.
