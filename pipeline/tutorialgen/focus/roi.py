"""Deterministic region-of-interest candidates from hand landmarks.

Boxes have a fixed meaning per id, so the LLM chooses *what* to focus on, never coordinates:

    B1 hands       union of every visible hand, padded
    B2 work zone   where the hands meet (landmarks of each hand near the other hand) or where a pinch /
                   power grip is held (thumb + fingertips, i.e. around the held object), padded
    B3 right hand  only when the hands work apart (hands_apart most of the time)
    B4 left hand   idem

A box is computed per *region*: a stretch of time with no scene cut, because a box from one shot means
nothing in the next. Within a region the box is the union over all supporting samples, so it contains
every supporting hand sample by construction (no percentile trimming that could crop a hand out).
"""

from __future__ import annotations

import bisect
import math
from dataclasses import dataclass

import numpy as np
from pydantic import BaseModel, Field

from ..gesture.timeline import FrameObs, HandObs
from ..schemas.steps import FocusBox, FocusRegion

KINDS = {"B1": "hands", "B2": "work_zone", "B3": "right_hand", "B4": "left_hand"}
LABELS = {"hands": "both hands", "work_zone": "work zone", "right_hand": "right hand", "left_hand": "left hand"}
FULL = "full"
PINCH_POINTS = (3, 4, 7, 8)
GRIP_POINTS = (4, 8, 12, 16, 20, 9)
RELIABLE_POSITION = {"out_of_frame", "too_small"}


class FocusConfig(BaseModel):
    """``focus`` config section: ROI candidates (draft) and the render crop."""

    enabled: bool = Field(True, description="render: zoom/crop to the chosen focus box; false = always full frame")
    boxes_in_prompt: bool = Field(True, description="draft: compute boxes, draw them on the keyframes and let the LLM pick one per sub-step")
    hands_pad_palms: float = Field(0.8, description="padding around the hands box, in palm sizes")
    zone_pad_palms: float = Field(0.7, description="padding around the work zone, in palm sizes")
    contact_palms: float = Field(1.0, description="a landmark within this many palm sizes of the other hand is a contact point")
    min_coverage: float = Field(0.3, description="a region needs hands in at least this fraction of its samples")
    min_zone_coverage: float = Field(0.25, description="the work zone needs contact/grip in at least this fraction of samples")
    min_region_s: float = Field(0.5, description="shots shorter than this get no box")
    max_zoom: float = Field(2.0, description="render: never magnify more than this")
    min_zoom_gain: float = Field(1.15, description="render: crops that would zoom less than this stay full frame")
    min_crop_frac: float = Field(0.4, description="render: crop width at least this fraction of the frame")
    pan_s: float = Field(0.6, description="render: eased pan between sub-steps within a shot")
    contain_pad: float = Field(0.03, description="render: per-frame safety margin keeping every drawn hand inside the crop")
    contain_ramp_s: float = Field(0.4, description="render: when a hand nears the crop edge, open the crop over this long before (and close after)")


@dataclass
class Shot:
    start: float
    end: float


def shots(cuts: list[float], start: float, end: float) -> list[Shot]:
    inner = sorted(c for c in cuts if start < c < end)
    edges = [start, *inner, end]
    return [Shot(a, b) for a, b in zip(edges, edges[1:]) if b > a]


def _usable(o: HandObs) -> bool:
    """Visible hands, plus hands that are only partly out of frame or small (their position is still right)."""
    return o.visibility == "visible" or o.reason in RELIABLE_POSITION


def _pad_xy(palm_diag: float, pad_palms: float, aspect: float) -> tuple[float, float]:
    """Padding of ``pad_palms`` palm sizes in normalized x / y units."""
    diag = math.hypot(aspect, 1.0)
    d = palm_diag * pad_palms
    return d * diag / aspect, d * diag


def _box(points: np.ndarray, pad: tuple[float, float]) -> list[float]:
    x0, y0 = points.min(axis=0)
    x1, y1 = points.max(axis=0)
    box = [x0 - pad[0], y0 - pad[1], x1 + pad[0], y1 + pad[1]]
    return [round(float(min(max(v, 0.0), 1.0)), 4) for v in box]


def contact_points(a: HandObs, b: HandObs, contact_palms: float) -> np.ndarray:
    """Landmarks (normalized xy) of each hand lying within ``contact_palms`` palm sizes of the other hand."""
    palm = (a.palm + b.palm) / 2
    d = np.linalg.norm(a.iso[:, None, :2] - b.iso[None, :, :2], axis=2) / max(palm, 1e-9)
    near_a = d.min(axis=1) <= contact_palms
    near_b = d.min(axis=0) <= contact_palms
    return np.vstack([a.raw[near_a, :2], b.raw[near_b, :2]])


def zone_points(fo: FrameObs, cfg: FocusConfig) -> np.ndarray | None:
    hands = [o for o in fo.hands.values() if o.visibility == "visible"]
    if len(hands) == 2 and fo.interaction in ("hands_close", "hands_touching"):
        pts = contact_points(hands[0], hands[1], cfg.contact_palms)
        if len(pts) >= 3:
            return pts
    held = []
    for o in hands:
        if o.grip == "pinch":
            held.append(o.raw[list(PINCH_POINTS), :2])
        elif o.grip in ("power_grip", "fist"):
            held.append(o.raw[list(GRIP_POINTS), :2])
    return np.vstack(held) if held else None


