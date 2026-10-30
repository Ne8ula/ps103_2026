"""LLM output schemas for the compliance stage and the citation guardrail.

The schemas are OpenAI structured-output friendly: every field required, no dicts, flat lists.
``validate_notes`` keeps only what the documents support:

- a citation must name a chunk that was actually shown to the model and quote it verbatim
  (whitespace/case-insensitive);
- a note left without citations is dropped;
- a note whose text contains a number that appears neither in its cited chunks nor in the video
  steps is dropped (the model must not invent numeric values).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from ..schemas.compliance import Citation, ComplianceNote, DocChunk
from .text import numbers, quote_in_text

Severity = Literal["info", "warning", "critical"]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class QuoteRef(_Strict):
    chunk_id: str = Field(description="id of a provided chunk, exactly as labelled, e.g. d01:12")
    quote: str = Field(description="verbatim excerpt copied from that chunk (one sentence or clause)")


class StepNoteDraft(_Strict):
    kind: Literal["requirement", "caution", "conflict", "reference"]
    severity: Severity
    text: str = Field(description="one or two sentences addressed to the person doing the step")
    citations: list[QuoteRef]


class StepNotesOutput(_Strict):
    """Task 'compliance_step'."""

    notes: list[StepNoteDraft]


class MissingStepDraft(_Strict):
    after_step_id: str | None = Field(description="step id the missing step belongs after; null if it belongs first")
    severity: Severity
    text: str = Field(description="the required step that the video does not show, and why it matters")
    citations: list[QuoteRef]


class MissingStepsOutput(_Strict):
    """Task 'compliance_missing_steps'."""

    notes: list[MissingStepDraft]


@dataclass
class ValidationResult:
    notes: list[ComplianceNote] = field(default_factory=list)
    dropped: list[str] = field(default_factory=list)


def validate_notes(drafts: list[StepNoteDraft | MissingStepDraft], chunks: list[DocChunk], step_id: str | None,
                   id_prefix: str, allowed_numbers_text: str, llm_call: str | None = None,
                   min_quote_chars: int = 12) -> ValidationResult:
    """Map LLM drafts to ComplianceNotes, dropping anything not grounded in the given chunks."""
    by_id = {c.id: c for c in chunks}
    out = ValidationResult()
    for n, draft in enumerate(drafts, start=1):
        where = f"{id_prefix} draft {n}"
        citations: list[Citation] = []
        for ref in draft.citations:
            chunk = by_id.get(ref.chunk_id.strip().strip("[]"))
            if chunk is None:
                out.dropped.append(f"{where}: citation to '{ref.chunk_id}' which was not retrieved")
            elif not quote_in_text(ref.quote, chunk.text, min_quote_chars):
                out.dropped.append(f"{where}: quote not found in {chunk.id}: {ref.quote[:80]!r}")
            elif all(c.chunk_id != chunk.id or c.quote != ref.quote for c in citations):
                citations.append(Citation(chunk_id=chunk.id, doc_name=chunk.doc_name, page=chunk.page, quote=ref.quote.strip()))
        if not citations:
            out.dropped.append(f"{where}: no valid citations; note dropped: {draft.text[:80]!r}")
            continue
        grounded = numbers(allowed_numbers_text) | set().union(*(numbers(by_id[c.chunk_id].text) for c in citations))
        invented = numbers(draft.text) - grounded
        if invented:
            out.dropped.append(f"{where}: numbers {sorted(invented)} not in the cited chunks or the steps; note dropped")
            continue
        kind = "missing_step" if isinstance(draft, MissingStepDraft) else draft.kind
        out.notes.append(ComplianceNote(
            id=f"{id_prefix}-{len(out.notes) + 1}", step_id=step_id, kind=kind, severity=draft.severity,
            text=draft.text.strip(), citations=citations, llm_call=llm_call,
            after_step_id=draft.after_step_id if isinstance(draft, MissingStepDraft) else None,
        ))
    return out
