"""M4: document loading, chunking, indexing, hybrid retrieval, citation guardrails, compliance stage."""

from __future__ import annotations

import logging
import time

import pytest

from tutorialgen.config import Config
from tutorialgen.llm import CachedLLM, make_provider
from tutorialgen.project import Project
from tutorialgen.rag import (
    DocSource, EmbeddingSettings, HybridRetriever, MissingStepDraft, MissingStepsOutput, QuoteRef, StepNoteDraft,
    StepNotesOutput, chunk_blocks, load_document, load_or_build_index, make_embedder, quote_in_text, step_query,
    validate_notes,
)
from tutorialgen.rag.embeddings import HashEmbedder
from tutorialgen.rag.loaders import heading_of, load_text, pages_to_blocks
from tutorialgen.schemas import ComplianceReport, DocChunk, DocIndex, Step, StepList
from tutorialgen.stages import StageContext
from tutorialgen.stages import compliance as compliance_stage

FILLER = (
    "Records of deliveries are kept by the person in charge for review by the regulatory authority. "
    "Each delivery is inspected for temperature, packaging integrity and labelling before it is accepted. "
)

SOP = f"""# Kitchen Hygiene SOP

## 1. Scope
This procedure applies to all kitchen staff who handle food, utensils or equipment.

## 2. Receiving Deliveries
{FILLER * 6}

## 3. Handwashing Procedure
Employees shall clean their hands and exposed portions of their arms for at least 20 seconds.
Employees shall follow these steps in the order stated:
(1) Rinse hands under clean, running warm water;
(2) Apply soap recommended by the soap manufacturer;
(3) Rub hands together vigorously for at least 20 seconds, including the backs of the hands, between the fingers and under the fingernails;
(4) Rinse hands thoroughly under clean, running warm water;
(5) Dry hands with a single-use paper towel;
(6) Use the paper towel to turn off the faucet so clean hands do not touch the handle.

## 4. Glove Use
Single-use gloves must be changed when they are torn, soiled, or when the employee changes tasks.
Gloves are not a substitute for handwashing.

## 5. Equipment Storage
Knives and cutting boards shall be stored on clean racks at least 6 inches above the floor.
{FILLER * 4}
"""


def hand_steps(scrub_seconds: int = 20, skip_dry: bool = False) -> StepList:
    raw = [
        ("Wet hands", "Wet both hands under running water.", [], []),
        ("Apply soap", "Apply a pump of liquid soap to your palms.", [], ["liquid soap"]),
        ("Scrub hands", f"Rub hands together for {scrub_seconds} seconds, including backs of hands, between fingers and under nails.", [], []),
        ("Rinse hands", "Rinse the soap off your hands under running water.", [], []),
        ("Dry hands", "Dry your hands with a paper towel.", [], ["paper towel"]),
        ("Turn off tap", "Turn off the faucet using the paper towel.", [], ["paper towel"]),
        ("Wave goodbye", "Smile and wave at the camera.", [], []),
    ]
    if skip_dry:
        raw = [r for r in raw if r[0] != "Dry hands"]
    steps = [Step(id=f"s{i + 1:02d}", index=i, start=i * 4.0, end=i * 4.0 + 4, title=t, instruction=ins,
                  tools=tools, materials=mats, confidence=0.8) for i, (t, ins, tools, mats) in enumerate(raw)]
    return StepList(revision=0, steps=steps)


def make_project(tmp_path, steps: StepList, with_doc: bool = True) -> Project:
    p = Project.create("handwash")
    p.write("refine/steps.json", steps)
    if with_doc:
        doc = tmp_path / "kitchen-sop.md"
        doc.write_text(SOP)
        p.add_document(doc, name="Kitchen Hygiene SOP")
    return p


def run_stage(p: Project) -> ComplianceReport:
    config = p.config()
    ctx = StageContext(project=p, config=config, llm=CachedLLM(make_provider(config), p.path("llm_cache")),
                       log=logging.getLogger("test.compliance"))
    compliance_stage.run(ctx)
    return p.read("compliance/compliance.json", ComplianceReport)


# ---- loaders ------------------------------------------------------------------------------------


