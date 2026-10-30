"""Per-frame hand observations over time: visibility filtering, palm speed, shape change, interaction, activity."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from ..schemas.gestures import FingerState
from ..schemas.media import Hand, HandFrame
from . import geometry as g
from .config import GestureConfig

HANDS = ("Right", "Left")  # rendering order


@dataclass
class HandObs:
    """One detected hand in one frame, with every per-frame feature."""

    label: str
    score: float
    raw: np.ndarray                 # 21 x 3 normalized image landmarks
    iso: np.ndarray                 # 21 x 3 isotropic, diag units
    palm: float                     # palm size, diag units
    centre: np.ndarray              # palm centre, iso xy
    position: list[float]           # palm centre, normalized image [x, y]
    visibility: str = "visible"     # visible | low_confidence
    reason: str | None = None       # why low_confidence
    fingers: list[FingerState] = field(default_factory=list)
    groups: list[list[str]] = field(default_factory=list)
    grip: str = "unknown"
    palm_facing: str = "unknown"
    speed: float | None = None      # palm-centre speed over speed_window_s, diag/s
    shape_rate: float | None = None  # hand-shape change over speed_window_s, palm sizes/s


@dataclass
class FrameObs:
    frame: int
    t: float
    hands: dict[str, HandObs]
    interaction: str = "none"
    activity: str = "idle"


def observe_hand(hand: Hand, aspect: float, cfg: GestureConfig) -> HandObs:
    """Single-frame features. Low-confidence hands keep a position but no finger guesses."""
    raw = np.asarray(hand.landmarks, dtype=float).reshape(21, 3)
    iso = g.to_iso(raw, aspect)
    centre = g.palm_centre(iso)
    praw = raw[list(g.PALM_IDS)].mean(axis=0)
    obs = HandObs(label=hand.handedness, score=hand.score, raw=raw, iso=iso, palm=g.palm_size(iso),
                  centre=centre[:2], position=[round(float(praw[0]), 4), round(float(praw[1]), 4)])
    reason = "low_score" if hand.score < cfg.min_score else g.implausibility(raw, iso, cfg)
    if reason:
        mark_low_confidence(obs, reason)
        return obs
    obs.fingers = g.describe_fingers(iso, cfg, hand.handedness)
    obs.groups = g.tip_groups(iso, obs.fingers, cfg)
    obs.grip = g.classify_grip(iso, obs.fingers, cfg)
    obs.palm_facing = g.palm_facing(iso, hand.handedness, cfg)
    return obs


def mark_low_confidence(obs: HandObs, reason: str) -> None:
    obs.visibility, obs.reason = "low_confidence", reason
    obs.fingers = [FingerState(name=n, state="unknown") for n in g.FINGER_NAMES]
    obs.groups, obs.grip, obs.palm_facing = [], "unknown", "unknown"


def _shape(o: HandObs) -> np.ndarray:
    return (o.iso - np.append(o.centre, g.palm_centre(o.iso)[2])) / max(o.palm, 1e-9)


def shape_change(a: HandObs, b: HandObs) -> float:
    """Mean landmark displacement after removing translation, in palm sizes."""
    return float(np.mean(np.linalg.norm(_shape(a) - _shape(b), axis=1)))


def fill_gaps(frames: list[HandFrame], max_gap_s: float) -> list[HandFrame]:
    """Insert empty frames where frames.jsonl skips time (a writer that omits hand-less frames)."""
    if len(frames) < 3:
        return frames
    dts = np.diff([f.t for f in frames])
    step = float(np.median(dts[dts > 0])) if np.any(dts > 0) else 0.0
    if step <= 0:
        return frames
    fps_est = (frames[-1].frame - frames[0].frame) / max(frames[-1].t - frames[0].t, 1e-9)
    out: list[HandFrame] = []
    for prev, cur in zip(frames, frames[1:]):
        out.append(prev)
        gap = cur.t - prev.t
        if gap > max(max_gap_s, 2.5 * step):
            for k in range(1, int(gap / step)):
                t = prev.t + k * step
                if cur.t - t < step / 2:
                    break
                out.append(HandFrame(frame=prev.frame + int(round((t - prev.t) * fps_est)), t=round(t, 4), hands=[]))
    out.append(frames[-1])
    return out


def build_timeline(frames: list[HandFrame], aspect: float, cfg: GestureConfig) -> list[FrameObs]:
    """Observe every frame, then add temporal features: jitter rejection, speed, shape rate, interaction, activity."""
    if cfg.fill_gaps:
        frames = fill_gaps(frames, cfg.max_gap_s)
    timeline: list[FrameObs] = []
    for fr in frames:
        best: dict[str, Hand] = {}
        for h in fr.hands:  # duplicate labels: keep the higher score
            if h.handedness not in best or h.score > best[h.handedness].score:
                best[h.handedness] = h
        timeline.append(FrameObs(frame=fr.frame, t=fr.t, hands={k: observe_hand(h, aspect, cfg) for k, h in best.items()}))

    last: dict[str, tuple[float, HandObs]] = {}
    history: dict[str, list[tuple[float, HandObs]]] = {k: [] for k in HANDS}
    for fo in timeline:
        for label, o in fo.hands.items():
            prev = last.get(label)
            if prev and 0 < fo.t - prev[0] <= cfg.max_gap_s:
                dt = fo.t - prev[0]
                if o.visibility == "visible":
                    if np.linalg.norm(o.centre - prev[1].centre) / dt > cfg.max_jump_speed:
                        mark_low_confidence(o, "jump")
                    elif shape_change(o, prev[1]) / dt > cfg.max_jitter_rate:
                        mark_low_confidence(o, "jitter")
            else:
                history[label] = []  # presence broken: restart the motion window
            hist = history[label]
            hist.append((fo.t, o))
            while hist and fo.t - hist[0][0] > cfg.speed_window_s + 1e-9:
                hist.pop(0)
            if len(hist) >= 2 and fo.t > hist[0][0]:
                t0, o0 = hist[0]
                o.speed = float(np.linalg.norm(o.centre - o0.centre)) / (fo.t - t0)
                o.shape_rate = shape_change(o, o0) / (fo.t - t0)
            last[label] = (fo.t, o)
        for label in HANDS:
            if label not in fo.hands:
                history[label] = []
        fo.interaction = interaction(fo.hands, cfg)
        fo.activity = activity(fo.hands, cfg)
    return timeline


def interaction(hands: dict[str, HandObs], cfg: GestureConfig) -> str:
    if len(hands) < 2:
        return "none"
    a, b = hands["Right"], hands["Left"]
    palm = (a.palm + b.palm) / 2
    closest = float(np.min(np.linalg.norm(a.iso[:, None, :2] - b.iso[None, :, :2], axis=2)))
    if closest / palm < cfg.touch_dist:
        return "hands_touching"
    if np.linalg.norm(a.centre - b.centre) / palm < cfg.close_dist:
        return "hands_close"
    return "hands_apart"


def activity(hands: dict[str, HandObs], cfg: GestureConfig) -> str:
    for o in hands.values():
        if (o.speed or 0.0) >= cfg.idle_speed:
            return "active"
        if o.visibility == "visible" and (o.shape_rate or 0.0) >= cfg.idle_shape_rate:
            return "active"
    return "idle"


def speed_bucket(speed: float | None, cfg: GestureConfig) -> str | None:
    if speed is None:
        return None
    if speed < cfg.still_max:
        return "still"
    if speed < cfg.slow_max:
        return "slow"
    if speed < cfg.moderate_max:
        return "moderate"
    return "fast"
