"""Sub-step anchors (times an action phase may start at) and validation of the LLM's sub-steps.

The model proposes phases with a start time, a caption, a focus box id and an optional emphasis.
Code owns everything structural: times snap to anchors (step start, narration starts, hand-state
change keyframes), phases are contiguous and at least ``min_s`` long, captions are bounded, box ids
must be ones that were offered (else a deterministic fallback, marked as such).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ..schemas import FocusBox, GestureKeyframe, SubStep, TranscriptSegment
from .llm_schemas import SubStepOutput

FULL = "full"
DEDUPE_S = 0.75


@dataclass
class Anchor:
    id: str
    t: float
    source: str                  # "step start" | "narration" | "hands: grip change" ...
    keyframe_id: str | None = None


def anchors(start: float, end: float, speech: list[TranscriptSegment], gestures: list[GestureKeyframe],
            limit: int = 10) -> list[Anchor]:
    """Candidate phase starts inside [start, end): step start, narration starts, hand-state changes."""
    raw: list[tuple[float, str, str | None]] = [(start, "step start", None)]
    raw += [(s.start, "narration", None) for s in speech if start < s.start < end]
    for g in gestures:
        reasons = [r.replace("_", " ") for r in g.reasons if r != "interval"]
        if reasons and start < g.t < end:
            raw.append((g.t, "hands: " + ", ".join(reasons), g.id))
    raw.sort(key=lambda x: x[0])
    kept: list[tuple[float, str, str | None]] = []
    for t, src, kid in raw:
        if kept and t - kept[-1][0] < DEDUPE_S:
            if kid and not kept[-1][2]:  # keep the time of the first, remember the keyframe
                kept[-1] = (kept[-1][0], kept[-1][1] + " + " + src, kid)
            continue
        if end - t < DEDUPE_S and kept:
            continue
        kept.append((t, src, kid))
    if len(kept) > limit:  # keep the step start, then evenly spaced
        rest = kept[1:]
        kept = [kept[0]] + [rest[int(k * len(rest) / (limit - 1))] for k in range(limit - 1)]
    return [Anchor(f"a{n + 1}", round(t, 3), src, kid) for n, (t, src, kid) in enumerate(kept)]


def bound_text(text: str | None, max_chars: int) -> str:
    """Collapse whitespace, drop a trailing full stop, and cut at a word boundary to ``max_chars``."""
    text = " ".join((text or "").split()).strip()
    text = re.sub(r"[.;:,]+$", "", text)
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars + 1].rsplit(" ", 1)[0] if " " in text[:max_chars + 1] else text[:max_chars]
    return re.sub(r"[\s,;:–-]+$", "", cut[:max_chars])


def fallback_focus(boxes: list[FocusBox]) -> str:
    ids = {b.id for b in boxes}
    return "B2" if "B2" in ids else "B1" if "B1" in ids else FULL


def build_substeps(out: list[SubStepOutput], start: float, end: float, anchor_list: list[Anchor], boxes: list[FocusBox],
                   gestures: list[GestureKeyframe], *, max_substeps: int = 4, min_s: float = 1.0, snap_s: float = 1.0,
                   caption_chars: int = 44, emphasis_chars: int = 24, default_caption: str = "") -> list[SubStep]:
    """Validated, contiguous sub-steps covering [start, end]. Never empty."""
    valid_ids = {b.id for b in boxes} | {FULL}
    times = [a.t for a in anchor_list] or [start]

    def snap(t: float) -> float:
        t = min(max(float(t), start), end)
        near = min(times, key=lambda a: abs(a - t))
        return near if abs(near - t) <= snap_s else round(t, 3)

    items = sorted(((snap(o.start_s), o) for o in out), key=lambda x: x[0])
    phases: list[tuple[float, SubStepOutput | None]] = []
    for t, o in items:
        if not phases:
            phases.append((start, o))  # the first phase always starts at the step start
        elif t - phases[-1][0] >= min_s and end - t >= min_s:
            phases.append((t, o))
        if len(phases) >= max_substeps:
            break
    if not phases:
        phases = [(start, None)]

    result: list[SubStep] = []
    for k, (t, o) in enumerate(phases):
        t_end = phases[k + 1][0] if k + 1 < len(phases) else end
        caption = bound_text(o.caption if o else "", caption_chars) or bound_text(default_caption, caption_chars)
        focus, source = (o.focus_box.strip() if o else ""), "llm"
        if focus.lower() == FULL:
            focus = FULL
        if focus not in valid_ids:
            focus, source = fallback_focus(boxes), "fallback"
        emphasis = bound_text(o.emphasis, emphasis_chars) if o and o.emphasis else None
        emphasis_t = None
        if emphasis:
            emphasis_t = round(min(max(o.emphasis_s if o.emphasis_s is not None else t, t), max(t, t_end - 0.5)), 3)
        result.append(SubStep(start=round(t, 3), end=round(t_end, 3), caption=caption, focus=focus, focus_source=source,
                              emphasis=emphasis or None, emphasis_t=emphasis_t,
                              gesture_keyframe_ids=[g.id for g in gestures if t <= g.t < t_end]))
    return result
