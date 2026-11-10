"""Edit stage artifact: what to keep, speed up or cut inside each step. Owner: edit stage; read by render."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from .common import Artifact

UnitLabel = Literal["task", "result", "explain", "aside", "idle"]


class EditUnit(Artifact):
    """A stretch of one step: a spoken line (cut at word boundaries) or the gap between lines."""

    id: str = Field(description="<step id>-u<n>, e.g. s03-u04")
    start: float
    end: float
    kind: Literal["speech", "gap"]
    text: str | None = None
    hands: float = Field(description="fraction of hand samples in the unit with a hand detected")
    motion: float = Field(description="pixel motion in the frame, normalized to this video (about 0..1)")
    label: UnitLabel
    label_source: Literal["llm", "rule", "default"]
    action: Literal["keep", "speed", "cut"]
    speed: float = Field(default=1.0, description="playback factor for action 'speed'")
    reason: str
    restored_by: str | None = Field(default=None, description="guard that turned a cut back into a keep")


class StepEdit(Artifact):
    step_id: str
    source_s: float
    output_s: float = Field(description="seconds this step's clip lasts after cuts and speed-ups")
    units: list[EditUnit]


class EditDecisionList(Artifact):
    """edit/edl.json"""

    version: str
    enabled: bool
    source_s: float = Field(description="sum of the steps' source durations")
    output_s: float = Field(description="sum of the steps' clip durations after editing (cards excluded)")
    steps: list[StepEdit]
    llm_calls: list[str] = []
