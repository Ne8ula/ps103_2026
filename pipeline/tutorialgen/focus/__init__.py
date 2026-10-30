"""Hand-driven focus: ROI candidates from landmarks (``roi``) and the render crop (``crop``).

The LLM never writes coordinates. Draft offers numbered boxes (drawn on the keyframes and described
in text) and the model picks a box id or "full" per sub-step; code validates the id and render turns
it into a smooth, aspect-preserving crop that never cuts a hand out.
"""

from __future__ import annotations

from ..config import Config
from ..gesture import GestureConfig, build_timeline
from ..project import Project
from ..schemas.media import HandFrame, Scenes, VideoMeta
from .roi import FULL, KINDS, FocusConfig, Timeline, candidate_boxes

HANDS = "hands/frames.jsonl"
SCENES = "hands/scenes.json"

__all__ = ["FULL", "KINDS", "FocusConfig", "Timeline", "candidate_boxes", "load_cuts", "load_timeline"]


def load_timeline(project: Project, config: Config, frames: list[HandFrame] | None = None) -> Timeline | None:
    """The gesture timeline (per-sample hand observations) of the project, or None without landmarks."""
    if frames is None:
        if not project.exists(HANDS):
            return None
        frames = project.read_jsonl(HANDS, HandFrame)
    if not frames:
        return None
    gcfg = config.section("gestures", GestureConfig)
    aspect = gcfg.default_aspect
    if project.exists("ingest/meta.json"):
        meta = project.read("ingest/meta.json", VideoMeta)
        if meta.width > 0 and meta.height > 0:
            aspect = meta.width / meta.height
    return Timeline(build_timeline(sorted(frames, key=lambda f: f.t), aspect, gcfg), aspect)


def content_box(video, samples: int = 12, dark: float = 16.0) -> list[float]:
    """Normalized [x0, y0, x1, y1] of the picture inside black letterbox / pillarbox bars (else the frame).

    A row or column counts as bar when it is dark in every sampled frame; only bars touching the edges count.
    """
    import cv2
    import numpy as np

    cap = cv2.VideoCapture(str(video))
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    rows = cols = None
    try:
        for k in range(samples):
            cap.set(cv2.CAP_PROP_POS_FRAMES, int((k + 0.5) * n / samples) if n else 0)
            ok, f = cap.read()
            if not ok:
                continue
            g = f.mean(axis=2)
            r, c = g.mean(axis=1), g.mean(axis=0)
            rows = r if rows is None else np.maximum(rows, r)
            cols = c if cols is None else np.maximum(cols, c)
    finally:
        cap.release()
    if rows is None:
        return [0.0, 0.0, 1.0, 1.0]

    def span(v):
        lit = np.nonzero(v > dark)[0]
        return (lit[0], lit[-1] + 1) if len(lit) else (0, len(v))

    (y0, y1), (x0, x1) = span(rows), span(cols)
    return [round(float(x0) / len(cols), 4), round(float(y0) / len(rows), 4), round(float(x1) / len(cols), 4),
            round(float(y1) / len(rows), 4)]


def load_cuts(project: Project) -> list[float]:
    return [c.t for c in project.read(SCENES, Scenes).cuts] if project.exists(SCENES) else []