def test_pdf_page_processing_strips_furniture_and_detects_headings():
    pages = []
    for n in range(1, 7):
        body = "Some general text about food safety on this page.\n"
        if n == 3:
            body = ("2-301 Hands and Arms\n2-301.12 Cleaning Procedure.\n(A) FOOD EMPLOYEES shall clean their hands "
                    "for at least 20 seconds, using a cleaning com-\npound in a HANDWASHING SINK.P\n(3) Rub together vigorously; P and\n")
        pages.append(f"FDA Food Code 2022     Chapter 2. Management\nChapter 2 - {n + 10}\n{body}Annex 3 - {n}\n")
    blocks = pages_to_blocks(pages)
    text = " ".join(b.text for b in blocks)
    assert "FDA Food Code" not in text and "Chapter 2 -" not in text and "Annex 3 -" not in text
    assert "cleaning compound in a HANDWASHING SINK." in text  # de-hyphenated, priority marker removed
    assert "vigorously; and" in text
    body = next(b for b in blocks if "at least 20 seconds" in b.text)
    assert body.page == 3 and body.section == "2-301.12 Cleaning Procedure" and not body.heading
    assert [b.section for b in blocks if b.heading] == ["2-301 Hands and Arms", "2-301.12 Cleaning Procedure"]


def test_heading_detection():
    assert heading_of("2-301.12 Cleaning Procedure.") == "2-301.12 Cleaning Procedure"
    assert heading_of("3.1 Scope") == "3.1 Scope"
    assert heading_of("20 seconds is the minimum time for rubbing hands together") is None
    assert heading_of("4. Lee, L.A., C.N. Shapiro, N. Hargrett-Bean and R.V. Tauxe, 1991.") is None
    assert heading_of("1. Wet your hands with clean running water.") is None


def test_markdown_and_docx_loaders(tmp_path):
    doc = load_text(SOP)
    heads = [b.text for b in doc.blocks if b.heading]
    assert heads[0] == "Kitchen Hygiene SOP" and "3. Handwashing Procedure" in heads
    item = next(b for b in doc.blocks if b.text.startswith("(5)"))
    assert item.section == "3. Handwashing Procedure" and item.page is None

    docx = pytest.importorskip("docx")
    d = docx.Document()
    d.add_heading("Glove Policy", level=1)
    d.add_paragraph("Gloves must be changed between tasks.")
    t = d.add_table(rows=1, cols=2)
    t.rows[0].cells[0].text, t.rows[0].cells[1].text = "Task", "Glove colour"
    d.add_heading("Aprons", level=2)
    d.add_paragraph("Aprons are removed before leaving the kitchen.")
    d.save(tmp_path / "policy.docx")
    blocks = load_document(tmp_path / "policy.docx").blocks
    assert [(b.text, b.section, b.heading) for b in blocks] == [
        ("Glove Policy", "Glove Policy", True),
        ("Gloves must be changed between tasks.", "Glove Policy", False),
        ("Task | Glove colour", "Glove Policy", False),
        ("Aprons", "Aprons", True),
        ("Aprons are removed before leaving the kitchen.", "Aprons", False),
    ]
    with pytest.raises(ValueError):
        load_document(tmp_path / "x.xlsx")


# ---- chunking -----------------------------------------------------------------------------------


def test_chunker_sections_sizes_overlap():
    blocks = load_text(SOP).blocks
    chunks = chunk_blocks("d01", "SOP", blocks, max_words=80, overlap_words=20, min_words=30)
    assert [c.id for c in chunks] == [f"d01:{i}" for i in range(len(chunks))]
    assert all(len(c.text.split()) <= 80 + 25 for c in chunks)  # heading lines may ride along
    hand = [c for c in chunks if c.section == "3. Handwashing Procedure"]
    assert hand and any("(3) Rub hands together" in c.text for c in hand)
    # The long filler section is split, and consecutive pieces overlap.
    receiving = [c for c in chunks if c.section == "2. Receiving Deliveries"]
    assert len(receiving) >= 2
    tail = receiving[0].text.split()[-5:]
    assert " ".join(tail) in receiving[1].text
    # Two documents never share a chunk.
    other = chunk_blocks("d02", "Other", load_text("# A\nShort doc about aprons.").blocks)
    assert len(other) == 1 and other[0].id == "d02:0" and other[0].doc_id == "d02"


# ---- citation guardrail -------------------------------------------------------------------------


