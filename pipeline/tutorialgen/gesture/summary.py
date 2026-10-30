"""Compact per-interval gesture summaries: one line per time range instead of many keyframe lines.

Computed from every sampled frame (the gesture timeline), not only the keyframes, so fractions are
real: how often each hand is visible, the dominant grip per hand, how often the hands touch, how much of
the time they move, the dominant motion (a net direction, or back-and-forth along an axis, which is
what scrubbing, stirring or sawing looks like), and where in the image the hands are.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

import numpy as np

from .geometry import direction8, direction_deg
from .text import GRIP_WORDS, region
from .timeline import HANDS, FrameObs

AXES = {"right": "left-right", "left": "left-right", "up": "up-down", "down": "up-down",
        "up-right": "diagonal", "down-left": "diagonal", "up-left": "diagonal", "down-right": "diagonal"}


@dataclass
class IntervalSummary:
    samples: int
    both: float
    one: float
    none: float
    grips: dict[str, tuple[str, float]]      # hand -> (dominant grip, share of its visible samples)
    contact: float                           # share of samples with the hands close or touching
    touching: float
    active: float
    motion: str | None                       # e.g. "back-and-forth left-right", "moving down-right"
    where: str | None

    def text(self) -> str:
        if self.samples == 0:
            return "no hand data"
        if self.none >= 0.999:
            return "no hands visible"
        parts = [_pct_join([("both hands", self.both), ("one hand", self.one), ("no hands", self.none)])]
        g = [f"{h[0]}: {GRIP_WORDS.get(grip, grip)}" + (f" {share:.0%}" if share < 0.95 else "")
             for h, (grip, share) in self.grips.items()]
        if g:
            parts.append("grip " + ", ".join(g))
        if self.contact >= 0.1:
            parts.append(f"hands {'touching' if self.touching >= self.contact / 2 else 'close'} {self.contact:.0%}")
        parts.append(f"active {self.active:.0%}" + (f", {self.motion}" if self.motion else ""))
        if self.where:
            parts.append(f"at {self.where}")
        return "; ".join(parts)


def _pct_join(items: list[tuple[str, float]]) -> str:
    return ", ".join(f"{name} {v:.0%}" for name, v in items if v >= 0.05)


def _motion(frames: list[FrameObs], min_move: float) -> str | None:
    """Dominant palm motion of the most visible hand: back-and-forth along an axis, or a net direction."""
    best = None
    for label in HANDS:
        pts = [(fo.t, fo.hands[label].centre) for fo in frames if label in fo.hands and fo.hands[label].visibility == "visible"]
        if len(pts) >= 4 and (best is None or len(pts) > len(best)):
            best = pts
    if best is None:
        return None
    t = np.array([p[0] for p in best])
    xy = np.array([p[1] for p in best])
    steps = np.diff(xy, axis=0)
    moving = np.linalg.norm(steps, axis=1) > min_move / 4
    if moving.sum() < 2:
        return None
    # Principal axis of the frame-to-frame motion; reversals along it mean back-and-forth.
    _, _, vt = np.linalg.svd(steps[moving], full_matrices=False)
    axis = vt[0]
    proj = steps[moving] @ axis
    signs = np.sign(proj[np.abs(proj) > 1e-6])
    reversals = int(np.sum(signs[1:] != signs[:-1])) if len(signs) > 1 else 0
    span = max(t[-1] - t[0], 1e-6)
    net = xy[-1] - xy[0]
    if reversals / span >= 0.8 and reversals >= 2:
        return f"back-and-forth {AXES[direction8(direction_deg(axis))]}"
    if np.linalg.norm(net) >= min_move:
        return f"moving {direction8(direction_deg(net))}"
    return "moving in place"


def summarize(frames: list[FrameObs], min_move: float = 0.02) -> IntervalSummary:
    n = len(frames)
    if n == 0:
        return IntervalSummary(0, 0, 0, 1, {}, 0, 0, 0, None, None)
    counts = [len(fo.hands) for fo in frames]  # detected, including low-confidence (occluded) hands
    grips: dict[str, tuple[str, float]] = {}
    for label in HANDS:
        seen = [fo.hands[label].grip for fo in frames if label in fo.hands and fo.hands[label].visibility == "visible"]
        known = [g for g in seen if g != "unknown"]
        if len(seen) >= max(2, 0.15 * n) and known:
            grip, k = Counter(known).most_common(1)[0]
            grips[label] = (grip, k / len(seen))
    contact = sum(fo.interaction in ("hands_close", "hands_touching") for fo in frames) / n
    touching = sum(fo.interaction == "hands_touching" for fo in frames) / n
    centres = [o.position for fo in frames for o in fo.hands.values() if o.visibility == "visible"]
    where = region(list(np.median(np.array(centres), axis=0))) if centres else None
    return IntervalSummary(
        samples=n, both=sum(c >= 2 for c in counts) / n, one=sum(c == 1 for c in counts) / n,
        none=sum(c == 0 for c in counts) / n, grips=grips, contact=contact, touching=touching,
        active=sum(fo.activity == "active" for fo in frames) / n, motion=_motion(frames, min_move), where=where,
    )
