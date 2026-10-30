"""Keyframe selection (debounced state changes, speed changes, max interval, min gap) and keyframe assembly."""

from __future__ import annotations

from typing import Hashable

import numpy as np

from ..schemas.gestures import GestureKeyframe, HandDescription, Trajectory
from .config import GestureConfig
from .geometry import direction8, direction_deg
from .text import keyframe_text
from .timeline import HANDS, FrameObs, speed_bucket

VERSION = "gesture_text/1.0"


def debounce(values: list[Hashable], n: int) -> list[Hashable]:
    """A new value is adopted from the start of its run, but only if the run lasts >= n samples.
    Before the first such run, the first long run's value is used (no start-up artifacts)."""
    if not values:
        return []
    runs: list[tuple[Hashable, int]] = []
    for v in values:
        if runs and runs[-1][0] == v:
            runs[-1] = (v, runs[-1][1] + 1)
        else:
            runs.append((v, 1))
    stable = next((v for v, k in runs if k >= n), values[0])
    out: list[Hashable] = []
    for v, k in runs:
        if k >= n:
            stable = v
        out.extend([stable] * k)
    return out


def _changes(values: list[Hashable], n: int, known=lambda v: True) -> set[int]:
    """Indices where the debounced value changes between two 'known' values."""
    stable = debounce(values, n)
    return {i for i in range(1, len(stable))
            if stable[i] != stable[i - 1] and known(stable[i]) and known(stable[i - 1])}


def state_events(timeline: list[FrameObs], cfg: GestureConfig) -> dict[int, set[str]]:
    """frame index -> reasons, from debounced per-hand and global state sequences."""
    n = cfg.debounce_frames
    events: dict[int, set[str]] = {}

    def add(idx: set[int], reason: str) -> None:
        for i in idx:
            events.setdefault(i, set()).add(reason)

    for label in HANDS:
        hands = [fo.hands.get(label) for fo in timeline]
        add(_changes([h.visibility if h else "absent" for h in hands], n), "visibility_change")
        add(_changes([h.grip if h else "unknown" for h in hands], n, lambda v: v != "unknown"), "grip_change")
        add(_changes([tuple(f.state for f in h.fingers) if h and h.visibility == "visible" else None for h in hands],
                     n, lambda v: v is not None), "finger_change")
        add(_changes([speed_bucket(h.speed, cfg) if h else None for h in hands], cfg.motion_debounce_frames,
                     lambda v: v is not None), "speed_change")
    add(_changes([fo.interaction for fo in timeline], n), "interaction_change")
    add(_changes([fo.activity for fo in timeline], cfg.motion_debounce_frames), "activity_change")
    return events


def select_keyframes(timeline: list[FrameObs], cfg: GestureConfig) -> list[tuple[int, list[str]]]:
    """(frame index, sorted reasons). Events within min_gap_s of the last keyframe are postponed, not dropped."""
    events = state_events(timeline, cfg)
    selected: list[tuple[int, list[str]]] = []
    pending: set[str] = set()
    last_t: float | None = None
    for i, fo in enumerate(timeline):
        pending |= events.get(i, set())
        any_hand = bool(fo.hands)
        if last_t is None:
            if any_hand:
                pending.add("start")
            else:
                pending.clear()
        elif any_hand and fo.t - last_t >= cfg.max_interval_s - 1e-9:
            pending.add("interval")
        if pending and (last_t is None or fo.t - last_t >= cfg.min_gap_s - 1e-9):
            selected.append((i, sorted(pending)))
            pending = set()
            last_t = fo.t
    return selected


def build_keyframes(timeline: list[FrameObs], cfg: GestureConfig) -> list[GestureKeyframe]:
    out: list[GestureKeyframe] = []
    last_seen: dict[str, float] = {}
    prev_kf: dict[str, tuple[float, np.ndarray, int]] = {}  # label -> (t, centre, timeline index)
    seen_until = 0
    for n, (i, reasons) in enumerate(select_keyframes(timeline, cfg), start=1):
        for fo in timeline[seen_until:i]:
            for label in fo.hands:
                last_seen[label] = fo.t
        seen_until = i
        fo = timeline[i]
        hands: list[HandDescription] = []
        for label in HANDS:
            o = fo.hands.get(label)
            if o is None:
                if label in last_seen and fo.t - last_seen[label] <= cfg.not_visible_memory_s:
                    hands.append(HandDescription(handedness=label, visibility="not_visible"))
                continue
            traj = None
            if label in prev_kf:
                t0, c0, i0 = prev_kf[label]
                traj = _trajectory(timeline, label, t0, c0, i0, i, o.centre, cfg)
            hands.append(HandDescription(
                handedness=label, visibility=o.visibility, visibility_reason=o.reason, fingers=o.fingers,
                groups=o.groups, grip=o.grip, palm_facing=o.palm_facing, position=o.position, trajectory=traj))
            prev_kf[label] = (fo.t, o.centre, i)
        out.append(GestureKeyframe(
            id=f"g{n:04d}", frame=fo.frame, t=round(fo.t, 3), reasons=reasons, hands=hands,
            interaction=fo.interaction, activity=fo.activity,
            text=keyframe_text(fo.t, hands, fo.interaction, fo.activity)))
    return out


def _trajectory(timeline: list[FrameObs], label: str, t0: float, c0: np.ndarray, i0: int, i: int,
                centre: np.ndarray, cfg: GestureConfig) -> Trajectory:
    """Net palm displacement since the hand's previous keyframe; speed = mean windowed speed over the interval."""
    delta = centre - c0
    dist = float(np.linalg.norm(delta))
    speeds = [fo.hands[label].speed for fo in timeline[i0 + 1:i + 1]
              if label in fo.hands and fo.hands[label].speed is not None]
    t = timeline[i].t
    mean_speed = float(np.mean(speeds)) if speeds else dist / max(t - t0, 1e-9)
    return Trajectory(since_t=round(t0, 3), direction=direction8(direction_deg(delta)) if dist >= cfg.min_move else None,
                      distance=round(dist, 4), speed=speed_bucket(mean_speed, cfg))