def test_quote_matching_and_validation():
    chunk = DocChunk(id="d01:3", doc_id="d01", doc_name="SOP", page=4, section="3. Handwashing",
                     text="(3) Rub hands together vigorously for at least 20 seconds,\nincluding the backs of the hands;")
    assert quote_in_text("rub hands together  VIGOROUSLY for at least 20 seconds", chunk.text)
    assert quote_in_text("“Rub hands together vigorously”", chunk.text)
    assert not quote_in_text("rub hands for 30 seconds", chunk.text)
    assert not quote_in_text("hands", chunk.text)  # too short to count

    drafts = [
        StepNoteDraft(kind="requirement", severity="warning", text="Rub for at least 20 seconds.",
                      citations=[QuoteRef(chunk_id="d01:3", quote="for at least 20 seconds, including the backs")]),
        StepNoteDraft(kind="caution", severity="info", text="Made up.",
                      citations=[QuoteRef(chunk_id="d09:1", quote="for at least 20 seconds")]),
        StepNoteDraft(kind="caution", severity="info", text="Paraphrase.",
                      citations=[QuoteRef(chunk_id="d01:3", quote="scrub for twenty seconds")]),
        StepNoteDraft(kind="requirement", severity="critical", text="Use water at 38 C.",
                      citations=[QuoteRef(chunk_id="d01:3", quote="including the backs of the hands")]),
        StepNoteDraft(kind="conflict", severity="critical", text="The step shows 5 seconds; at least 20 are required.",
                      citations=[QuoteRef(chunk_id="[d01:3]", quote="vigorously for at least 20 seconds"),
                                 QuoteRef(chunk_id="d01:7", quote="anything")]),
    ]
    res = validate_notes(drafts, [chunk], "s03", "c-s03", "Rub hands for 5 seconds", llm_call="k")
    assert [(n.id, n.kind) for n in res.notes] == [("c-s03-1", "requirement"), ("c-s03-2", "conflict")]
    assert res.notes[1].citations[0].chunk_id == "d01:3" and len(res.notes[1].citations) == 1
    assert res.notes[0].citations[0].page == 4 and res.notes[0].llm_call == "k"
    assert len(res.dropped) == 6  # 3 bad citations + 3 dropped notes (no citations x2, invented number)
    assert any("['38']" in d for d in res.dropped)

    missing = validate_notes([MissingStepDraft(after_step_id="s04", severity="warning", text="Dry hands.",
                                               citations=[QuoteRef(chunk_id="d01:3", quote="including the backs of the hands")])],
                             [chunk], None, "c-global", "")
    assert missing.notes[0].kind == "missing_step" and missing.notes[0].after_step_id == "s04"


def test_llm_output_schemas_are_openai_strict_compatible():
    pytest.importorskip("openai")
    from openai.lib._pydantic import to_strict_json_schema

    for model in (StepNotesOutput, MissingStepsOutput):
        schema = to_strict_json_schema(model)
        for d in [schema, *schema.get("$defs", {}).values()]:
            if d.get("type") == "object":
                assert d["additionalProperties"] is False
                assert set(d["required"]) == set(d["properties"])


# ---- index + retrieval --------------------------------------------------------------------------


def test_index_reuse_and_hybrid_retrieval(tmp_path):
    src = tmp_path / "sop.md"
    src.write_text(SOP)
    docs = [DocSource("d01", "SOP", src, "inputs/documents/sop.md", "sha1")]
    idx = load_or_build_index(tmp_path / "index", docs, HashEmbedder(), max_words=120, min_words=30)
    assert idx.rebuilt and (tmp_path / "index" / "embeddings.npy").exists()
    assert idx.vectors.shape[0] == len(idx.chunks) > 3
    again = load_or_build_index(tmp_path / "index", docs, HashEmbedder(), max_words=120, min_words=30)
    assert not again.rebuilt and again.doc_index == idx.doc_index
    assert load_or_build_index(tmp_path / "index", docs, HashEmbedder(dims=256), max_words=120, min_words=30).rebuilt
    docs[0].sha = "sha2"
    assert load_or_build_index(tmp_path / "index", docs, HashEmbedder(dims=256), max_words=120, min_words=30).rebuilt

    retriever = HybridRetriever(again, HashEmbedder())
    steps = hand_steps().steps
    hits = retriever.search([step_query(s) for s in steps], top_k=3)
    for s, h in zip(steps, hits):
        assert len(h) == 3 and h[0].score >= h[1].score
        if s.title in ("Scrub hands", "Rinse hands", "Dry hands"):
            assert h[0].chunk.section == "3. Handwashing Procedure", s.title


def test_embedder_selection(monkeypatch):
    assert make_embedder(EmbeddingSettings(provider="hash")).name == "hash:512"
    assert make_embedder(EmbeddingSettings(provider="local")).name == "local:BAAI/bge-small-en-v1.5"  # lazy, no download
    with pytest.raises(ValueError):
        make_embedder(EmbeddingSettings(provider="openai"))
    with pytest.raises(ValueError):
        make_embedder(EmbeddingSettings(provider="nope"))
    assert Config.load().raw("embeddings")["provider"] == "hash"  # conftest forces it


