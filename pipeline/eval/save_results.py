"""Score the committed projects against their hand labels and save the results next to the labels.

    python eval/save_results.py        # writes eval/results/<project>.json

Each result records which labels and which LLM produced it, so numbers from different runs are not mixed up.
"""

from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path

import yaml

from tutorialgen.eval import Labels, evaluate
from tutorialgen.project import Project
from tutorialgen.schemas import EditDecisionList

PIPELINE = Path(__file__).resolve().parents[1]
RUNS = [
    # (project folder, labels file, what the run is)
    ("projects/hand-washing-sfdph-a3c265", "sfdph-wash-hands-en.yaml", "edited PSA, fake LLM (placeholder text)"),
    ("projects/hand-washing-sfdph-a3c265-nogesture", "sfdph-wash-hands-en.yaml", "edited PSA, fake LLM, gesture text off"),
    ("projects/hand-washing-gemini-7c839f", "sfdph-wash-hands-en.yaml", "edited PSA, Gemini free tier"),
    ("projects/x1c-wiper-mod-livestream-a21371", "x1c-steinwipe-livestream.yaml", "uncut livestream, Gemini, before expert answers"),
    ("demo/capture/home/x1c-wiper-mod-livestream-a21371", "x1c-steinwipe-livestream.yaml", "uncut livestream, Gemini, after expert answers"),
]


def main() -> None:
    out_dir = PIPELINE / "eval" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    for folder, labels_file, note in RUNS:
        root = PIPELINE / folder
        if not (root / "project.json").exists():
            print(f"skip {folder}: not found")
            continue
        project = Project(root)
        labels = Labels.model_validate(yaml.safe_load((PIPELINE / "eval" / labels_file).read_text()))
        with contextlib.redirect_stderr(io.StringIO()):
            result = evaluate(project, labels)
        if project.exists("edit/edl.json"):
            edl = project.read("edit/edl.json", EditDecisionList)
            result["edit"] = {"enabled": edl.enabled, "step_seconds": edl.source_s, "kept_seconds": edl.output_s}
        name = folder.replace("demo/capture/home/", "").replace("projects/", "") + ("-reviewed" if folder.startswith("demo/") else "")
        (out_dir / f"{name}.json").write_text(json.dumps({"project": folder, "labels": labels_file, "run": note, **result}, indent=2) + "\n")
        print(f"{name}: steps {result['steps']}, boundary F1 {result['boundaries']['f1']}, facts {result['facts_stated']}")


if __name__ == "__main__":
    main()
