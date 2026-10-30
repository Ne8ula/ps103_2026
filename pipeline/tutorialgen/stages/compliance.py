"""Stage 'compliance': RAG over the uploader's SOPs/manuals -> cited notes per step + missing steps.

refine/steps.json + inputs/documents -> compliance/index/ (chunks.json, embeddings.npy, manifest.json)
                                     -> compliance/compliance.json (ComplianceReport)

Per step: hybrid retrieval (BM25 + embeddings, RRF) -> one LLM call ("compliance_step") -> notes
whose citations are checked against the retrieved chunks (rag.notes.validate_notes). Whole
procedure: one LLM call ("compliance_missing_steps") for SOP-required steps the video never shows.
A step with no surviving note is marked ``no_relevant_guidance``.
"""

from __future__ import annotations

import re
import time

from pydantic import BaseModel

from ..llm import LLMRequest, fake_handler
from ..prompts import load_prompt
from ..rag import (
    DocSource, EmbeddingSettings, Hit, HybridRetriever, MissingStepDraft, MissingStepsOutput, QuoteRef,
    StepNoteDraft, StepNotesOutput, load_or_build_index, make_embedder, procedure_query, step_query, validate_notes,
)
from ..rag.text import sentences, tokenize
from ..schemas.compliance import ComplianceReport, DocChunk, StepCompliance
from ..schemas.steps import Step, StepList
from . import StageContext

INDEX_DIR = "compliance/index"
REPORT = "compliance/compliance.json"


class ComplianceSettings(BaseModel):
    top_k: int = 6                      # chunks retrieved per step and sent to the LLM
    missing_steps_top_k: int = 8        # chunks for the whole-procedure missing-step check
    check_missing_steps: bool = True
    rrf_k: int = 60                     # reciprocal-rank-fusion constant
    candidate_pool: int = 50            # per-retriever depth before fusion
    chunk_words: int = 300              # max words per chunk (~400 tokens)
    chunk_overlap_words: int = 40
    min_chunk_words: int = 60           # smaller sections are merged into the next one
    min_quote_chars: int = 12           # shorter "quotes" do not count as citations
    strip_priority_markers: bool = True  # FDA Food Code "P"/"Pf" markers after clauses


