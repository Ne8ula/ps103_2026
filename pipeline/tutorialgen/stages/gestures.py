"""Stage 'gestures': hands/frames.jsonl -> gestures/gestures.json (GestLLM-style gesture text at keyframes)."""

from __future__ import annotations

import hashlib

from ..gesture import VERSION, GestureConfig, build_keyframes, build_timeline
from ..schemas.gestures import GestureTrack
from ..schemas.media import HandFrame, VideoMeta
from . import StageContext


def video_aspect(ctx: StageContext, default: float) -> float:
    if ctx.project.exists("ingest/meta.json"):
        meta = ctx.project.read("ingest/meta.json", VideoMeta)
        if meta.width > 0 and meta.height > 0:
            return meta.width / meta.height
    ctx.log.warning("gestures: ingest/meta.json missing; assuming aspect %.3f", default)
    return default


def run(ctx: StageContext) -> None:
    cfg = ctx.config.section("gestures", GestureConfig)
    frames = ctx.project.read_jsonl("hands/frames.jsonl", HandFrame)
    frames.sort(key=lambda f: f.t)
    timeline = build_timeline(frames, video_aspect(ctx, cfg.default_aspect), cfg)
    keyframes = build_keyframes(timeline, cfg)
    track = GestureTrack(version=VERSION, config_hash=hashlib.sha256(cfg.model_dump_json().encode()).hexdigest()[:16],
                         keyframes=keyframes)
    ctx.project.write("gestures/gestures.json", track)
    # Convenience for humans; not a declared output.
    (ctx.project.stage_dir("gestures") / "gestures.txt").write_text("\n".join(f"{k.id} {k.text}" for k in keyframes) + "\n")
    ctx.log.info("gestures: %d frames -> %d keyframes", len(frames), len(keyframes))
