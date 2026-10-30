"""Deterministic clip layout from a structured step: timed callouts and their link to sub-steps.

No LLM is involved (free-tier budgets are tight and nothing here needs judgement that the step does not
already carry):

- items: the step's tools and materials as one short chip at the start of the clip;
- emphasis: each sub-step's emphasis, from its time, for ``emphasis_s``;
- safety: the step's compliance notes (requirement / caution / conflict) as callout cards, verbatim
  note text, linked by note id to the sub-step whose caption shares the most words with the note
  (the first sub-step on a tie), severest first, at most ``max_safety`` per step.
"""

from __future__ import annotations

import re

from ..schemas.compliance import ComplianceNote
from ..schemas.steps import Step
from ..schemas.tutorial import Callout
from ..steps.substeps import bound_text

SAFETY_KINDS = ("conflict", "requirement", "caution")
SEVERITY_ORDER = {"critical": 0, "warning": 1, "info": 2}
STOP = set("the a an and or of to in on for with is are be your you it this that at by as from should must".split())


def _words(text: str) -> set[str]:
    return {w.rstrip("s") for w in re.findall(r"[a-z]{3,}", text.lower()) if w not in STOP}


def link_substep(step: Step, note: ComplianceNote) -> int | None:
    if not step.substeps:
        return None
    words = _words(note.text)
    scores = [len(words & _words(f"{s.caption} {s.emphasis or ''}")) for s in step.substeps]
    best = max(range(len(scores)), key=lambda k: (scores[k], -k))
    return best


def callouts(step: Step, notes: list[ComplianceNote], *, emphasis_s: float = 2.5, items_s: float = 3.0,
             max_safety: int = 2, items_chars: int = 48) -> list[Callout]:
    out: list[Callout] = []
    items = [*step.tools, *step.materials]
    if items:
        text = bound_text("Uses: " + " · ".join(dict.fromkeys(i.strip() for i in items if i.strip())), items_chars)
        out.append(Callout(kind="items", text=text, start=step.start, end=round(min(step.start + items_s, step.end), 3)))
    for k, s in enumerate(step.substeps):
        if not s.emphasis:
            continue
        t0 = s.emphasis_t if s.emphasis_t is not None else s.start
        t1 = min(t0 + emphasis_s, s.end)
        t0 = max(s.start, min(t0, t1 - min(emphasis_s, s.end - s.start)))
        out.append(Callout(kind="emphasis", text=s.emphasis, start=round(t0, 3), end=round(t1, 3), substep=k))
    safety = sorted((n for n in notes if n.kind in SAFETY_KINDS), key=lambda n: SEVERITY_ORDER.get(n.severity, 3))
    for note in safety[:max_safety]:
        k = link_substep(step, note)
        start, end = (step.substeps[k].start, step.substeps[k].end) if k is not None else (step.start, step.end)
        out.append(Callout(kind="safety", text=note.text, start=start, end=end, severity=note.severity, note_id=note.id,
                           substep=k))
    return out
