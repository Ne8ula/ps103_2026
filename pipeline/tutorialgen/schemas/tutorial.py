"""Stage 9 artifact: the final tutorial package. Owner: render workstream."""

from __future__ import annotations

from pydantic import Field

from .common import Artifact
from .compliance import ComplianceNote
from .steps import Question, Step


class TutorialStep(Artifact):
    step: Step
    compliance: list[ComplianceNote] = []
    gesture_keyframe_ids: list[str] = []
    clip_path: str | None = Field(default=None, description="per-step clip with overlay, relative to project root")


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
    artifacts: dict[str, str] = Field(default={}, description="name -> path relative to project root (video, landmarks, gestures, transcript, ...)")