def run(ctx: StageContext) -> None:
    s = ctx.config.section("compliance", ComplianceSettings)
    steps = ctx.project.read("refine/steps.json", StepList).steps
    docs = ctx.project.manifest.documents

    if not docs:
        ctx.log.info("no reference documents: every step gets no_relevant_guidance")
        for stale in ("chunks.json", "embeddings.npy"):
            ctx.project.path(f"{INDEX_DIR}/{stale}").unlink(missing_ok=True)
        ctx.project.write_json(f"{INDEX_DIR}/manifest.json", {"documents": [], "embedding_model": None})
        ctx.project.write(REPORT, ComplianceReport(
            documents=[], steps=[StepCompliance(step_id=st.id, no_relevant_guidance=True) for st in steps]))
        return

    embedder = make_embedder(ctx.config.section("embeddings", EmbeddingSettings))
    sources = [DocSource(d.id, d.name, ctx.project.path(d.path), d.path, d.sha) for d in docs]
    t0 = time.perf_counter()
    index = load_or_build_index(ctx.project.path(INDEX_DIR), sources, embedder, s.chunk_words,
                                s.chunk_overlap_words, s.min_chunk_words, s.strip_priority_markers)
    ctx.log.info("index %s: %d chunks in %.1fs", "built" if index.rebuilt else "reused", len(index.chunks), time.perf_counter() - t0)

    retriever = HybridRetriever(index, embedder, s.rrf_k, s.candidate_pool)
    queries = [step_query(st) for st in steps]
    hits_per_step = retriever.search(queries, s.top_k)
    dropped: list[str] = []

    step_prompt = load_prompt("compliance_step")
    results = []
    for st, query, hits in zip(steps, queries, hits_per_step):
        chunks = [h.chunk for h in hits]
        notes = []
        if chunks:
            req = LLMRequest(
                task="compliance_step", system=step_prompt.system, schema=StepNotesOutput,
                user=step_prompt.render(
                    step_id=st.id, title=st.title, instruction=st.instruction,
                    details="; ".join(st.details) or "none", tools=", ".join(st.tools + st.materials) or "none",
                    cautions="; ".join(st.cautions) or "none", start=st.start, end=st.end,
                    chunks=format_chunks(hits)),
                context={"step": step_context(st), "chunks": chunk_context(chunks)},
                prompt_version=step_prompt.version,
            )
            out, key = ctx.llm.call(req)
            checked = validate_notes(out.notes, chunks, st.id, f"c-{st.id}", step_text(st) + " " + labels_text(chunks),
                                     key, s.min_quote_chars)
            notes, dropped = checked.notes, dropped + checked.dropped
        results.append(StepCompliance(step_id=st.id, notes=notes, no_relevant_guidance=not notes,
                                      retrieved_chunk_ids=[c.id for c in chunks], query=query))

    global_notes = []
    if s.check_missing_steps and steps:
        hits = retriever.search([procedure_query(steps)], s.missing_steps_top_k)[0]
        if hits:
            prompt = load_prompt("compliance_missing_steps")
            chunks = [h.chunk for h in hits]
            req = LLMRequest(
                task="compliance_missing_steps", system=prompt.system, schema=MissingStepsOutput,
                user=prompt.render(steps="\n".join(f"{st.id}. {st.title}: {st.instruction}" for st in steps),
                                   chunks=format_chunks(hits)),
                context={"steps": [step_context(st) for st in steps], "chunks": chunk_context(chunks)},
                prompt_version=prompt.version,
            )
            out, key = ctx.llm.call(req)
            checked = validate_notes(out.notes, chunks, None, "c-global",
                                     " ".join(step_text(st) for st in steps) + " " + labels_text(chunks), key, s.min_quote_chars)
            global_notes, dropped = checked.notes, dropped + checked.dropped

    for msg in dropped:
        ctx.log.warning("dropped: %s", msg)
    ctx.project.write(REPORT, ComplianceReport(
        documents=index.doc_index.documents, steps=results, global_notes=global_notes,
        embedding_model=index.doc_index.embedding_model, dropped=dropped))
    n_notes = sum(len(r.notes) for r in results)
    ctx.log.info("%d step notes, %d global notes, %d steps without guidance, %d drops",
                 n_notes, len(global_notes), sum(r.no_relevant_guidance for r in results), len(dropped))


# ---- prompt building --------------------------------------------------------------------------


def chunk_label(c: DocChunk) -> str:
    where = []
    if c.page is not None:
        where.append(f"p. {c.page}" + (f"-{c.page_end}" if c.page_end else ""))
    if c.section:
        where.append(c.section)
    return f"[{c.id}] {c.doc_name}" + (f" ({', '.join(where)})" if where else "")


def format_chunks(hits: list[Hit]) -> str:
    return "\n\n".join(f"{chunk_label(h.chunk)}\n{h.chunk.text}" for h in hits)


def step_text(st: Step) -> str:
    return " ".join([st.title, st.instruction, *st.details, *st.tools, *st.materials, *st.cautions, st.expected_result or ""])


def labels_text(chunks: list[DocChunk]) -> str:
    """Chunk labels (page numbers, section numbers) are shown to the LLM, so their numbers are grounded too."""
    return " ".join(chunk_label(c) for c in chunks)


def step_context(st: Step) -> dict:
    return {"id": st.id, "title": st.title, "instruction": st.instruction, "details": st.details,
            "tools": st.tools + st.materials, "cautions": st.cautions}


def chunk_context(chunks: list[DocChunk]) -> list[dict]:
    return [{"id": c.id, "text": c.text, "section": c.section, "page": c.page} for c in chunks]


# ---- fake LLM (no API key): plausible, citation-valid placeholder notes ------------------------

