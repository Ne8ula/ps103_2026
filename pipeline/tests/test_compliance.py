"""M4: document loading, chunking, indexing, hybrid retrieval, citation guardrails, compliance stage."""

from __future__ import annotations

import logging
import time

import pytest

from tutorialgen.config import Config
from tutorialgen.llm import CachedLLM, make_provider
from tutorialgen.project import Project
from tutorialgen.rag import (
    DocSource, EmbeddingSettings, Hit, HybridRetriever, ProcedureCoverageOutput, SentenceRef, Shown, SopProcedureOutput,
    StepFinding, StepFindingsOutput, chunk_blocks, chunk_sentences, expand_neighbours, format_chunk, load_document,
    load_or_build_index, make_embedder, quote_in_text, step_facets, step_query, validate_findings,
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


def test_quote_matching():
    text = "(3) Rub hands together vigorously for at least 20 seconds,\nincluding the backs of the hands;"
    assert quote_in_text("rub hands together  VIGOROUSLY for at least 20 seconds", text)
    assert quote_in_text("“Rub hands together vigorously”", text)
    assert not quote_in_text("rub hands for 30 seconds", text)
    assert not quote_in_text("hands", text)  # too short to count


HAND_CHUNK = DocChunk(id="d01:3", doc_id="d01", doc_name="SOP", page=4, section="3. Handwashing",
                      text="3. Handwashing\nEmployees shall follow these steps: (1) Rinse under running warm water; "
                           "(2) Apply soap; (3) Rub hands together vigorously for at least 20 seconds, including the "
                           "backs of the hands; (4) Rinse thoroughly.")
OTHER_CHUNK = DocChunk(id="d01:9", doc_id="d01", doc_name="SOP", page=9, text="Gloves are changed every 4 hours. Aprons are washed daily.")


def finding(kind="requirement", cites=(("d01:3", [5]),), text="Rub vigorously.", sop=None, video=None) -> StepFinding:
    return StepFinding(citations=[SentenceRef(chunk_id=c, sentence_ids=ids) for c, ids in cites], kind=kind,
                       requirement_type="duration", step_field="duration", sop_value=sop, video_value=video,
                       severity="warning", text=text)


def test_structured_context_numbers_sentences():
    sents = chunk_sentences(HAND_CHUNK)
    assert sents[0] == "3. Handwashing" and sents[2] == "(1) Rinse under running warm water;"
    assert sents[4].startswith("(3) Rub hands together")
    record = format_chunk(HAND_CHUNK)
    assert record.startswith('<chunk id="d01:3" document="SOP" pages="4" section="3. Handwashing">')
    assert "[S5] (3) Rub hands together" in record and record.endswith("</chunk>")
    assert format_chunk(HAND_CHUNK, only={3}).count("[S") == 1


def test_sentence_citations_are_checked_and_quotes_derived():
    shown = Shown()
    shown.add(HAND_CHUNK)
    shown.add(OTHER_CHUNK, only={1})  # e.g. a document procedure step: only its sentence was shown
    step = "Rub hands for 5 seconds"
    res = validate_findings([
        finding(cites=(("d01:3", [5, 6]),)),                                  # ok: one run -> one citation
        finding(cites=(("d09:1", [1]),), text="Made up."),                    # chunk not shown
        finding(cites=(("d01:3", [42]),), text="Bad id."),                    # sentence does not exist
        finding(cites=(("d01:9", [2]),), text="Aprons."),                     # sentence not shown
        finding(cites=(("d01:3", [4]),), text="Use water at 38 C."),          # invented number
        finding("conflict", (("[d01:3]", [5]), ("d01:9", [1])), "The step shows 5 seconds; at least 20 are required.",
                sop="at least 20 seconds", video="5 seconds"),
        finding("conflict", (("d01:3", [5]),), "Too short.", sop="at least 30 seconds", video="5 seconds"),
        finding("conflict", (("d01:3", [5]),), "Too short.", sop="at least 20 seconds", video="10 seconds"),
    ], shown, "s03", step, llm_call="k")
    assert [(n.id, n.kind) for n in res.notes] == [("c-s03-1", "requirement"), ("c-s03-2", "conflict")]
    first, conflict = res.notes
    assert [(c.chunk_id, c.sentence_ids) for c in first.citations] == [("d01:3", [5, 6])]
    assert first.citations[0].quote.startswith("(3) Rub hands") and first.citations[0].quote.endswith("Rinse thoroughly.")
    assert all(quote_in_text(c.quote, HAND_CHUNK.text) for c in first.citations)
    assert first.citations[0].page == 4 and first.llm_call == "k" and first.requirement_type == "duration"
    assert [c.chunk_id for c in conflict.citations] == ["d01:3", "d01:9"]
    assert conflict.sop_value == "at least 20 seconds" and conflict.video_value == "5 seconds"
    assert res.proposed_citations == 9 and res.invalid_citations == 3
    assert any("['38']" in d for d in res.dropped)
    assert any("sop_value numbers ['30']" in d for d in res.dropped)
    assert any("video_value numbers ['10']" in d for d in res.dropped)


def test_llm_output_schemas_are_openai_strict_compatible():
    pytest.importorskip("openai")
    from openai.lib._pydantic import to_strict_json_schema

    for model in (StepFindingsOutput, SopProcedureOutput, ProcedureCoverageOutput):
        schema = to_strict_json_schema(model)
        for d in [schema, *schema.get("$defs", {}).values()]:
            if d.get("type") == "object":
                assert d["additionalProperties"] is False
                assert set(d["required"]) == set(d["properties"])
                for prop in d["properties"].values():
                    assert "default" not in prop
                    assert "anyOf" not in prop or all("$ref" not in a for a in prop["anyOf"])  # no unions of objects


def test_facets_and_neighbour_expansion():
    st = Step(id="s03", index=2, start=0, end=4, title="Scrub hands", instruction="Rub hands together for 5 seconds.",
              tools=["nail brush"], materials=["soap"], cautions=["Do not use hot water."], confidence=0.9)
    facets = {f.name: f for f in step_facets(st, "Wet. Scrub. Rinse.")}
    assert list(facets) == ["action", "objects", "quantities", "safety", "procedure"]
    assert facets["objects"].query == "Scrub hands: nail brush, soap" and "5 seconds" in facets["quantities"].query
    assert facets["procedure"].weight < facets["action"].weight
    assert "procedure" not in {f.name for f in step_facets(st, None, {"procedure": 0})}

    def chunk(n, section, text="Body text."):
        return DocChunk(id=f"d01:{n}", doc_id="d01", doc_name="SOP", section=section, text=text)

    chunks = [chunk(0, "A"), chunk(1, "B", "(1) Rinse; (2) Apply soap;"), chunk(2, "B", "(3) Rub; (4) Rinse."),
              chunk(3, "C"), chunk(4, "B", "2-4 Other Heading\nText.")]
    hits = expand_neighbours([Hit(chunks[1], 1.0, 1, 1), Hit(chunks[3], 0.5, 2, 2)], chunks)
    assert [(h.chunk.id, h.neighbour_of) for h in hits] == [("d01:1", None), ("d01:2", "d01:1"), ("d01:3", None)]
    assert len(expand_neighbours([Hit(chunks[1], 1.0, 1, 1)], chunks, limit=0)) == 1


def test_reference_lists_are_recognised():
    from tutorialgen.rag.retrieve import looks_like_references

    refs = ("9. De Witt, J.C. 1985. The importance of hand hygiene. Antonie von Leeuwenhoek, Vol. 51, pp. 523-527. "
            "10. Eckert, D.G., 1989. Indications for alcohol or bland soap. Infect. Control, Vol. 10, pp. 306-311. "
            "11. Ansari, S.A., 1991. Comparison of cloth, paper and air drying. Am. J. Infect. Cont., Vol.19. No. 5.")
    assert looks_like_references(refs)
    assert not looks_like_references(HAND_CHUNK.text)
    assert not looks_like_references(SOP)


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

    # Every citation points at a chunk shown for that step and quotes it verbatim, by sentence ids.
    for s in report.steps:
        assert set(s.retrieved_chunk_ids) <= set(s.context_chunk_ids)
        for n in s.notes:
            for c in n.citations:
                assert c.chunk_id in s.context_chunk_ids and quote_in_text(c.quote, chunks[c.chunk_id].text)
                assert c.sentence_ids
    assert report.citation_stats["invalid_citations"] == 0 and report.citation_stats["proposed_citations"] > 0

    # The document procedure was extracted in order, and the video steps were mapped onto it.
    sop = report.sop_procedure
    assert report.sop_procedure_title == "3. Handwashing Procedure"
    assert [p.id for p in sop] == ["P1", "P2", "P3", "P4", "P5", "P6"] and all(p.mandatory for p in sop)
    assert sop[2].action.startswith("Rub hands together vigorously") and "s03" in sop[2].video_step_ids
    assert sop[4].status == "missing" and sop[4].action.startswith("Dry hands")
    assert "P3" in by_step["s03"].sop_step_ids and set(report.procedure_chunk_ids)
    assert conflict.sop_value == "at least 20 seconds" and conflict.video_value == "5 seconds"
    assert conflict.requirement_type == "duration"
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
    assert target & set(by_step["s06"].retrieved_chunk_ids), by_step["s06"].retrieved_chunk_ids  # tap: re-ranker
    # The Cleaning Procedure is extracted as the document procedure, so every hand-washing step sees it.
    assert {c.chunk_id for p in report.sop_procedure for c in p.citations} & target
    for sid in ("s01", "s02", "s03", "s04", "s05", "s06"):
        assert target & set(by_step[sid].context_chunk_ids), sid
    assert any(n.kind == "conflict" for n in by_step["s03"].notes)
    print(f"food code: {len(index.chunks)} chunks, stage {elapsed:.0f}s")