def _points_for(kind: str, fo: FrameObs, cfg: FocusConfig) -> tuple[np.ndarray | None, list[float]]:
    """Points supporting ``kind`` in one sample, and the palm sizes of the hands involved."""
    if kind == "work_zone":
        pts = zone_points(fo, cfg)
        return pts, [o.palm for o in fo.hands.values() if o.visibility == "visible"]
    if kind in ("right_hand", "left_hand"):
        o = fo.hands.get("Right" if kind == "right_hand" else "Left")
        return (o.raw[:, :2], [o.palm]) if o is not None and _usable(o) else (None, [])
    usable = [o for o in fo.hands.values() if _usable(o)]
    if not usable:
        return None, []
    return np.vstack([o.raw[:, :2] for o in usable]), [o.palm for o in usable]


class Timeline:
    """Gesture timeline (per-frame observations) with time slicing."""

    def __init__(self, frames: list[FrameObs], aspect: float):
        self.frames = sorted(frames, key=lambda f: f.t)
        self.times = [f.t for f in self.frames]
        self.aspect = aspect

    def between(self, start: float, end: float) -> list[FrameObs]:
        return self.frames[bisect.bisect_left(self.times, start):bisect.bisect_left(self.times, end)]


def region_box(tl: Timeline, kind: str, start: float, end: float, cfg: FocusConfig) -> FocusRegion | None:
    """Box of ``kind`` over [start, end), or None when it is not supported often enough."""
    samples = tl.between(start, end)
    if not samples or end - start < cfg.min_region_s:
        return None
    pts, palms, hit = [], [], 0
    for fo in samples:
        p, pl = _points_for(kind, fo, cfg)
        if p is not None and len(p):
            pts.append(p)
            palms += pl
            hit += 1
    coverage = hit / len(samples)
    need = cfg.min_zone_coverage if kind == "work_zone" else cfg.min_coverage
    if not pts or coverage < need:
        return None
    pad = cfg.zone_pad_palms if kind == "work_zone" else cfg.hands_pad_palms
    box = _box(np.vstack(pts).clip(0, 1), _pad_xy(float(np.median(palms)) if palms else 0.05, pad, tl.aspect))
    if box[2] - box[0] <= 0.01 or box[3] - box[1] <= 0.01:
        return None
    return FocusRegion(start=round(start, 3), end=round(end, 3), box=box, coverage=round(coverage, 3))


def _apart(tl: Timeline, start: float, end: float) -> bool:
    two = [fo for fo in tl.between(start, end) if len(fo.hands) == 2]
    return bool(two) and sum(fo.interaction == "hands_apart" for fo in two) / len(two) >= 0.5


def candidate_boxes(tl: Timeline, cuts: list[float], start: float, end: float, cfg: FocusConfig) -> list[FocusBox]:
    """Focus boxes for a step: one region per shot where the box is supported. Ids are stable per kind."""
    out: list[FocusBox] = []
    parts = shots(cuts, start, end)
    for bid, kind in KINDS.items():
        regions = []
        for sh in parts:
            if kind in ("right_hand", "left_hand") and not _apart(tl, sh.start, sh.end):
                continue
            if (r := region_box(tl, kind, sh.start, sh.end, cfg)) is not None:
                regions.append(r)
        if regions:
            out.append(FocusBox(id=bid, kind=kind, label=LABELS[kind], regions=regions))
    return out


def box_at(box: FocusBox, t: float) -> list[float] | None:
    for r in box.regions:
        if r.start <= t < r.end or (t == r.end and r is box.regions[-1]):
            return r.box
    return None


def area(b: list[float]) -> float:
    return max(b[2] - b[0], 0.0) * max(b[3] - b[1], 0.0)


def describe(b: list[float]) -> str:
    return f"x {b[0]:.2f}-{b[2]:.2f}, y {b[1]:.2f}-{b[3]:.2f} ({area(b) * 100:.0f}% of the frame)"


BOX_COLORS = {"B1": (121, 232, 214), "B2": (60, 170, 255), "B3": (255, 150, 92), "B4": (230, 120, 230)}


def draw_boxes(img: np.ndarray, boxes: list[FocusBox], t: float) -> list[str]:
    """Draw and label the boxes present at time ``t`` on a BGR image in place; returns the ids drawn."""
    import cv2

    h, w = img.shape[:2]
    s = max(h / 360.0, 1.0)
    drawn, labels = [], []
    present = [(fb, box_at(fb, t)) for fb in boxes]
    present = [(fb, b) for fb, b in present if b is not None]
    for fb, b in present:  # all frames first, so no label is drawn over by a later box
        color = BOX_COLORS.get(fb.id, (255, 255, 255))
        p0 = (int(b[0] * (w - 1)), int(b[1] * (h - 1)))
        p1 = (int(b[2] * (w - 1)), int(b[3] * (h - 1)))
        cv2.rectangle(img, p0, p1, (0, 0, 0), int(4 * s))
        cv2.rectangle(img, p0, p1, color, int(2 * s))
    for fb, b in present:
        color = BOX_COLORS.get(fb.id, (255, 255, 255))
        text = f"{fb.id} {fb.label}"
        fs, th = 0.5 * s, max(int(s), 1)
        (tw, tht), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, fs, th)
        x = min(int(b[0] * (w - 1)) + 2, max(w - tw - 4, 0))
        y = min(max(int(b[1] * (h - 1)) + tht + 6, tht + 4), h - 4)  # inside the top-left corner
        # Move down past any label it would overlap (boxes with nearby corners).
        while any(x < lx1 and x + tw > lx0 and y - tht - 4 < ly1 and y + 4 > ly0 for lx0, ly0, lx1, ly1 in labels) and y < h - 4:
            y += tht + 10
        labels.append((x - 2, y - tht - 4, x + tw + 2, y + 4))
        cv2.rectangle(img, (x - 2, y - tht - 4), (x + tw + 2, y + 4), (0, 0, 0), -1)
        cv2.putText(img, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX, fs, color, th, cv2.LINE_AA)
        drawn.append(fb.id)
    return drawn
