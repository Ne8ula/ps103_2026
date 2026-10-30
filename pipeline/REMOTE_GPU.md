# Remote GPU Worker

Status: **prepared, not deployed.** The provider and dispatch method are still open (see GOALS.md).

## Contract

Stages are pure functions of the project folder, so a worker needs only the folder and the image:

1. Sync the project folder to the worker (`/work/projects/<id>`).
2. Run exactly the heavy stages: `docker run --gpus all -v <dir>:/work/projects tutorialgen-worker <id> --only transcribe --only perception` (later `--only render`).
3. Sync the folder back. The manifest carries each stage's fingerprint and output hash, so the local runner sees them as done and continues with gestures → … without re-running them.

`--only` refuses to run a stage whose requirements are not done, which catches a missing sync early. In the API, the hook is `dispatch` in `tutorialgen/api/jobs.py`: a remote implementation would split a run at the `gpu=True` stages, ship those, and run the rest locally.

## What the GPU Actually Speeds Up

| Stage | On GPU | Notes |
|---|---|---|
| transcribe | Yes: faster-whisper on CUDA (float16, `small` model) | Biggest win for long narrated videos |
| perception | Maybe: MediaPipe's GPU delegate uses OpenGL ES/EGL, not CUDA | Falls back to CPU automatically; needs the `graphics` driver capability in the container |
| render | No, for now: the bundled ffmpeg has no NVENC | CPU libx264; a system ffmpeg with NVENC would be needed |

On this development machine (CPU), the 58 s sample takes about 100 s from ingest through refine. A 2-minute YouTube video took about 2 min for perception and 2.5 min for transcription.

## Open Decisions

- Provider (e.g. a RunPod pod vs. a serverless endpoint), and how folders are synced (object storage vs. rsync).
- Whether to dispatch per stage or per run.
- Image build and a real-GPU test run, including confirming the MediaPipe GPU delegate works headless.
