"""Stage 'perception': MediaPipe hand landmarks on frames sampled from the normalized video, One Euro
smoothing per handedness track, and HSV-histogram scene cuts.

Outputs: hands/frames.jsonl (one HandFrame per sampled frame, empty ``hands`` included),
hands/summary.json, hands/scenes.json.
"""

from __future__ import annotations

import time
from typing import Callable

import numpy as np
from pydantic import BaseModel, ConfigDict, Field

from ..media import hands as H
from ..media import video
from ..media.scenes import SceneCutDetector
from ..schemas.media import Hand, HandFrame, HandsSummary, SceneCut, Scenes, VideoMeta
from . import StageContext


class SmoothingSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    min_cutoff: float = Field(1.0, description="Hz; lower = smoother at rest")
    beta: float = Field(1.0, description="speed coefficient, speed in hand-sizes per second")
    d_cutoff: float = 1.0
    reset_gap_s: float = Field(0.5, description="restart a track after the hand is missing this long")

    def label(self) -> str:
        if not self.enabled:
            return "none"
        return f"one_euro(min_cutoff={self.min_cutoff:g},beta={self.beta:g},d_cutoff={self.d_cutoff:g})"


class PerceptionSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sample_fps: float = Field(15.0, description="frames per second sampled from the normalized video")
    num_hands: int = 2
    min_detection_confidence: float = 0.5
    min_presence_confidence: float = 0.5
    min_tracking_confidence: float = 0.5
    model_path: str | None = Field(None, description="hand_landmarker.task; default downloads to pipeline/models/")
    mirror_handedness: bool = Field(False, description="flip Left/Right; only for horizontally mirrored footage")
    dedupe_handedness: bool = Field(True, description="if both hands get the same label, relabel the weaker one")
    smoothing: SmoothingSettings = SmoothingSettings()
    scene_threshold: float = Field(0.4, description="Bhattacharyya HSV-histogram distance that counts as a cut")
    scene_min_gap_s: float = 0.5
    decimals: int = Field(5, description="rounding of stored landmark coordinates")


Detector = Callable[[np.ndarray, float], list[H.DetectedHand]]


def _hand(h: H.DetectedHand, nd: int) -> Hand:
    return Hand(
        handedness=h.handedness, score=round(h.score, 4),
        landmarks=np.round(h.landmarks, nd).tolist(),
        world_landmarks=np.round(h.world_landmarks, nd).tolist() if h.world_landmarks is not None else None,
    )


def process(path: str, fps: float, cfg: PerceptionSettings, detect: Detector,
            log=None) -> tuple[list[HandFrame], list[SceneCut]]:
    """Run detection, handedness fixes, smoothing and scene cuts over the sampled frames."""
    smoother = H.HandSmoother(cfg.smoothing.min_cutoff, cfg.smoothing.beta, cfg.smoothing.d_cutoff,
                              cfg.smoothing.reset_gap_s) if cfg.smoothing.enabled else None
    scenes = SceneCutDetector(cfg.scene_threshold, cfg.scene_min_gap_s)
    frames: list[HandFrame] = []
    cuts: list[SceneCut] = []
    for i, t, rgb in video.iter_frames(path, fps, cfg.sample_fps):
        if (score := scenes.update(rgb, t)) is not None:
            cuts.append(SceneCut(t=round(t, 3), frame=i, score=round(score, 4)))
        hands = H.fix_handedness(detect(rgb, t), cfg.mirror_handedness, cfg.dedupe_handedness)
        if smoother is not None:
            hands = smoother(hands, t)
        hands.sort(key=lambda h: h.handedness)
        frames.append(HandFrame(frame=i, t=round(t, 4), hands=[_hand(h, cfg.decimals) for h in hands]))
        if log and len(frames) % 150 == 0:
            log.info("perception: %d frames (t=%.1fs)", len(frames), t)
    return frames, cuts


def run(ctx: StageContext) -> None:
    p = ctx.project
    cfg = ctx.config.section("perception", PerceptionSettings)
    meta = p.read("ingest/meta.json", VideoMeta)
    model_path = H.ensure_model(cfg.model_path)
    started = time.perf_counter()
    with H.HandLandmarker(model_path, cfg.num_hands, cfg.min_detection_confidence, cfg.min_presence_confidence,
                          cfg.min_tracking_confidence, device=ctx.config.device) as landmarker:
        frames, cuts = process(str(p.path(meta.video_path)), meta.fps, cfg, landmarker.detect, ctx.log)
        device = landmarker.device
    elapsed = time.perf_counter() - started

    p.write_jsonl("hands/frames.jsonl", frames)
    p.write("hands/scenes.json", Scenes(cuts=cuts))
    summary = HandsSummary(
        model=model_path.name, sample_fps=min(cfg.sample_fps, meta.fps), frames_processed=len(frames),
        frames_with_hands=sum(1 for f in frames if f.hands), smoothing=cfg.smoothing.label(), device=device,
        mirror_handedness=cfg.mirror_handedness, frames_with_two_hands=sum(1 for f in frames if len(f.hands) >= 2),
        elapsed_s=round(elapsed, 2),
    )
    p.write("hands/summary.json", summary)
    ctx.log.info("perception: %d/%d sampled frames with hands, %d scene cuts, %.1fs on %s",
                 summary.frames_with_hands, summary.frames_processed, len(cuts), elapsed, device)
