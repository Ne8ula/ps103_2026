"""Deterministic, model-neutral plain-text rendering of a gesture keyframe."""

from __future__ import annotations

import math

from ..schemas.gestures import HandDescription
from .geometry import FINGER_NAMES, LONG_FINGERS, direction8

GRIP_WORDS = {
    "open": "open hand", "pinch": "pinch grip", "power_grip": "power grip", "point": "point gesture",
    "fist": "fist", "relaxed": "relaxed hand", "unknown": "unclear grip",
}
PALM_WORDS = {"camera": "palm facing camera", "away": "palm facing away", "side": "palm sideways"}
LOW_CONF_WORDS = {
    "low_score": "partly hidden or unclear", "out_of_frame": "partly out of frame", "too_small": "too small to read",
    "implausible_shape": "unstable tracking", "jitter": "unstable tracking", "jump": "unstable tracking",
}
INTERACTION_WORDS = {"hands_apart": "Hands apart.", "hands_close": "Hands close together.", "hands_touching": "Hands touching."}


def _join(names: list[str]) -> str:
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


def _mean_dir(degs: list[float]) -> str | None:
    if not degs:
        return None
    x = sum(math.cos(math.radians(d)) for d in degs)
    y = sum(math.sin(math.radians(d)) for d in degs)
    if math.hypot(x, y) < 1e-6 * len(degs):
        return None
    return direction8(math.degrees(math.atan2(y, x)))


def region(position: list[float]) -> str:
    """3 x 3 image region of a normalized [x, y] point (y down)."""
    x, y = position
    col = "left" if x < 1 / 3 else "right" if x > 2 / 3 else "centre"
    row = "top" if y < 1 / 3 else "bottom" if y > 2 / 3 else "middle"
    if row == "middle":
        return "centre" if col == "centre" else f"{col} side"
    return row if col == "centre" else f"{row}-{col}"


def finger_clauses(h: HandDescription) -> list[str]:
    """Paper-style finger description: groups with their direction, then single fingers, then half-bent and curled."""
    by = {f.name: f for f in h.fingers}
    grouped = {n for grp in h.groups for n in grp}
    clauses: list[str] = []
    for grp in h.groups:
        d = _mean_dir([by[n].direction_deg for n in grp if by[n].direction_deg is not None])
        clauses.append("+".join(grp) + " together" + (f" pointing {d}" if d else ""))
    ext = [n for n in FINGER_NAMES if by[n].state == "extended" and n not in grouped]
    spread_longs = [n for n in LONG_FINGERS if n in ext]
    if len(spread_longs) == 4:
        d = _mean_dir([by[n].direction_deg for n in spread_longs if by[n].direction_deg is not None])
        clauses.append("fingers spread" + (f" pointing {d}" if d else ""))
        ext = [n for n in ext if n == "thumb"]
    for n in ext:
        d = by[n].direction
        clauses.append(f"{'thumb out' if n == 'thumb' else n + ' extended'}" + (f" pointing {d}" if d else ""))
    partial = [n for n in FINGER_NAMES if by[n].state == "partial" and n not in grouped]
    if partial:
        clauses.append(f"{_join(partial)} half-bent")
    curled = [n for n in FINGER_NAMES if by[n].state == "curled"]
    if len(curled) == 5:
        clauses.append("all fingers curled")
    elif curled:
        clauses.append(f"{_join(curled)} curled")
    return clauses


def trajectory_phrase(h: HandDescription) -> str | None:
    tr = h.trajectory
    if tr is None:
        return None
    if tr.speed == "still":
        return "holding position"
    if tr.direction is None:
        return f"moving in place, {tr.speed}"
    return f"moving {tr.direction}, {tr.speed}"


def hand_text(h: HandDescription) -> str:
    name = f"{h.handedness} hand"
    if h.visibility == "not_visible":
        return f"{name}: not visible."
    parts: list[str]
    if h.visibility == "low_confidence":
        parts = [f"unclear ({LOW_CONF_WORDS.get(h.visibility_reason or '', 'low confidence')})"]
    else:
        parts = [GRIP_WORDS[h.grip]]
        if h.palm_facing in PALM_WORDS:
            parts.append(PALM_WORDS[h.palm_facing])
        parts += finger_clauses(h)
    if h.position is not None:
        parts.append(f"at {region(h.position)}")
    text = f"{name}: " + ", ".join(parts)
    if tp := trajectory_phrase(h):
        text += f"; {tp}"
    return text + "."


def keyframe_text(t: float, hands: list[HandDescription], interaction: str, activity: str) -> str:
    body = [hand_text(h) for h in hands]
    if not any(h.visibility != "not_visible" for h in hands):
        body.append("No hands visible.")
    if interaction in INTERACTION_WORDS:
        body.append(INTERACTION_WORDS[interaction])
    body.append("Active." if activity == "active" else "Idle.")
    return f"t={t:.1f}s | " + " ".join(body)
