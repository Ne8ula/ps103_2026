"""Request and response bodies that are API-only. Artifact responses reuse ``tutorialgen.schemas``."""

from __future__ import annotations

from pydantic import BaseModel, Field

from ..project import Manifest, VideoInput


class CreateProject(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    video_url: str | None = Field(default=None, description="http(s) URL, e.g. YouTube")


class VideoUrl(BaseModel):
    url: str = Field(description="http(s) URL, e.g. YouTube")


class ProjectSummary(BaseModel):
    id: str
    name: str
    created_at: str
    video: VideoInput | None
    documents: int
    stages: dict[str, str] = Field(description="stage -> pending | running | done | failed")
    active_run_id: str | None = None


class ProjectDetail(Manifest):
    active_run_id: str | None = None


class AnswerRequest(BaseModel):
    question_id: str
    text: str = Field(min_length=1)


class StageInfo(BaseModel):
    name: str
    requires: list[str]
    outputs: list[str]
    inputs: list[str]
    uses_llm: bool
    gpu: bool
    description: str


class Health(BaseModel):
    status: str = "ok"
    version: str
    active_runs: int
