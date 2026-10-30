"""Stage 'candidates': heuristic step-boundary candidates -> candidates/candidates.json.

Sources: scene cuts, motion pauses (low-energy runs and energy minima), hand-state changes (gesture
keyframe reasons), hands entering/leaving, narration pauses. Falls back to scene cuts plus evenly
spaced candidates when no hand is ever detected.
"""

from __future__ import annotations

import numpy as np

from ..gesture import CandidatesConfig
from ..gesture import motion as m
from ..schemas.gestures import BoundaryCandidate, Candidates, GestureTrack
from ..schemas.media import HandFrame, Scenes, Transcript, VideoMeta
from . import StageContext


def _read(ctx: StageContext, rel: str, model):
    return ctx.project.read(rel, model) if ctx.project.exists(rel) else None


def run(ctx: StageContext) -> None:
    cfg = ctx.config.section("candidates", CandidatesConfig)
    meta = _read(ctx, "ingest/meta.json", VideoMeta)
    scenes = _read(ctx, "hands/scenes.json", Scenes)
    transcript = _read(ctx, "transcript/transcript.json", Transcript)
    track = _read(ctx, "gestures/gestures.json", GestureTrack)
    frames = ctx.project.read_jsonl("hands/frames.jsonl", HandFrame) if ctx.project.exists("hands/frames.jsonl") else []
    frames.sort(key=lambda f: f.t)

    aspect = meta.width / meta.height if meta and meta.height else 16 / 9
    ts, energy, counts = m.motion_energy(frames, aspect, cfg.max_gap_s)
    energy = m.smooth(ts, energy, cfg.energy_smooth_s)

    ends = [meta.duration if meta else 0.0, float(ts[-1]) if len(ts) else 0.0]
    if transcript and transcript.segments:
        ends.append(max(s.end for s in transcript.segments))
    duration = max(ends)

    raws = m.scene_candidates(scenes) + m.narration_candidates(transcript, cfg)
    if len(counts) and counts.max() > 0:
        raws += m.pause_candidates(ts, energy, counts, cfg)
        raws += m.hand_count_candidates(ts, counts, cfg)
        raws += m.state_change_candidates(track, cfg)
    else:
        ctx.log.warning("candidates: no hands detected; using scene cuts and even spacing")
        raws += m.even_candidates(duration, cfg)

    boundaries = []
    for t, score, reasons in m.merge_candidates(raws, cfg):
        if score < cfg.min_score or t < cfg.edge_margin_s or t > duration - cfg.edge_margin_s:
            continue
        if meta and meta.fps > 0:
            frame = int(round(t * meta.fps))
        elif len(ts):
            frame = frames[int(np.argmin(np.abs(ts - t)))].frame
        else:
            frame = 0
        boundaries.append(BoundaryCandidate(t=round(t, 3), frame=frame, score=score, reasons=reasons))

    ctx.project.write("candidates/candidates.json",
                      Candidates(boundaries=boundaries, activity=m.activity_samples(ts, energy, counts, cfg)))
    ctx.log.info("candidates: %d raw -> %d boundaries", len(raws), len(boundaries))
