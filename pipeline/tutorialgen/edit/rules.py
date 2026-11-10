"""Fixed rules from labels to actions, and the guards that undo unsafe cuts."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from ..schemas.edit import EditUnit
from ..schemas.steps import Step
from ..steps.guards import numbers_in
from .units import Unit


class EditConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = True                 # false = keep every step's full range (render plays it as before)
    use_llm: bool = True                 # false = spoken lines are kept without labels
    line_max_s: float = 6.0              # spoken lines: at most this long ...
    line_max_words: int = 12             # ... or this many words, split at pauses longer than line_gap_s
    line_gap_s: float = 0.8
    absorb_gap_s: float = 0.4            # gaps shorter than this stay with the neighbouring line
    min_cut_s: float = 1.5               # never cut or speed up a unit shorter than this (no jump cuts)
    idle_hands: float = 0.1              # a gap is idle when hands are seen in less than this share of samples ...
    idle_motion: float = 0.15            # ... and pixel motion (95th percentile = 1) stays below this
    speed_after_s: float = 8.0           # silent task stretches longer than this play faster
    speedup: int = 3                     # integer frame stride for sped-up units (audio is muted there)
    active_hands: float = 0.3            # an aside counts as "hands still working" above this hand share ...
    active_motion: float = 0.3           # ... or this motion; then it is sped up instead of cut
    min_step_s: float = 3.0              # every step keeps at least this much output
    motion_fps: float = 4.0
    units_per_call: int = 60


def gap_label(u: Unit, cfg: EditConfig) -> str:
    return "idle" if u.hands < cfg.idle_hands and u.motion < cfg.idle_motion else "task"


def action_for(u: Unit, label: str, cfg: EditConfig) -> tuple[str, float, str]:
    """(action, speed, reason) from the label and the unit's evidence."""
    long_enough = u.duration >= cfg.min_cut_s
    working = u.hands >= cfg.active_hands or u.motion >= cfg.active_motion
    if label == "idle":
        return ("cut", 1.0, "nothing happens: no hands and little motion") if long_enough else ("keep", 1.0, "short pause")
    if label == "aside":
        if not long_enough:
            return "keep", 1.0, "short aside"
        if working:
            return "speed", float(cfg.speedup), "off-topic talk while the work continues: shown faster, muted"
        return "cut", 1.0, "off-topic talk with no work on screen"
    if label == "task" and u.kind == "gap" and u.duration >= cfg.speed_after_s:
        return "speed", float(cfg.speedup), f"long silent stretch of work: {cfg.speedup}x"
    return "keep", 1.0, {"task": "doing the task", "result": "shows the result", "explain": "needed explanation"}.get(label, "kept")


def step_output_seconds(units: list[EditUnit]) -> float:
    return sum((u.end - u.start) / (u.speed if u.action == "speed" else 1.0) for u in units if u.action != "cut")


def apply_rules(step: Step, units: list[Unit], labels: dict[str, tuple[str, str]], cfg: EditConfig) -> list[EditUnit]:
    """Label every unit (LLM labels for speech, rules for gaps), pick actions, then run the guards."""
    out: list[EditUnit] = []
    for u in units:
        if u.kind == "gap":
            label, source = gap_label(u, cfg), "rule"
        elif u.id in labels:
            label, source = labels[u.id][0], "llm"
        else:
            label, source = "explain", "default"
        action, speed, reason = action_for(u, label, cfg)
        if source == "llm" and labels[u.id][1]:
            reason = f"{reason} ({labels[u.id][1]})"
        out.append(EditUnit(id=u.id, start=u.start, end=u.end, kind=u.kind, text=u.text, hands=u.hands, motion=u.motion,
                            label=label, label_source=source, action=action, speed=speed, reason=reason))
    by_id = {u.id: u for u in units}

    # Guard 1: every number the step states keeps a unit where it was said.
    stated = " ".join([step.title, step.instruction, *step.details, *(s.caption for s in step.substeps)])
    for value in numbers_in(stated):
        sources = [e for e in out if value in by_id[e.id].numbers]
        if sources and not any(e.action == "keep" for e in sources):
            first = sources[0]
            first.action, first.speed, first.restored_by = "keep", 1.0, f"states {value:g}, which the step uses"

    # Guard 2: a spoken number is never cut or muted, whatever the label (sizes, positions, counts).
    for e in out:
        if e.action != "keep" and by_id[e.id].numbers:
            e.action, e.speed, e.restored_by = "keep", 1.0, "says a number"

    # Guard 3: a minimum length per step, restoring the busiest units first.
    if step_output_seconds(out) < cfg.min_step_s:
        for e in sorted((e for e in out if e.action != "keep"), key=lambda e: -(e.hands + e.motion)):
            e.action, e.speed, e.restored_by = "keep", 1.0, "step would be shorter than the minimum"
            if step_output_seconds(out) >= cfg.min_step_s:
                break
    return out
