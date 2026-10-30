"""Stage 'compliance': RAG over the uploader's SOPs/manuals -> cited notes per step + missing steps.

refine/steps.json + inputs/documents -> compliance/index/ (chunks.json, embeddings.npy, manifest.json)
                                     -> compliance/compliance.json (ComplianceReport)

1. Retrieval per step: the step's fields become sub-queries (action, objects, quantities, cautions,
   whole procedure as context), each BM25 + dense, fused with weighted RRF; a cross-encoder re-ranks
   the candidates; same-section neighbours of the best hits are added (rag.retrieve, rag.rerank).
2. Document procedure: chunks retrieved for the whole procedure -> one LLM call
   ("compliance_sop_procedure") extracts the documents' ordered procedure steps P1..Pn, each citing
   sentence ids -> one LLM call ("compliance_missing_steps") maps every P step to the video steps
   that perform it; unperformed mandatory P steps become missing_step notes whose citations are the
   P step's own (already checked) citations.
3. Per step: one LLM call ("compliance_step") sees the step field by field, the document procedure
   with the P steps matched to it marked, and the retrieved chunks as records with numbered
   sentences. It returns typed findings citing (chunk, sentence ids); the code checks the ids and
   derives the verbatim quotes (rag.notes.validate_findings).

A step with no surviving note is marked ``no_relevant_guidance``.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel

from ..llm import LLMRequest, fake_handler
from ..prompts import load_prompt
from ..rag import (
    DocSource, EmbeddingSettings, Hit, HybridRetriever, Index, load_or_build_index, make_embedder, procedure_query,
    step_query,
)
from ..rag.notes import (
    ProcedureCoverageOutput, SentenceRef, Shown, SopProcedureOutput, SopStepCoverage, SopStepDraft, StepFinding,
    StepFindingsOutput, chunk_sentences, format_chunk, resolve_citations, validate_findings,
)
from ..rag.rerank import DEFAULT_RERANK_MODEL, CrossEncoderReranker
from ..rag.retrieve import Facet, expand_neighbours, step_facets
from ..rag.text import numbers, tokenize
from ..schemas.compliance import ComplianceNote, ComplianceReport, DocChunk, SopProcedureStep, StepCompliance
from ..schemas.steps import Step, StepList
from . import StageContext

INDEX_DIR = "compliance/index"
REPORT = "compliance/compliance.json"


class ComplianceSettings(BaseModel):
    top_k: int = 6                      # chunks retrieved per step and sent to the LLM
    missing_steps_top_k: int = 6        # chunks retrieved for the whole procedure (procedure extraction)
    check_missing_steps: bool = True    # extract the document procedure and check which steps the video skips
    rrf_k: int = 60                     # reciprocal-rank-fusion constant
    candidate_pool: int = 50            # per-retriever depth before fusion
    chunk_words: int = 300              # max words per chunk (~400 tokens)
    chunk_overlap_words: int = 40
    min_chunk_words: int = 60           # smaller sections are merged into the next one
    strip_priority_markers: bool = True  # FDA Food Code "P"/"Pf" markers after clauses
    # Retrieval (see eval/rag_compliance_bench.py for the measured effect of each knob)
    retrieval: Literal["structured", "plain"] = "structured"  # plain = one query per step (legacy)
    facet_weights: dict[str, float] = {}  # override RRF weights: action, objects, quantities, safety, procedure
    rerank: Literal["auto", "on", "off"] = "auto"  # auto = on unless embeddings.provider is hash (tests)
    rerank_model: str = DEFAULT_RERANK_MODEL
    rerank_candidates: int = 30          # fused candidates the cross-encoder re-orders
    neighbours: int = 2                  # max same-section neighbour chunks added per step (0 = off)
    skip_references: bool = True         # never retrieve bibliography / reference-list chunks


# ---- retrieval -------------------------------------------------------------------------------


@dataclass
class Retrieval:
    index: Index
    retriever: HybridRetriever
    reranker: CrossEncoderReranker | None


def open_retrieval(ctx: StageContext, s: ComplianceSettings, sources: list[DocSource]) -> Retrieval:
    emb_settings = ctx.config.section("embeddings", EmbeddingSettings)
    embedder = make_embedder(emb_settings)
    t0 = time.perf_counter()
    index = load_or_build_index(ctx.project.path(INDEX_DIR), sources, embedder, s.chunk_words,
                                s.chunk_overlap_words, s.min_chunk_words, s.strip_priority_markers)
    ctx.log.info("index %s: %d chunks in %.1fs", "built" if index.rebuilt else "reused", len(index.chunks), time.perf_counter() - t0)
    use_rerank = s.rerank == "on" or (s.rerank == "auto" and emb_settings.provider != "hash")
    reranker = CrossEncoderReranker(s.rerank_model, emb_settings.threads, emb_settings.cache_dir) if use_rerank else None
    return Retrieval(index, HybridRetriever(index, embedder, s.rrf_k, s.candidate_pool, s.skip_references), reranker)


def _ranked(r: Retrieval, facet_sets: list[list[Facet]], rerank_queries: list[str], s: ComplianceSettings,
            top_k: int, depth: int | None) -> list[list[Hit]]:
    pool = max(depth or 0, s.rerank_candidates, top_k)
    out = []
    for query, hits in zip(rerank_queries, r.retriever.search_facets(facet_sets, pool)):
        if r.reranker is not None:
            hits = r.reranker.rerank(query, hits[: s.rerank_candidates]) + hits[s.rerank_candidates:]
        if depth:
            out.append(hits[:depth])
        else:
            out.append(expand_neighbours(hits[:top_k], r.index.chunks, limit=s.neighbours) if s.neighbours else hits[:top_k])
    return out


def retrieve_steps(r: Retrieval, steps: list[Step], s: ComplianceSettings, depth: int | None = None) -> list[list[Hit]]:
    """Per step: facet-fused hybrid candidates -> cross-encoder re-rank -> top_k (+ neighbours).

    With ``depth`` the full ranking is returned instead (no truncation to top_k, no neighbours), for
    measuring where a chunk lands."""
    if s.retrieval == "plain":
        return r.retriever.search([step_query(st) for st in steps], depth or s.top_k)
    proc = procedure_query(steps)
    facets = [step_facets(st, proc, s.facet_weights) for st in steps]
    return _ranked(r, facets, [step_query(st) for st in steps], s, s.top_k, depth)


def retrieve_procedure(r: Retrieval, steps: list[Step], s: ComplianceSettings) -> list[Hit]:
    q = procedure_query(steps)
    if s.retrieval == "plain":
        return r.retriever.search([q], s.missing_steps_top_k)[0]
    return _ranked(r, [[Facet("procedure", q)]], [q], s, s.missing_steps_top_k, None)[0]


def rank_steps(ctx: StageContext, steps: list[Step], depth: int = 200) -> dict[str, list[str]]:
    """Full chunk ranking per step (benchmark helper; the index must already exist)."""
    s = ctx.config.section("compliance", ComplianceSettings)
    sources = [DocSource(d.id, d.name, ctx.project.path(d.path), d.path, d.sha) for d in ctx.project.manifest.documents]
    r = open_retrieval(ctx, s, sources)
    return {st.id: [h.chunk.id for h in hits] for st, hits in zip(steps, retrieve_steps(r, steps, s, depth))}


# ---- stage -----------------------------------------------------------------------------------


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

    sources = [DocSource(d.id, d.name, ctx.project.path(d.path), d.path, d.sha) for d in docs]
    r = open_retrieval(ctx, s, sources)
    t0 = time.perf_counter()
    hits_per_step = retrieve_steps(r, steps, s)
    ctx.log.info("retrieved chunks for %d steps in %.1fs", len(steps), time.perf_counter() - t0)
    dropped: list[str] = []
    stats = {"proposed_citations": 0, "invalid_citations": 0}
    all_steps_text = " ".join(step_text(st) for st in steps)

    # Document procedure -> coverage -> missing steps.
    sop: list[SopProcedureStep] = []
    title: str | None = None
    proc_chunks: list[DocChunk] = []
    global_notes: list[ComplianceNote] = []
    if s.check_missing_steps and steps:
        proc_chunks = [h.chunk for h in retrieve_procedure(r, steps, s)]
        if proc_chunks:
            sop, title = extract_procedure(ctx, steps, proc_chunks, dropped, stats)
        if sop:
            global_notes = check_coverage(ctx, steps, sop, title, all_steps_text, dropped)
    by_chunk = {c.id: c for c in r.index.chunks}

    step_prompt = load_prompt("compliance_step")
    results = []
    for st, hits in zip(steps, hits_per_step):
        shown = Shown()
        for h in hits:
            shown.add(h.chunk)
        for p in sop:
            for c in p.citations:
                shown.add(by_chunk[c.chunk_id], set(c.sentence_ids))
        notes: list[ComplianceNote] = []
        if hits or sop:
            others = "; ".join(f"{o.id} {o.title}" for o in steps if o.id != st.id) or "none"
            req = LLMRequest(
                task="compliance_step", system=step_prompt.system, schema=StepFindingsOutput,
                user=step_prompt.render(
                    step_id=st.id, title=st.title, instruction=st.instruction,
                    details="; ".join(st.details) or "none", tools=", ".join(st.tools) or "none",
                    materials=", ".join(st.materials) or "none", cautions="; ".join(st.cautions) or "none",
                    start=st.start, end=st.end, other_steps=others, procedure_title=title or "none found",
                    procedure=format_procedure(sop, st.id), chunks="\n\n".join(format_chunk(h.chunk) for h in hits) or "none"),
                context={"step": step_context(st), "chunks": [chunk_record(h.chunk) for h in hits],
                         "procedure": procedure_context(sop, st.id)},
                prompt_version=step_prompt.version,
            )
            out, key = ctx.llm.call(req)
            checked = validate_findings(out.findings, shown, st.id, step_text(st) + " " + all_steps_text, key)
            notes, dropped = checked.notes, dropped + checked.dropped
            stats["proposed_citations"] += checked.proposed_citations
            stats["invalid_citations"] += checked.invalid_citations
        results.append(StepCompliance(
            step_id=st.id, notes=notes, no_relevant_guidance=not notes,
            retrieved_chunk_ids=[h.chunk.id for h in hits], query=step_query(st),
            context_chunk_ids=list(shown.chunks), sop_step_ids=[p.id for p in sop if st.id in p.video_step_ids]))

    for msg in dropped:
        ctx.log.warning("dropped: %s", msg)
    ctx.project.write(REPORT, ComplianceReport(
        documents=r.index.doc_index.documents, steps=results, global_notes=global_notes,
        embedding_model=r.index.doc_index.embedding_model, dropped=dropped, sop_procedure=sop,
        sop_procedure_title=title, procedure_chunk_ids=[c.id for c in proc_chunks], citation_stats=stats))
    n_notes = sum(len(x.notes) for x in results)
    ctx.log.info("%d step notes, %d global notes, %d SOP procedure steps, %d steps without guidance, %d drops",
                 n_notes, len(global_notes), len(sop), sum(x.no_relevant_guidance for x in results), len(dropped))


def extract_procedure(ctx: StageContext, steps: list[Step], chunks: list[DocChunk], dropped: list[str],
                      stats: dict[str, int]) -> tuple[list[SopProcedureStep], str | None]:
    prompt = load_prompt("compliance_sop_procedure")
    shown = Shown()
    for c in chunks:
        shown.add(c)
    req = LLMRequest(
        task="compliance_sop_procedure", system=prompt.system, schema=SopProcedureOutput,
        user=prompt.render(task="; ".join(st.title for st in steps), chunks="\n\n".join(format_chunk(c) for c in chunks)),
        context={"steps": [step_context(st) for st in steps], "chunks": [chunk_record(c) for c in chunks]},
        prompt_version=prompt.version,
    )
    out, _ = ctx.llm.call(req)
    sop: list[SopProcedureStep] = []
    for n, d in enumerate(out.steps, start=1):
        res = resolve_citations(d.citations, shown)
        stats["proposed_citations"] += len(d.citations)
        stats["invalid_citations"] += len(res.errors)
        dropped += [f"sop step {n}: {e}" for e in res.errors]
        if not res.citations:
            dropped.append(f"sop step {n}: no valid citations; dropped: {d.action[:80]!r}")
            continue
        if invented := numbers(d.action) - numbers(" ".join(res.sentences)):
            dropped.append(f"sop step {n}: numbers {sorted(invented)} not in the cited sentences; dropped")
            continue
        sop.append(SopProcedureStep(id=f"P{len(sop) + 1}", action=d.action.strip(), mandatory=d.mandatory,
                                    citations=res.citations))
    return sop, (out.title or None) if sop else None


def check_coverage(ctx: StageContext, steps: list[Step], sop: list[SopProcedureStep], title: str | None,
                   all_steps_text: str, dropped: list[str]) -> list[ComplianceNote]:
    """Which document steps does the video perform? Fills ``video_step_ids``/``status`` on ``sop`` and
    returns missing_step notes for the ones it does not."""
    prompt = load_prompt("compliance_missing_steps")
    req = LLMRequest(
        task="compliance_missing_steps", system=prompt.system, schema=ProcedureCoverageOutput,
        user=prompt.render(steps="\n".join(f"{st.id}. {st.title}: {st.instruction}" for st in steps),
                           procedure_title=title or "untitled", procedure=format_procedure(sop, None)),
        context={"steps": [step_context(st) for st in steps], "procedure": procedure_context(sop, None)},
        prompt_version=prompt.version,
    )
    out, key = ctx.llm.call(req)
    by_id = {p.id: p for p in sop}
    step_ids = [st.id for st in steps]
    notes: list[ComplianceNote] = []
    for cov in out.coverage:
        p = by_id.get(cov.sop_step.strip())
        if p is None:
            dropped.append(f"coverage: unknown document step {cov.sop_step!r}")
            continue
        p.video_step_ids = [v for v in cov.video_step_ids if v in step_ids]
        p.status = "missing" if cov.status == "missing" and not p.video_step_ids else (
            "partly_covered" if cov.status == "partly_covered" else "covered")
        if p.status != "missing":
            continue
        text = cov.text.strip() or f"The documents require a step the video does not show: {p.action}"
        grounded = numbers(all_steps_text) | numbers(p.action) | numbers(" ".join(c.quote for c in p.citations))
        if invented := numbers(text) - grounded:
            dropped.append(f"coverage {p.id}: numbers {sorted(invented)} not in the document step; note dropped")
            continue
        notes.append(ComplianceNote(
            id=f"c-global-{len(notes) + 1}", step_id=None, kind="missing_step",
            severity=cov.severity if p.mandatory else ("warning" if cov.severity == "critical" else cov.severity),
            text=text, citations=p.citations, llm_call=key, sop_step_id=p.id,
            after_step_id=cov.after_step_id if cov.after_step_id in step_ids else None))
    return notes


# ---- prompt building --------------------------------------------------------------------------


def format_procedure(sop: list[SopProcedureStep], step_id: str | None) -> str:
    if not sop:
        return "none found in the documents"
    lines = []
    for p in sop:
        mark = " [matched to this step]" if step_id and step_id in p.video_step_ids else ""
        src = "; ".join(f'{c.chunk_id} [{", ".join(f"S{i}" for i in c.sentence_ids)}] "{c.quote}"' for c in p.citations)
        lines.append(f"{p.id}{mark} {p.action} ({'mandatory' if p.mandatory else 'recommended'}) | source: {src}")
    return "\n".join(lines)


def step_text(st: Step) -> str:
    return " ".join([st.title, st.instruction, *st.details, *st.tools, *st.materials, *st.cautions, st.expected_result or ""])


def step_context(st: Step) -> dict:
    return {"id": st.id, "title": st.title, "instruction": st.instruction, "details": st.details,
            "tools": st.tools + st.materials, "cautions": st.cautions}


def chunk_record(c: DocChunk) -> dict:
    return {"id": c.id, "section": c.section, "page": c.page, "sentences": chunk_sentences(c)}


def procedure_context(sop: list[SopProcedureStep], step_id: str | None) -> list[dict]:
    return [{"id": p.id, "action": p.action, "mandatory": p.mandatory, "matched": bool(step_id and step_id in p.video_step_ids),
             "refs": [{"chunk_id": c.chunk_id, "sentence_ids": c.sentence_ids, "text": c.quote} for c in p.citations]}
            for p in sop]


# ---- fake LLM (no API key): plausible, citation-valid placeholder output -------------------------

_STEP_SECONDS = re.compile(r"(\d+)\s*(?:-|to)?\s*(?:\d+\s*)?(?:seconds|secs?|s)\b", re.I)
_DOC_AT_LEAST = re.compile(r"at least (\d+)(?:\s*(?:to|-)\s*(\d+))?\s*seconds", re.I)
_MANDATORY = re.compile(r"\b(shall|must|required|requires)\b", re.I)
_ITEM = re.compile(r"^(?:(?:and|or)\s+)?\((\d{1,2})\)\s*(.{8,})$")


def _overlap(a: set[str], text: str) -> int:
    return len(a & set(tokenize(text)))


def _visible_sentences(req: LLMRequest) -> list[tuple[str, int, str]]:
    """(chunk id, sentence id, text) of everything the fake 'sees': chunks, then procedure sources."""
    out = [(c["id"], n, sent) for c in req.context["chunks"] for n, sent in enumerate(c["sentences"], start=1)]
    for p in req.context.get("procedure", []):
        for ref in p["refs"]:
            out += [(ref["chunk_id"], ref["sentence_ids"][0], ref["text"])]
    return out


@fake_handler("compliance_step")
def _fake_step(req: LLMRequest) -> StepFindingsOutput:
    step, chunks = req.context["step"], req.context["chunks"]
    text = " ".join([step["title"], step["instruction"], *step["details"], *step["tools"], *step["cautions"]])
    words = set(tokenize(text))
    findings: list[StepFinding] = []

    # Conflict: the step states a duration below a document's "at least N seconds".
    if m := _STEP_SECONDS.search(text):
        shown = int(m.group(1))
        for cid, sid, sent in _visible_sentences(req):
            req_m = _DOC_AT_LEAST.search(sent)
            if req_m and shown < int(req_m.group(1)) and _overlap(words, sent) >= 1:
                findings.append(StepFinding(
                    citations=[SentenceRef(chunk_id=cid, sentence_ids=[sid])], kind="conflict",
                    requirement_type="duration", step_field="duration", sop_value=req_m.group(0),
                    video_value=m.group(0).strip(), severity="critical",
                    text=f"[fake LLM] The video shows {shown} seconds, but the document requires {req_m.group(0)}."))
                break

    # A document procedure step matched to this video step, else the best-overlapping chunk sentence.
    matched = [p for p in req.context.get("procedure", []) if p["matched"]]
    if matched:
        p = matched[0]
        ref = p["refs"][0]
        findings.append(StepFinding(
            citations=[SentenceRef(chunk_id=ref["chunk_id"], sentence_ids=ref["sentence_ids"])],
            kind="requirement" if p["mandatory"] else "reference", requirement_type="order", step_field="whole_step",
            sop_value=None, video_value=None, severity="warning" if p["mandatory"] else "info",
            text=f"[fake LLM] Placeholder note: document step {p['id']} ('{p['action'][:60]}') applies to "
                 f"'{step['title']}'; check the cited sentence."))
        return StepFindingsOutput(findings=findings)
    best = max(chunks, key=lambda c: (_overlap(words, " ".join(c["sentences"])), -chunks.index(c)), default=None)
    if best is not None and _overlap(words, " ".join(best["sentences"])) >= 2:
        sid, sent = max(enumerate(best["sentences"], start=1), key=lambda x: (_overlap(words, x[1]), -len(x[1])))
        if _overlap(words, sent) >= 1 and len(sent) >= 12:
            mandatory = bool(_MANDATORY.search(sent) or _MANDATORY.search(" ".join(best["sentences"])))
            findings.append(StepFinding(
                citations=[SentenceRef(chunk_id=best["id"], sentence_ids=[sid])],
                kind="requirement" if mandatory else "reference", requirement_type="other", step_field="whole_step",
                sop_value=None, video_value=None, severity="warning" if mandatory else "info",
                text=f"[fake LLM] Placeholder note: {best.get('section') or best['id']} appears relevant to "
                     f"'{step['title']}'; check the cited sentence."))
    return StepFindingsOutput(findings=findings)


@fake_handler("compliance_sop_procedure")
def _fake_sop_procedure(req: LLMRequest) -> SopProcedureOutput:
    """The first chunk with an enumerated list "(1) ... (2) ... (3) ..." is the procedure."""
    for c in req.context["chunks"]:
        items = [(n, m) for n, sent in enumerate(c["sentences"], start=1) if (m := _ITEM.match(sent))]
        if len(items) < 3:
            continue
        mandatory = bool(_MANDATORY.search(" ".join(c["sentences"])))
        steps = [SopStepDraft(citations=[SentenceRef(chunk_id=c["id"], sentence_ids=[n])],
                              action=m.group(2).rstrip(";,.: ").removesuffix(" and").rstrip(";, "), mandatory=mandatory)
                 for n, m in items]
        return SopProcedureOutput(title=c["section"], steps=steps)
    return SopProcedureOutput(title=None, steps=[])


@fake_handler("compliance_missing_steps")
def _fake_coverage(req: LLMRequest) -> ProcedureCoverageOutput:
    """A document step is covered by video steps whose title or instruction verb it contains or that share at least
    half of its words; otherwise it is missing, after the video step of the previous covered one."""
    steps = req.context["steps"]
    step_words = {s["id"]: set(tokenize(f"{s['title']} {s['instruction']} {' '.join(s['details'])}")) for s in steps}
    verbs = {s["id"]: {(tokenize(s[f]) or [""])[0] for f in ("title", "instruction")} for s in steps}
    out: list[SopStepCoverage] = []
    last: str | None = None
    for p in req.context["procedure"]:
        toks = set(tokenize(p["action"]))
        hit = [sid for sid in step_words if toks and (verbs[sid] & toks or len(toks & step_words[sid]) / len(toks) >= 0.5)]
        if hit:
            last = hit[-1]
            out.append(SopStepCoverage(sop_step=p["id"], video_step_ids=hit, status="covered", after_step_id=None,
                                       severity="info", text=""))
        else:
            out.append(SopStepCoverage(
                sop_step=p["id"], video_step_ids=[], status="missing", after_step_id=last,
                severity="critical" if p["mandatory"] else "warning",
                text=f"[fake LLM] Placeholder: the document lists a step the video may not show: {p['action']}"))
    return ProcedureCoverageOutput(coverage=out)
