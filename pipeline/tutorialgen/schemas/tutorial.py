"""Stage 9 artifact: the final tutorial package. Owner: render workstream."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from .common import Artifact
from .compliance import ComplianceNote
from .steps import ProcedureNote, Question, Step


class Callout(Artifact):
    """An on-screen chip shown during part of a step clip."""

    kind: Literal["emphasis", "safety", "items"]
    text: str
    start: float
    end: float
    severity: Literal["info", "warning", "critical"] = "info"
    note_id: str | None = Field(default=None, description="safety: the ComplianceNote id it shows")
    substep: int | None = Field(default=None, description="index into step.substeps it belongs to")


class CropSegment(Artifact):
    """The crop rendered for one stretch of a step clip (one sub-step within one shot)."""

    start: float
    end: float
    rect: list[float] = Field(description="[x0, y0, x1, y1] normalized source crop; [0, 0, 1, 1] = full frame")
    focus: str = Field(description="requested FocusBox id or 'full'")
    reason: str = Field(description="why this rect: box id used, or why it fell back to the full frame")
    cut_before: bool = Field(default=False, description="a scene cut (or the clip start) precedes it: no pan into it")


class TutorialStep(Artifact):
    step: Step
    compliance: list[ComplianceNote] = []
    gesture_keyframe_ids: list[str] = []
    clip_path: str | None = Field(default=None, description="per-step clip with overlay, relative to project root")
    callouts: list[Callout] = []
    crop_plan: list[CropSegment] = []


class Tutorial(Artifact):
    """render/tutorial.json"""

    project_id: str
    title: str
    source: str
    revision: int
    generated_at: str
    llm: str = Field(description="provider:model that produced the text")
    steps: list[TutorialStep]
    global_notes: list[ComplianceNote] = []
    open_questions: list[Question] = []
    procedure_notes: list[ProcedureNote] = Field(default=[], description="whole-procedure facts from uploader answers (refine)")
    artifacts: dict[str, str] = Field(default={}, description="name -> path relative to project root (video, landmarks, gestures, transcript, ...)")
