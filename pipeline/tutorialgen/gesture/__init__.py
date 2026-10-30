"""Our reimplementation of the GestLLM approach (arXiv 2501.07295): hand landmarks -> keyframe features -> text.

geometry   single-hand features (finger state, direction, groups, grip, palm facing, plausibility)
timeline   per-frame observations with jitter rejection, speed, shape change, interaction, activity
keyframes  debounced keyframe selection and trajectory between keyframes
text       deterministic, LLM-agnostic text rendering
motion     motion energy and boundary candidates (stage 'candidates')
config     every threshold, as the stage config models
"""

from __future__ import annotations

from .config import CandidatesConfig, GestureConfig
from .keyframes import VERSION, build_keyframes
from .timeline import build_timeline

__all__ = ["VERSION", "CandidatesConfig", "GestureConfig", "build_keyframes", "build_timeline"]
