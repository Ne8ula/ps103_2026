"""Stage 4-5, 7-8 artifacts: segmentation, drafted steps, questions, answers. Owner: LLM workstream."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from .common import Artifact, Provenance


class StepSegment(Artifact):
    id: str = Field(description="s01 ...")
    start: float
    end: float
    summary: str
    rationale: str
    confidence: float = Field(ge=0, le=1)
    llm_calls: list[str] = Field(default=[], description="LLM cache keys of the window call(s) that proposed this segment")


class Segmentation(Artifact):
    """segment/segments.json"""

    segments: list[StepSegment]
    notes: list[str] = []
    content_start: float | None = Field(default=None, description="start of the covered range (after leading idle)")
    content_end: float | None = Field(default=None, description="end of the covered range (before trailing idle)")


class MissingInfo(Artifact):
    field: Literal["tool", "material", "quantity", "setting", "duration", "purpose", "safety", "order", "outcome", "other"]
    description: str
    blocking: bool
    key: str | None = Field(default=None, description="stable gap key, e.g. s03:missing:duration; questions map it to a stable question id")


class Step(Artifact):
    id: str
    index: int
    start: float
    end: float
    title: str
    instruction: str
    details: list[str] = []
    tools: list[str] = []
    materials: list[str] = []
    expected_result: str | None = None
    cautions: list[str] = []
    confidence: float = Field(ge=0, le=1)
    missing_info: list[MissingInfo] = []
    user_supplied: list[str] = Field(default=[], description="facts that came from uploader answers")
    keyframe_paths: list[str] = Field(default=[], description="images relative to project root")
    provenance: Provenance = Provenance()


class ProcedureNote(Artifact):
    """A whole-procedure fact from an uploader answer that no single step could absorb."""

    text: str
    question_id: str | None = None
    answer_ids: list[str] = []


class AppliedAnswer(Artifact):
    """Record of one answer merged by refine; (answer_id, text) detects a replaced answer."""

    answer_id: str
    question_id: str
    text: str
    step_id: str | None = Field(description="step it was merged into; None = recorded as a procedure note")
    revision: int


class StepList(Artifact):
    """draft/steps.json (revision 0) and refine/steps.json (revision >= 0)"""

    revision: int
    steps: list[Step]
    applied_answer_ids: list[str] = []
    notes: list[ProcedureNote] = []
    answer_log: list[AppliedAnswer] = []
    base_hash: str | None = Field(default=None, description="refine only: hash of the draft it was built on")


class Question(Artifact):
    id: str = Field(description="q001 ...; stable across rounds for the same underlying gap")
    step_id: str | None
    kind: Literal["missing_info", "low_confidence", "sop_conflict", "sop_missing_step", "clarify_order", "other"]
    text: str
    why: str
    answer_type: Literal["free_text", "yes_no", "choice", "number"] = "free_text"
    choices: list[str] = []
    priority: int = Field(ge=1, le=3, description="1 = most important")
    blocking: bool
    status: Literal["open", "answered", "dismissed"] = "open"
    source_refs: list[str] = Field(default=[], description="missing_info / compliance note ids that raised it")


class QuestionSet(Artifact):
    """questions/questions.json"""

    round: int
    questions: list[Question]


class Answer(Artifact):
    id: str
    question_id: str
    text: str
    created_at: str


class AnswerSet(Artifact):
    """inputs/answers.json — an input, written by the CLI/API, never by a stage."""

    answers: list[Answer] = []
