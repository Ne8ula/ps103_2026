"""Shared building blocks for every stage artifact."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

SCHEMA_VERSION = 1


class Artifact(BaseModel):
    """Base for anything written to a project folder. Unknown fields are rejected."""

    model_config = ConfigDict(extra="forbid")


class TimeRange(Artifact):
    start: float = Field(ge=0, description="seconds")
    end: float = Field(ge=0, description="seconds")


class Provenance(Artifact):
    """Where a generated statement came from. Every step and note carries one."""

    time_ranges: list[TimeRange] = []
    gesture_keyframe_ids: list[str] = []
    transcript_segment_ids: list[int] = []
    chunk_ids: list[str] = []
    answer_ids: list[str] = []
    llm_calls: list[str] = Field(default=[], description="LLM cache keys used to produce this item")
