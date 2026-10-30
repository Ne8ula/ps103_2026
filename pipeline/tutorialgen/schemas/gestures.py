"""Stage 2-3 artifacts: gesture text (our GestLLM approach) and boundary candidates. Owner: gesture workstream.

This schema is LLM-agnostic: no prompt wording lives here, only facts derived from landmarks.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from .common import Artifact

FingerName = Literal["thumb", "index", "middle", "ring", "pinky"]
Direction8 = Literal["up", "up-right", "right", "down-right", "down", "down-left", "left", "up-left"]
Speed = Literal["still", "slow", "moderate", "fast"]


class FingerState(Artifact):
    name: FingerName
    state: Literal["extended", "partial", "curled", "unknown"]
    direction_deg: float | None = Field(default=None, description="image-plane angle, 0 = right, 90 = up")
    direction: Direction8 | None = None


class Trajectory(Artifact):
    """Hand movement since the previous keyframe."""

    since_t: float
    direction: Direction8 | None
    distance: float = Field(description="palm-centre travel, fraction of image diagonal")
    speed: Speed


class HandDescription(Artifact):
    handedness: Literal["Left", "Right"]
    visibility: Literal["visible", "low_confidence", "not_visible"]
    visibility_reason: str | None = Field(default=None, description="why low_confidence: low_score, out_of_frame, too_small, implausible_shape, jitter, jump")
    fingers: list[FingerState] = []
    groups: list[list[FingerName]] = Field(default=[], description="fingers whose tips are close together")
    grip: Literal["open", "pinch", "power_grip", "point", "fist", "relaxed", "unknown"] = "unknown"
    palm_facing: Literal["camera", "away", "side", "unknown"] = "unknown"
    position: list[float] | None = Field(default=None, description="[x, y] palm centre, normalized")
    trajectory: Trajectory | None = None


class GestureKeyframe(Artifact):
    id: str = Field(description="g0001 ...")
    frame: int
    t: float
    reasons: list[str] = Field(description="why this frame is a keyframe, e.g. grip_change, speed_change, interval")
    hands: list[HandDescription]
    interaction: Literal["none", "hands_apart", "hands_close", "hands_touching"]
    activity: Literal["idle", "active"]
    text: str = Field(description="plain-text rendering for any LLM")


class GestureTrack(Artifact):
    """gestures/gestures.json"""

    version: str
    config_hash: str
    keyframes: list[GestureKeyframe]


class BoundaryCandidate(Artifact):
    t: float
    frame: int
    score: float = Field(ge=0, le=1)
    reasons: list[str] = Field(description="scene_cut, hand_state_change, motion_pause, narration_pause, hands_enter, hands_exit")


class ActivitySample(Artifact):
    t: float
    motion_energy: float
    hands_visible: int


class Candidates(Artifact):
    """candidates/candidates.json"""

    boundaries: list[BoundaryCandidate]
    activity: list[ActivitySample]
