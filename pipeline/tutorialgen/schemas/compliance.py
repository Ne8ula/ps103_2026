"""Stage 6 artifacts: document index and cited compliance notes. Owner: RAG workstream."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from .common import Artifact


class DocumentInfo(Artifact):
    id: str
    name: str
    path: str = Field(description="relative to project root")
    pages: int | None = None
    chunks: int


class DocChunk(Artifact):
    id: str = Field(description="<doc_id>:<n>")
    doc_id: str
    doc_name: str
    page: int | None = None
    page_end: int | None = Field(default=None, description="last page when the chunk spans pages")
    section: str | None = None
    text: str


class DocIndex(Artifact):
    """compliance/index/chunks.json (embeddings sit next to it as embeddings.npy)"""

    embedding_model: str
    documents: list[DocumentInfo]
    chunks: list[DocChunk]


class Citation(Artifact):
    chunk_id: str
    doc_name: str
    page: int | None = None
    quote: str = Field(description="verbatim excerpt of the chunk supporting the note")


class ComplianceNote(Artifact):
    id: str
    step_id: str | None = Field(description="None for whole-procedure notes, e.g. a missing step")
    kind: Literal["requirement", "caution", "conflict", "missing_step", "reference"]
    severity: Literal["info", "warning", "critical"]
    text: str
    citations: list[Citation] = Field(min_length=1)
    after_step_id: str | None = Field(default=None, description="missing_step only: where the step belongs")
    llm_call: str | None = Field(default=None, description="LLM cache key that produced the note")


class StepCompliance(Artifact):
    step_id: str
    notes: list[ComplianceNote] = []
    no_relevant_guidance: bool
    retrieved_chunk_ids: list[str] = []
    query: str | None = Field(default=None, description="retrieval query built from the step")


class ComplianceReport(Artifact):
    """compliance/compliance.json"""

    documents: list[DocumentInfo]
    steps: list[StepCompliance]
    global_notes: list[ComplianceNote] = []
    embedding_model: str | None = None
    dropped: list[str] = Field(default=[], description="LLM notes/citations rejected by validation, and why")
