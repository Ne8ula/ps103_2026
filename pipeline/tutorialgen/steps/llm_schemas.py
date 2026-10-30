"""Structured-output schemas for the LLM tasks of segment, draft, refine and questions.

Kept OpenAI structured-output friendly: every field is required (optional values are ``X | None``),
no dict fields, no numeric constraints (values are clamped in code), shallow nesting. These are
what the model returns; stages turn them into the artifact schemas in ``schemas/steps.py`` and fill
ids, times and provenance themselves.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

MissingField = Literal["tool", "material", "quantity", "setting", "duration", "purpose", "safety", "order", "outcome", "other"]


class _Out(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ---- segment_steps ------------------------------------------------------------------------------


class ProposedStep(_Out):
    start_s: float = Field(description="step start in seconds; use one of the listed boundary times")
    end_s: float = Field(description="step end in seconds; use one of the listed boundary times")
    summary: str = Field(description="one sentence: what the person does in this step")
    rationale: str = Field(description="why the step starts and ends here (speech, hand state, image change)")
    confidence: float = Field(description="0-1: how sure you are about these boundaries")


class SegmentWindowOutput(_Out):
    steps: list[ProposedStep] = Field(description="consecutive steps in time order inside the window")
    notes: list[str] = Field(description="observations worth surfacing, e.g. ambiguous boundaries; may be empty")


# ---- draft_step ---------------------------------------------------------------------------------


class MissingItem(_Out):
    field: MissingField
    description: str = Field(description="what exactly is unknown, phrased as the fact a learner would need")
    blocking: bool = Field(description="true if a learner could not perform the step safely or correctly without it")


class SubStepOutput(_Out):
    start_s: float = Field(description="start of this action phase; use one of the listed anchor times")
    caption: str = Field(description="on-screen caption, imperative, at most ~6 words")
    focus_box: str = Field(description="id of the focus box to zoom to during this phase (e.g. B2), or 'full'")
    emphasis: str | None = Field(description="optional 1-3 word callout of the spot to watch (e.g. 'between fingers'), else null")
    emphasis_s: float | None = Field(description="when the emphasis applies, seconds; null if no emphasis")


class DraftStepOutput(_Out):
    title: str = Field(description="short imperative title, max ~8 words")
    instruction: str = Field(description="one or two imperative sentences")
    details: list[str]
    tools: list[str]
    materials: list[str]
    expected_result: str | None
    cautions: list[str]
    confidence: float = Field(description="0-1: how well the evidence supports this description")
    missing_info: list[MissingItem]
    substeps: list[SubStepOutput] = Field(description="1-4 consecutive action phases in time order; the first starts at the step start")


# ---- refine_step --------------------------------------------------------------------------------


class RefineStepOutput(_Out):
    title: str
    instruction: str
    details: list[str]
    tools: list[str]
    materials: list[str]
    expected_result: str | None
    cautions: list[str]
    confidence: float
    user_supplied: list[str] = Field(description="complete list of facts that come from uploader answers")
    resolved_missing_keys: list[str] = Field(description="keys of missing-info items the answers resolve")
    new_missing_info: list[MissingItem] = Field(description="new gaps the answers reveal; usually empty")


# ---- questions ----------------------------------------------------------------------------------


class PhrasedQuestion(_Out):
    gap_keys: list[str] = Field(description="keys of the gaps this question covers (several if they are duplicates)")
    text: str = Field(description="the question for the uploader, plain language, one sentence")
    why: str = Field(description="why the answer matters for the tutorial")
    answer_type: Literal["free_text", "yes_no", "choice", "number"]
    choices: list[str] = Field(description="options when answer_type is choice; otherwise empty")
    priority: int = Field(description="1 = most important, 3 = nice to have")


class QuestionsOutput(_Out):
    questions: list[PhrasedQuestion]
