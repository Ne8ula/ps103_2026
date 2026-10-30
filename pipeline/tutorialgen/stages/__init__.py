"""Stage registry. Order matters: it is the default execution order.

Every stage is ``run(ctx: StageContext) -> None``: it reads upstream artifacts from the project and
writes its own outputs. Stages are pure functions of files, so heavy ones (``gpu=True``) can later
be dispatched to a remote GPU worker without code changes.

Answer loop: after the uploader answers questions, re-running from ``refine`` merges the answers
into the steps, then ``compliance`` and ``questions`` refresh, then ``render``.
"""

from __future__ import annotations

import importlib
import logging
from dataclasses import dataclass, field
from typing import Callable

from ..config import Config
from ..llm import CachedLLM
from ..project import Project


@dataclass
class StageContext:
    project: Project
    config: Config
    llm: CachedLLM
    log: logging.Logger


@dataclass(frozen=True)
class StageSpec:
    name: str
    module: str
    requires: tuple[str, ...]
    outputs: tuple[str, ...]           # project-relative files or dirs; hashed to detect change
    config_sections: tuple[str, ...]   # config sections that affect the result
    inputs: tuple[str, ...] = ()       # project inputs (e.g. inputs/answers.json, inputs/documents)
    uses_llm: bool = False
    gpu: bool = False
    description: str = ""

    def load(self) -> Callable[[StageContext], None]:
        return importlib.import_module(f"tutorialgen.stages.{self.module}").run


STAGES: dict[str, StageSpec] = {
    s.name: s
    for s in [
        StageSpec("ingest", "ingest", (), ("ingest/meta.json",), ("ingest",),
                  description="download/copy and normalize the video, extract audio"),
        StageSpec("perception", "perception", ("ingest",), ("hands/frames.jsonl", "hands/summary.json", "hands/scenes.json"),
                  ("perception", "device"), gpu=True, description="MediaPipe hand landmarks, smoothing, scene cuts"),
        StageSpec("transcribe", "transcribe", ("ingest",), ("transcript/transcript.json",),
                  ("transcribe", "device"), gpu=True, description="Whisper transcript of narration, if any"),
        StageSpec("gestures", "gestures", ("perception",), ("gestures/gestures.json",),
                  ("gestures",), description="GestLLM-style landmark -> gesture text at keyframes"),
        StageSpec("candidates", "candidates", ("perception", "transcribe", "gestures"), ("candidates/candidates.json",),
                  ("candidates",), description="heuristic step-boundary candidates"),
        StageSpec("segment", "segment", ("ingest", "perception", "transcribe", "gestures", "candidates"),
                  ("segment/segments.json", "segment/keyframes"), ("segment", "llm", "use_gesture_text", "gestures"), uses_llm=True, description="LLM groups the video into steps"),
        StageSpec("draft", "draft", ("segment", "perception", "transcribe", "gestures"), ("draft/steps.json",),
                  ("draft", "llm", "use_gesture_text", "gestures", "focus"), uses_llm=True, description="LLM drafts each step with missing-info flags"),
        StageSpec("refine", "refine", ("draft",), ("refine/steps.json",),
                  ("refine", "llm"), inputs=("inputs/answers.json",), uses_llm=True,
                  description="merge uploader answers into affected steps"),
        StageSpec("compliance", "compliance", ("refine",), ("compliance/compliance.json", "compliance/index"),
                  ("compliance", "embeddings", "llm"), inputs=("inputs/documents",), uses_llm=True,
                  description="RAG over SOPs/manuals: cited notes, conflicts, missing steps"),
        StageSpec("questions", "questions", ("refine", "compliance"), ("questions/questions.json",),
                  ("questions", "llm"), inputs=("inputs/answers.json",), uses_llm=True,
                  description="turn gaps into prioritized questions for the uploader"),
        StageSpec("render", "render", ("refine", "compliance", "questions", "perception", "gestures"),
                  ("render/tutorial.json", "render/tutorial.mp4", "render/tutorial.md"),
                  ("render", "device", "focus", "gestures"), gpu=True, description="tutorial video with hand overlays + text cards, tutorial.json"),
    ]
}

ORDER = list(STAGES)
