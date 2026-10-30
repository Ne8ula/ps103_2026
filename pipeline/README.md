# tutorialgen

Turns an unstructured demo video plus optional SOPs/compliance manuals into a stepwise tutorial: per-step instructions with cited compliance notes, questions for the uploader about missing information, saved hand-pose data, and a rendered video with hand overlays and text cards. Goals and milestones: [`../GOALS.md`](../GOALS.md).

## Setup

```bash
python3 -m venv ../.venv && ../.venv/bin/pip install -e '.[dev]'
../.venv/bin/python samples/fetch.py          # development video + SOP
../.venv/bin/python -m pytest -q               # fast tests; -m slow runs media/model tests
```

`OPENAI_API_KEY` switches the LLM stages from the deterministic fake provider to GPT-5.4 mini. Without it, every stage still runs and produces clearly placeholder text.

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
