"""M9 evaluation: score a finished project against hand labels, optionally with vs. without gesture text.

    python -m tutorialgen.eval <project> eval/<labels>.yaml [--ablation]

--ablation copies the project, sets use_gesture_text: false, re-runs from segment onward (upstream
stages are reused through their fingerprints) and reports both scores side by side. With the fake
LLM the numbers only prove the harness works; real comparisons need the OpenAI provider.
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

import yaml
from pydantic import BaseModel

from . import runner
from .config import load_env_files
from .project import Project
from .schemas import ComplianceReport, QuestionSet, StepList


class Labels(BaseModel):
    video: str
    tolerance_s: float = 2.0
    content: list[float]
    boundaries: list[float]
    optional_boundaries: list[float] = []
    steps: list[dict] = []
    facts: list[list[str]] = []
    expected_questions: list[dict] = []
    expected_citations: list[dict] = []
    expected_notes: list[dict] = []     # {about, any: [keywords]} matched against compliance note text


def boundary_scores(predicted: list[float], labels: Labels) -> dict:
    """Greedy one-to-one matching within the tolerance; predictions near optional boundaries are ignored."""
    tol = labels.tolerance_s
    lo, hi = labels.content
    preds = [t for t in predicted if lo + tol < t < hi - tol]
    preds = [t for t in preds if not any(abs(t - o) <= tol for o in labels.optional_boundaries)]
    unmatched = list(labels.boundaries)
    tp = 0
    errors = []
    for t in sorted(preds):
        best = min(unmatched, key=lambda g: abs(g - t), default=None)
        if best is not None and abs(best - t) <= tol:
            unmatched.remove(best)
            tp += 1
            errors.append(abs(best - t))
    precision = tp / len(preds) if preds else 0.0
    recall = tp / len(labels.boundaries) if labels.boundaries else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"predicted": len(preds), "true_positives": tp, "precision": round(precision, 3), "recall": round(recall, 3),
            "f1": round(f1, 3), "mean_abs_error_s": round(sum(errors) / len(errors), 2) if errors else None}


def evaluate(project: Project, labels: Labels) -> dict:
    steps = project.read("refine/steps.json", StepList)
    starts = [s.start for s in steps.steps[1:]]
    text = " ".join(
        " ".join([s.title, s.instruction, *s.details, *s.cautions, *s.user_supplied, s.expected_result or ""])
        for s in steps.steps
    ).lower()
    facts = [any(alt.lower() in text for alt in alts) for alts in labels.facts]

    result: dict = {
        "steps": len(steps.steps),
        "labelled_steps": len(labels.steps),
        "boundaries": boundary_scores(starts, labels),
        "facts_stated": f"{sum(facts)}/{len(facts)}",
        "facts_missing": [alts[0] for alts, ok in zip(labels.facts, facts) if not ok],
    }

    if project.exists("questions/questions.json"):
        qs = project.read("questions/questions.json", QuestionSet).questions
        open_qs = [q for q in qs if q.status == "open"]
        qtext = [f"{q.text} {q.why}".lower() for q in open_qs]
        hits = [any(any(k in t for k in e["any"]) for t in qtext) for e in labels.expected_questions]
        result["questions"] = {
            "open": len(open_qs),
            "blocking": sum(q.blocking for q in open_qs),
            "expected_raised": f"{sum(hits)}/{len(hits)}",
            "expected_missing": [e["about"] for e, ok in zip(labels.expected_questions, hits) if not ok],
        }

    if project.exists("compliance/compliance.json"):
        report = project.read("compliance/compliance.json", ComplianceReport)
        notes = [n for s in report.steps for n in s.notes] + report.global_notes
        pages = {c.page for n in notes for c in n.citations}
        result["compliance"] = {
            "notes": len(notes),
            "conflicts": sum(n.kind == "conflict" for n in notes),
            "missing_steps": sum(n.kind == "missing_step" for n in notes),
            "steps_without_guidance": sum(s.no_relevant_guidance for s in report.steps),
            "expected_citations_found": f"{sum(e['page'] in pages for e in labels.expected_citations)}/{len(labels.expected_citations)}",
            "dropped_by_validation": len(report.dropped),
        }
        if labels.expected_notes:
            texts = [n.text.lower() for n in notes]
            hits = [any(any(k in t for k in e["any"]) for t in texts) for e in labels.expected_notes]
            result["compliance"]["expected_notes_found"] = f"{sum(hits)}/{len(hits)}"
            result["compliance"]["expected_notes_missing"] = [e["about"] for e, ok in zip(labels.expected_notes, hits) if not ok]
    providers = {json.loads(p.read_text()).get("provider") for p in project.path("llm_cache").glob("*.json")}
    result["llm"] = sorted(p for p in providers if p)
    return result


def ablation_copy(project: Project) -> Project:
    dest = project.root.with_name(project.root.name + "-nogesture")
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(project.root, dest, ignore=shutil.ignore_patterns("render"))
    config = yaml.safe_load((dest / "config.yaml").read_text()) if (dest / "config.yaml").exists() else {}
    config = config or {}
    config["use_gesture_text"] = False
    (dest / "config.yaml").write_text(yaml.safe_dump(config))
    copy = Project(dest)
    copy.manifest.id = dest.name
    copy.save_manifest()
    return copy


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="tutorialgen.eval", description=__doc__)
    ap.add_argument("project")
    ap.add_argument("labels")
    ap.add_argument("--ablation", action="store_true", help="also score a copy run without gesture text")
    args = ap.parse_args(argv)
    load_env_files()
    project = Project.load(args.project)
    labels = Labels.model_validate(yaml.safe_load(Path(args.labels).read_text()))
    out = {"with_gesture_text": evaluate(project, labels)}
    if args.ablation:
        copy = ablation_copy(project)
        runner.run(copy, until="questions")
        out["without_gesture_text"] = evaluate(copy, labels)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
