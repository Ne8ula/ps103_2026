"""Retrieval + note benchmark for the compliance stage (RAG over the FDA Food Code).

Hand-written hand-washing steps (the same ones as the slow test in tests/test_compliance.py, with a
deliberate "rub 5 seconds" conflict and an unrelated "wave goodbye" control step) are checked against
samples/data/fda-food-code-2022.pdf. Reports, per step:

- rank of the §2-301.12 Cleaning Procedure chunk in the step's full retrieval ranking;
- whether that chunk (or its sentences) reaches the LLM context;
- notes produced, conflicts, whether a note cites the target chunk;

and in total: notes, conflicts, proposed vs. valid citations, drops, missing-step notes, LLM calls.

Usage (from pipeline/):

    python eval/rag_compliance_bench.py --home /tmp/bench --index <dir with chunks.json/embeddings.npy/manifest.json> \
        [--llm fake|gemini] [--out results.json] [--set compliance.top_k=6 ...]

``--index`` reuses an already-built Food Code index (embedding the 668 pages takes ~5 min on CPU);
if its manifest does not match the current chunking it is rebuilt (and ``--save-index`` keeps it).
The default LLM is the deterministic fake provider, so retrieval numbers are exact and note numbers
measure the plumbing; ``--llm gemini`` measures a live model (respect the free-tier quota).
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import shutil
import sys
from pathlib import Path

PIPELINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PIPELINE))

from tutorialgen.config import Config  # noqa: E402
from tutorialgen.llm import CachedLLM, make_provider  # noqa: E402
from tutorialgen.project import Project  # noqa: E402
from tutorialgen.schemas import ComplianceReport, DocIndex, Step, StepList  # noqa: E402
from tutorialgen.stages import StageContext  # noqa: E402
from tutorialgen.stages import compliance as compliance_stage  # noqa: E402

PDF = PIPELINE / "samples" / "data" / "fda-food-code-2022.pdf"
CONFLICT_STEP = "s03"
CONTROL_STEP = "s07"

STEPS = [
    ("Wet hands", "Wet both hands under running water.", [], []),
    ("Apply soap", "Apply a pump of liquid soap to your palms.", [], ["liquid soap"]),
    ("Scrub hands", "Rub hands together for 5 seconds, including backs of hands, between fingers and under nails.", [], []),
    ("Rinse hands", "Rinse the soap off your hands under running water.", [], []),
    ("Dry hands", "Dry your hands with a paper towel.", [], ["paper towel"]),
    ("Turn off tap", "Turn off the faucet using the paper towel.", [], ["paper towel"]),
    ("Wave goodbye", "Smile and wave at the camera.", [], []),
]


def bench_steps() -> StepList:
    return StepList(revision=0, steps=[
        Step(id=f"s{i + 1:02d}", index=i, start=i * 4.0, end=i * 4.0 + 4, title=t, instruction=ins, tools=tools,
             materials=mats, confidence=0.8) for i, (t, ins, tools, mats) in enumerate(STEPS)])


def is_target(c) -> bool:
    return bool(c.section and c.section.startswith("2-301.12") and "(3) Rub together" in c.text)


def _parse_set(items: list[str]) -> dict:
    out: dict = {}
    for item in items:
        key, value = item.split("=", 1)
        node = out
        *path, last = key.split(".")
        for k in path:
            node = node.setdefault(k, {})
        node[last] = json.loads(value) if value[:1] in "[{0123456789-tfn\"" else value
    return out


def _count_citations(obj) -> int:
    if isinstance(obj, dict):
        return int("chunk_id" in obj) + sum(_count_citations(v) for v in obj.values())
    if isinstance(obj, list):
        return sum(_count_citations(v) for v in obj)
    return 0


_CITE_DROP = re.compile(r"citation to|quote not found|sentence", re.I)


def run(args) -> dict:
    p = Project.create("rag bench", Path(args.home))
    p.add_document(PDF, name="FDA Food Code 2022")
    p.write("refine/steps.json", bench_steps())
    if args.index:
        shutil.copytree(args.index, p.path(compliance_stage.INDEX_DIR))
    overrides = {"embeddings": {"provider": "local"}, "llm": {"provider": args.llm}}
    if args.llm == "gemini" and args.model:
        overrides["llm"]["model"] = args.model
    overrides = _merge(overrides, _parse_set(args.set))
    config = p.config(overrides)
    llm = CachedLLM(make_provider(config), p.path("llm_cache"))
    ctx = StageContext(project=p, config=config, llm=llm, log=logging.getLogger("bench"))
    compliance_stage.run(ctx)
    report = p.read(compliance_stage.REPORT, ComplianceReport)
    index = p.read(f"{compliance_stage.INDEX_DIR}/chunks.json", DocIndex)
    target_ids = {c.id for c in index.chunks if is_target(c)}

    rankings = _rankings(ctx, p)
    calls = [json.loads(f.read_text()) for f in sorted(p.path("llm_cache").glob("*.json"))] if p.exists("llm_cache") else []
    stats = getattr(report, "citation_stats", None) or {}
    if stats:
        proposed, cite_drops = stats["proposed_citations"], stats["invalid_citations"]
    else:  # legacy report: count from the recorded responses and the drop messages
        proposed = sum(_count_citations(c["response"]) for c in calls if c["task"].startswith("compliance"))
        cite_drops = sum(bool(_CITE_DROP.search(d)) for d in report.dropped)

    steps_out = []
    for sc in report.steps:
        ranking = rankings.get(sc.step_id, [])
        rank = next((i + 1 for i, cid in enumerate(ranking) if cid in target_ids), None)
        pinned = set(getattr(sc, "context_chunk_ids", None) or [])
        steps_out.append({
            "step_id": sc.step_id,
            "target_rank": rank,
            "target_in_context": bool(target_ids & (set(sc.retrieved_chunk_ids) | pinned)),
            "notes": len(sc.notes),
            "kinds": [n.kind for n in sc.notes],
            "cites_target": any(c.chunk_id in target_ids for n in sc.notes for c in n.citations),
            "texts": [n.text for n in sc.notes],
        })
    all_notes = [n for sc in report.steps for n in sc.notes]
    valid_citations = sum(len(n.citations) for n in all_notes + report.global_notes)
    summary = {
        "target_chunks": sorted(target_ids),
        "chunks": len(index.chunks),
        "llm": llm.label,
        "llm_calls": len(calls),
        "notes": len(all_notes),
        "global_notes": len(report.global_notes),
        "conflicts": [n.step_id for n in all_notes if n.kind == "conflict"],
        "conflict_on_expected_step": any(n.kind == "conflict" for n in all_notes if n.step_id == CONFLICT_STEP),
        "control_step_notes": sum(len(sc.notes) for sc in report.steps if sc.step_id == CONTROL_STEP),
        "proposed_citations": proposed,
        "valid_citations_kept": valid_citations,
        "citation_drops": cite_drops,
        "citation_validity": round(1 - cite_drops / proposed, 3) if proposed else None,
        "drops": len(report.dropped),
        "dropped": report.dropped,
        "steps_in_context": sum(s["target_in_context"] for s in steps_out if s["step_id"] != CONTROL_STEP),
        "steps_citing_target": sum(s["cites_target"] for s in steps_out if s["step_id"] != CONTROL_STEP),
        "mean_target_rank": _mean([s["target_rank"] for s in steps_out if s["step_id"] != CONTROL_STEP]),
        "missing_step_notes": [n.text for n in report.global_notes],
        "sop_procedure": [f"{p.id} [{p.status}: {', '.join(p.video_step_ids)}] {p.action}"
                          for p in getattr(report, "sop_procedure", [])],
    }
    if args.save_index and not args.index:
        shutil.copytree(p.path(compliance_stage.INDEX_DIR), args.save_index, dirs_exist_ok=True)
    return {"summary": summary, "steps": steps_out, "project": str(p.root)}


def _rankings(ctx: StageContext, p: Project) -> dict[str, list[str]]:
    """Full per-step chunk ranking (the order the stage would take its top_k from)."""
    steps = p.read("refine/steps.json", StepList).steps
    if hasattr(compliance_stage, "rank_steps"):
        return compliance_stage.rank_steps(ctx, steps, depth=200)
    # Legacy stage: plain step query, hybrid BM25 + dense with RRF.
    from tutorialgen.rag import EmbeddingSettings, HybridRetriever, make_embedder, step_query
    from tutorialgen.rag.index import Index, IndexManifest
    import numpy as np

    d = p.path(compliance_stage.INDEX_DIR)
    index = Index(DocIndex.model_validate_json((d / "chunks.json").read_text()), np.load(d / "embeddings.npy"),
                  IndexManifest.model_validate_json((d / "manifest.json").read_text()), False)
    retriever = HybridRetriever(index, make_embedder(ctx.config.section("embeddings", EmbeddingSettings)), pool=200)
    hits = retriever.search([step_query(s) for s in steps], 200)
    return {s.id: [h.chunk.id for h in hs] for s, hs in zip(steps, hits)}


def _mean(xs: list[int | None], missing: int = 201) -> float:
    vals = [x if x is not None else missing for x in xs]
    return round(sum(vals) / len(vals), 1) if vals else 0.0


def _merge(a: dict, b: dict) -> dict:
    out = dict(a)
    for k, v in b.items():
        out[k] = _merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--home", required=True, help="scratch projects folder")
    ap.add_argument("--index", help="existing compliance/index dir to reuse")
    ap.add_argument("--save-index", help="copy the (re)built index here")
    ap.add_argument("--llm", default="fake")
    ap.add_argument("--model")
    ap.add_argument("--set", action="append", default=[], help="config override, e.g. compliance.top_k=8")
    ap.add_argument("--out")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    result = run(args)
    s = result["summary"]
    print(f"\n{'step':5} {'rank':>5} {'ctx':>4} {'notes':>5} {'cites§':>6}  kinds")
    for st in result["steps"]:
        print(f"{st['step_id']:5} {str(st['target_rank']):>5} {('yes' if st['target_in_context'] else 'no'):>4} "
              f"{st['notes']:>5} {('yes' if st['cites_target'] else 'no'):>6}  {', '.join(st['kinds'])}")
    for k, v in s.items():
        if k not in ("dropped",):
            print(f"{k}: {v}")
    if args.out:
        Path(args.out).write_text(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
