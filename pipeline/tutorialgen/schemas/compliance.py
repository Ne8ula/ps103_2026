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
    sentence_ids: list[int] = Field(default=[], description="1-based sentence numbers in the chunk the quote is made of")


class ComplianceNote(Artifact):
    id: str
    step_id: str | None = Field(description="None for whole-procedure notes, e.g. a missing step")
    kind: Literal["requirement", "caution", "conflict", "missing_step", "reference"]
    severity: Literal["info", "warning", "critical"]
    text: str
    citations: list[Citation] = Field(min_length=1)
    after_step_id: str | None = Field(default=None, description="missing_step only: where the step belongs")
    llm_call: str | None = Field(default=None, description="LLM cache key that produced the note")
    requirement_type: str | None = Field(default=None, description="order | duration | temperature | quantity | "
                                         "equipment | material | technique | prohibition | hygiene | timing | other")
    step_field: str | None = Field(default=None, description="part of the step the note applies to (instruction, "
                                   "tools, materials, duration, temperature, quantity, order, cautions, whole_step)")
    sop_value: str | None = Field(default=None, description="the requirement as worded in the cited sentences")
    video_value: str | None = Field(default=None, description="conflict only: what the video step shows instead")
    sop_step_id: str | None = Field(default=None, description="missing_step only: the SOP procedure step (P1...) not shown")


class SopProcedureStep(Artifact):
    """One step of the procedure as the documents state it (extracted by the LLM, citations checked)."""

    id: str = Field(description="P1, P2 ... in document order")
    action: str
    mandatory: bool
    citations: list[Citation] = Field(min_length=1)
    video_step_ids: list[str] = Field(default=[], description="video steps that perform it (coverage check)")
    status: Literal["covered", "partly_covered", "missing", "unchecked"] = "unchecked"


class StepCompliance(Artifact):
    step_id: str
    notes: list[ComplianceNote] = []
    no_relevant_guidance: bool
    retrieved_chunk_ids: list[str] = []
    query: str | None = Field(default=None, description="retrieval query built from the step")
    context_chunk_ids: list[str] = Field(default=[], description="every chunk shown to the LLM for this step: "
                                         "retrieved chunks, neighbours, and chunks of the SOP procedure steps")
    sop_step_ids: list[str] = Field(default=[], description="SOP procedure steps this video step performs")


class ComplianceReport(Artifact):
    """compliance/compliance.json"""

    documents: list[DocumentInfo]
    steps: list[StepCompliance]
    global_notes: list[ComplianceNote] = []
    embedding_model: str | None = None
    dropped: list[str] = Field(default=[], description="LLM notes/citations rejected by validation, and why")
    sop_procedure: list[SopProcedureStep] = Field(default=[], description="the documents' ordered procedure, "
                                                  "extracted from the procedure chunks; basis of the missing-step check")
    sop_procedure_title: str | None = None
    procedure_chunk_ids: list[str] = Field(default=[], description="chunks retrieved for the whole procedure")
    citation_stats: dict[str, int] = Field(default={}, description="proposed / invalid citations across LLM calls")