# ---- stage --------------------------------------------------------------------------------------


def test_stage_without_documents_makes_no_llm_calls(tmp_path):
    p = make_project(tmp_path, hand_steps(), with_doc=False)
    report = run_stage(p)
    assert report.documents == [] and len(report.steps) == 7
    assert all(s.no_relevant_guidance and not s.notes for s in report.steps)
    assert not p.path("llm_cache").exists() and p.exists("compliance/index")


def test_stage_end_to_end_with_conflict_and_missing_step(tmp_path):
    p = make_project(tmp_path, hand_steps(scrub_seconds=5, skip_dry=True))
    report = run_stage(p)
    assert report.documents[0].name == "Kitchen Hygiene SOP" and report.documents[0].chunks >= 3
    assert report.embedding_model == "hash:512"
    chunks = {c.id: c for c in p.read("compliance/index/chunks.json", DocIndex).chunks}
    by_step = {s.step_id: s for s in report.steps}

    scrub = by_step["s03"]
    conflict = next(n for n in scrub.notes if n.kind == "conflict")
    assert conflict.severity == "critical" and conflict.text.startswith("[fake LLM]")
    assert "5 seconds" in conflict.text and "at least 20 seconds" in conflict.text
    assert conflict.id.startswith("c-s03-") and conflict.llm_call.startswith("compliance_step-")

    # Every citation points at a retrieved chunk and quotes it verbatim.
    for s in report.steps:
        for n in s.notes:
            for c in n.citations:
                assert c.chunk_id in s.retrieved_chunk_ids and quote_in_text(c.quote, chunks[c.chunk_id].text)
    # "Wave goodbye" (s06 once drying is skipped) still retrieves chunks, but nothing relevant is said.
    assert by_step["s06"].retrieved_chunk_ids
    assert by_step["s06"].no_relevant_guidance and not by_step["s06"].notes

    # The SOP requires drying, which the video skipped.
    assert any(n.kind == "missing_step" and "Dry hands" in n.text for n in report.global_notes)
    for n in report.global_notes:
        assert n.step_id is None and n.id.startswith("c-global-")
        assert all(quote_in_text(c.quote, chunks[c.chunk_id].text) for c in n.citations)

    # Re-running reuses the index and the LLM cache.
    mtime = p.path("compliance/index/embeddings.npy").stat().st_mtime_ns
    assert run_stage(p) == report
    assert p.path("compliance/index/embeddings.npy").stat().st_mtime_ns == mtime


def test_stage_without_conflict_for_compliant_video(tmp_path):
    report = run_stage(make_project(tmp_path, hand_steps(scrub_seconds=20)))
    assert not any(n.kind == "conflict" for s in report.steps for n in s.notes)
    assert not any("Dry hands" in n.text for n in report.global_notes)
    assert any(n.kind == "requirement" for s in report.steps for n in s.notes)


# ---- real manual + local embedding model (slow: downloads ~70 MB once, embeds 668 pages) --------


@pytest.mark.slow
def test_food_code_retrieval_with_local_model(tmp_path, sample, monkeypatch):
    pdf = sample("fda-food-code-2022.pdf")
    monkeypatch.setenv("TUTORIALGEN_EMBEDDINGS_PROVIDER", "local")
    p = Project.create("food code")
    p.add_document(pdf, name="FDA Food Code 2022")
    steps = hand_steps(scrub_seconds=5)
    p.write("refine/steps.json", steps)
    t0 = time.perf_counter()
    report = run_stage(p)
    elapsed = time.perf_counter() - t0
    by_step = {s.step_id: s for s in report.steps}
    index = p.read("compliance/index/chunks.json", DocIndex)
    target = {c.id for c in index.chunks if c.section and c.section.startswith("2-301.12") and "(3) Rub together" in c.text}
    assert target, "2-301.12 Cleaning Procedure chunk not found"
    assert target & set(by_step["s03"].retrieved_chunk_ids[:3]), by_step["s03"].retrieved_chunk_ids  # scrub
    assert target & set(by_step["s04"].retrieved_chunk_ids), by_step["s04"].retrieved_chunk_ids  # rinse: in top_k
    assert any(n.kind == "conflict" for n in by_step["s03"].notes)
    print(f"food code: {len(index.chunks)} chunks, stage {elapsed:.0f}s")
