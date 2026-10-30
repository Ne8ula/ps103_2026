"""LLM output schemas for the compliance stage, structured LLM context, and the citation guardrail.

Context: every chunk is shown as a record (id, document, pages, section) with its text split into
numbered sentences ``[S1] ...``. The model cites ``(chunk_id, sentence_ids)``; the code checks the ids
and derives the verbatim quote itself, so a citation can never misquote its source.

The output schemas are OpenAI/Gemini strict-structured-output friendly: every field required,
``X | None`` instead of defaults, no dict fields, no unions of objects.

Guardrails (``validate_findings`` / ``resolve_citations``):

- a citation must name a chunk that was shown and sentence ids that exist in it (and, for chunks
  shown only as selected sentences, one of those sentences);
- a note left without valid citations is dropped;
- a number in the note text must appear in its cited chunks, the video steps, or the chunk labels;
- a number in ``sop_value`` must appear in the cited *sentences*, and a number in ``video_value`` in
  the step; otherwise the note is dropped (the model must not invent numeric values).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from ..schemas.compliance import Citation, ComplianceNote, DocChunk
from .text import numbers, sentences

Severity = Literal["info", "warning", "critical"]
RequirementType = Literal["order", "duration", "temperature", "quantity", "equipment", "material", "technique",
                          "prohibition", "hygiene", "timing", "other"]
StepField = Literal["instruction", "tools", "materials", "duration", "temperature", "quantity", "order", "cautions",
                    "whole_step"]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SentenceRef(_Strict):
    chunk_id: str = Field(description="id of a provided chunk, exactly as labelled, e.g. d01:12")
    sentence_ids: list[int] = Field(description="numbers of the cited sentences in that chunk, e.g. [3, 4] for [S3] [S4]")


class StepFinding(_Strict):
    citations: list[SentenceRef] = Field(description="the sentences the finding rests on; cite before you write")
    kind: Literal["requirement", "caution", "conflict", "reference"]
    requirement_type: RequirementType
    step_field: StepField = Field(description="which part of the video step the finding applies to")
    sop_value: str | None = Field(description="the specific requirement as worded in the cited sentences (e.g. "
                                              "'at least 20 seconds', 'single-use paper towel'); null if none")
    video_value: str | None = Field(description="conflict only: what the video step shows instead, worded as in "
                                                "the step (e.g. '5 seconds'); null otherwise")
    severity: Severity
    text: str = Field(description="one or two sentences addressed to the person doing the step")


class StepFindingsOutput(_Strict):
    """Task 'compliance_step'."""

    findings: list[StepFinding]


class SopStepDraft(_Strict):
    citations: list[SentenceRef]
    action: str = Field(description="the step as the document states it, as a short imperative")
    mandatory: bool = Field(description="true if the document requires it (shall/must), false if recommended")


class SopProcedureOutput(_Strict):
    """Task 'compliance_sop_procedure'."""

    title: str | None = Field(description="name of the procedure in the documents, null if none applies")
    steps: list[SopStepDraft] = Field(description="the document's procedure steps, in the order it states them")


class SopStepCoverage(_Strict):
    sop_step: str = Field(description="id of the document procedure step, e.g. P3")
    video_step_ids: list[str] = Field(description="ids of the video steps that perform it; empty if none")
    status: Literal["covered", "partly_covered", "missing"]
    after_step_id: str | None = Field(description="missing only: id of the video step it should follow; null if "
                                                  "it belongs before the first step or is not missing")
    severity: Severity
    text: str = Field(description="missing only: the step the video does not show and why it matters; else ''")


class ProcedureCoverageOutput(_Strict):
    """Task 'compliance_missing_steps'."""

    coverage: list[SopStepCoverage]


# ---- structured context ------------------------------------------------------------------------


_BARE_NUMBER = re.compile(r"^(?:\d{1,3}(?:[.-]\d{1,3})*\.?|\(?[A-Za-z0-9]{1,3}[.)]|¶|§)$")


def chunk_sentences(chunk: DocChunk) -> list[str]:
    """Numbered sentences of a chunk (1-based ids are positions in this list). Each is a verbatim
    substring modulo whitespace; a bare section number ("3.") is kept with the text that follows it."""
    out: list[str] = []
    carry = ""
    for s in sentences(chunk.text):
        if _BARE_NUMBER.match(s):
            carry = f"{carry} {s}".strip()
            continue
        out.append(f"{carry} {s}".strip() if carry else s)
        carry = ""
    if carry:
        out.append(carry)
    return out


def chunk_label(c: DocChunk) -> str:
    where = []
    if c.page is not None:
        where.append(f"p. {c.page}" + (f"-{c.page_end}" if c.page_end else ""))
    if c.section:
        where.append(c.section)
    return f"[{c.id}] {c.doc_name}" + (f" ({', '.join(where)})" if where else "")


def format_chunk(c: DocChunk, only: set[int] | None = None) -> str:
    """A chunk as a record with numbered sentences; ``only`` shows just those sentence ids."""
    pages = "" if c.page is None else f'{c.page}{f"-{c.page_end}" if c.page_end else ""}'
    head = f'<chunk id="{c.id}" document="{c.doc_name}" pages="{pages}" section="{c.section or ""}">'
    lines = [f"[S{n}] {s}" for n, s in enumerate(chunk_sentences(c), start=1) if only is None or n in only]
    return "\n".join([head, *lines, "</chunk>"])


@dataclass
class Shown:
    """What the model was shown: chunk id -> chunk, and per chunk the sentence ids visible (None = all)."""

    chunks: dict[str, DocChunk] = field(default_factory=dict)
    visible: dict[str, set[int] | None] = field(default_factory=dict)

    def add(self, chunk: DocChunk, only: set[int] | None = None) -> None:
        self.chunks[chunk.id] = chunk
        prev = self.visible.get(chunk.id, set())
        self.visible[chunk.id] = None if only is None or prev is None else prev | only

    def labels_text(self) -> str:
        """Chunk labels (page and section numbers) are shown to the model, so their numbers are grounded."""
        return " ".join(chunk_label(c) for c in self.chunks.values())


@dataclass
class Resolved:
    citations: list[Citation]
    sentences: list[str]          # cited sentence texts (for value checks)
    errors: list[str]


def resolve_citations(refs: list[SentenceRef], shown: Shown) -> Resolved:
    """Check (chunk, sentence id) references and build verbatim Citations, one per run of consecutive
    sentences. Invalid references are reported, valid ones kept."""
    out = Resolved([], [], [])
    seen: set[tuple[str, int]] = set()
    for ref in refs:
        cid = ref.chunk_id.strip().strip("[]")
        chunk = shown.chunks.get(cid)
        if chunk is None:
            out.errors.append(f"citation to '{ref.chunk_id}' which was not shown")
            continue
        sents = chunk_sentences(chunk)
        visible = shown.visible.get(cid)
        ok = []
        for sid in ref.sentence_ids:
            if not 1 <= sid <= len(sents) or (visible is not None and sid not in visible):
                out.errors.append(f"citation to sentence S{sid} of {cid}, which was not shown")
            elif (cid, sid) not in seen:
                seen.add((cid, sid))
                ok.append(sid)
        if not ok and not ref.sentence_ids:
            out.errors.append(f"citation to {cid} without sentence ids")
        for run in _runs(sorted(ok)):
            text = " ".join(sents[i - 1] for i in run)
            out.citations.append(Citation(chunk_id=cid, doc_name=chunk.doc_name, page=chunk.page, quote=text,
                                          sentence_ids=run))
            out.sentences += [sents[i - 1] for i in run]
    return out


def _runs(ids: list[int]) -> list[list[int]]:
    runs: list[list[int]] = []
    for i in ids:
        if runs and i == runs[-1][-1] + 1:
            runs[-1].append(i)
        else:
            runs.append([i])
    return runs


@dataclass
class ValidationResult:
    notes: list[ComplianceNote] = field(default_factory=list)
    dropped: list[str] = field(default_factory=list)
    proposed_citations: int = 0
    invalid_citations: int = 0


def validate_findings(findings: list[StepFinding], shown: Shown, step_id: str, step_text: str,
                      llm_call: str | None = None) -> ValidationResult:
    """Map LLM findings to ComplianceNotes, dropping anything not grounded in what was shown."""
    out = ValidationResult()
    prefix = f"c-{step_id}"
    for n, f in enumerate(findings, start=1):
        where = f"{prefix} finding {n}"
        res = resolve_citations(f.citations, shown)
        out.proposed_citations += len(f.citations)
        out.invalid_citations += len(res.errors)
        out.dropped += [f"{where}: {e}" for e in res.errors]
        if not res.citations:
            out.dropped.append(f"{where}: no valid citations; note dropped: {f.text[:80]!r}")
            continue
        cited_chunks = " ".join(shown.chunks[c.chunk_id].text for c in res.citations)
        grounded = numbers(step_text) | numbers(shown.labels_text()) | numbers(cited_chunks)
        if invented := numbers(f.text) - grounded:
            out.dropped.append(f"{where}: numbers {sorted(invented)} not in the cited chunks or the steps; note dropped")
            continue
        if f.sop_value and (bad := numbers(f.sop_value) - numbers(" ".join(res.sentences))):
            out.dropped.append(f"{where}: sop_value numbers {sorted(bad)} not in the cited sentences; note dropped")
            continue
        if f.video_value and (bad := numbers(f.video_value) - numbers(step_text)):
            out.dropped.append(f"{where}: video_value numbers {sorted(bad)} not in the step; note dropped")
            continue
        out.notes.append(ComplianceNote(
            id=f"{prefix}-{len(out.notes) + 1}", step_id=step_id, kind=f.kind, severity=f.severity,
            text=f.text.strip(), citations=res.citations, llm_call=llm_call,
            requirement_type=f.requirement_type, step_field=f.step_field,
            sop_value=(f.sop_value or "").strip() or None,
            video_value=((f.video_value or "").strip() or None) if f.kind == "conflict" else None,
        ))
    return out
