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


def load_cuts(project: Project) -> list[float]:
    return [c.t for c in project.read(SCENES, Scenes).cuts] if project.exists(SCENES) else []