_STEP_SECONDS = re.compile(r"(\d+)\s*(?:-|to)?\s*(?:\d+\s*)?(?:seconds|secs?|s)\b", re.I)
_DOC_AT_LEAST = re.compile(r"at least (\d+)(?:\s*(?:to|-)\s*(\d+))?\s*seconds", re.I)
_MANDATORY = re.compile(r"\b(shall|must|required|requires)\b", re.I)
_ITEM = re.compile(r"\(\d{1,2}\)\s*[^;()]{8,200}?(?=;|\.\s|\.$|$)")


def _overlap(a: set[str], text: str) -> int:
    return len(a & set(tokenize(text)))


def _quotable(sentence: str, limit: int = 240) -> str:
    """Trim a long sentence at a word boundary; the result is still a verbatim prefix."""
    if len(sentence) <= limit:
        return sentence
    return sentence[:limit].rsplit(" ", 1)[0]


@fake_handler("compliance_step")
def _fake_step(req: LLMRequest) -> StepNotesOutput:
    step, chunks = req.context["step"], req.context["chunks"]
    text = " ".join([step["title"], step["instruction"], *step["details"], *step["tools"], *step["cautions"]])
    words = set(tokenize(text))
    notes: list[StepNoteDraft] = []

    # Conflict: the step states a duration below a document's "at least N seconds".
    if m := _STEP_SECONDS.search(text):
        shown = int(m.group(1))
        for c in chunks:
            for sent in sentences(c["text"]):
                req_m = _DOC_AT_LEAST.search(sent)
                if req_m and shown < int(req_m.group(1)) and _overlap(words, sent) >= 1:
                    need = req_m.group(0)
                    notes.append(StepNoteDraft(
                        kind="conflict", severity="critical",
                        text=f"[fake LLM] The video shows {shown} seconds, but the document requires {need}.",
                        citations=[QuoteRef(chunk_id=c["id"], quote=_quotable(sent))]))
                    break
            if notes:
                break

    # Best-overlapping chunk/sentence as a requirement or reference note.
    best = max(chunks, key=lambda c: (_overlap(words, c["text"]), -chunks.index(c)), default=None)
    if best is not None and _overlap(words, best["text"]) >= 2:
        sent = max(sentences(best["text"]), key=lambda x: (_overlap(words, x), -len(x)))
        if _overlap(words, sent) >= 1 and len(sent) >= 12:
            mandatory = bool(_MANDATORY.search(sent) or _MANDATORY.search(best["text"]))
            notes.append(StepNoteDraft(
                kind="requirement" if mandatory else "reference", severity="warning" if mandatory else "info",
                text=f"[fake LLM] Placeholder note: {best.get('section') or best['id']} appears relevant to "
                     f"'{step['title']}'; check the quoted passage.",
                citations=[QuoteRef(chunk_id=best["id"], quote=_quotable(sent))]))
    return StepNotesOutput(notes=notes)


@fake_handler("compliance_missing_steps")
def _fake_missing(req: LLMRequest) -> MissingStepsOutput:
    """An enumerated document item "(n) ..." is missing if no step title starts with one of its words
    and no single step shares at least half of its words."""
    steps, chunks = req.context["steps"], req.context["chunks"]
    title_verbs = {t[0] for s in steps if (t := tokenize(s["title"]))}
    step_words = [set(tokenize(f"{s['title']} {s['instruction']} {' '.join(s['details'])}")) for s in steps]
    notes: list[MissingStepDraft] = []
    seen: set[str] = set()
    for c in chunks:
        for m in _ITEM.finditer(c["text"]):
            item = m.group(0).strip()
            toks = set(tokenize(re.sub(r"^\(\w+\)", "", item)))
            if len(toks) < 3 or item.lower() in seen:
                continue
            seen.add(item.lower())
            if toks & title_verbs or max((len(toks & w) / len(toks) for w in step_words), default=0) >= 0.5:
                continue
            notes.append(MissingStepDraft(
                after_step_id=None, severity="warning",
                text=f"[fake LLM] Placeholder: the document lists a step the video may not show: {item}",
                citations=[QuoteRef(chunk_id=c["id"], quote=_quotable(item))]))
            if len(notes) >= 3:
                return MissingStepsOutput(notes=notes)
    return MissingStepsOutput(notes=notes)
