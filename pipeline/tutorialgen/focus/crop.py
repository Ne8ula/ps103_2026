"""Render-side focus: turn sub-step focus choices into a crop plan, then a per-frame crop rect.

Crops keep the frame's aspect ratio, so in normalized coordinates a crop is always a square of side
``s`` (s = 1 is the full frame; zoom = 1 / s). Per sub-step and shot the rect is static; between two
sub-steps inside one shot it pans with an ease-in-out over ``pan_s``; at a scene cut it switches hard.
Every frame the rect is then grown, if needed, so every hand drawn on that frame stays inside it.
"""

from __future__ import annotations

import bisect

import numpy as np

from ..schemas.steps import Step, SubStep
from ..schemas.tutorial import CropSegment
from .roi import FULL, KINDS, FocusConfig, Timeline, region_box, shots

FULL_RECT = [0.0, 0.0, 1.0, 1.0]


def fit_crop(box: list[float], cfg: FocusConfig) -> list[float] | None:
    """Smallest aspect-preserving crop holding ``box`` within the zoom limits; None if not worth zooming."""
    bw, bh = box[2] - box[0], box[3] - box[1]
    s = min(max(bw, bh, 1.0 / max(cfg.max_zoom, 1.0), cfg.min_crop_frac), 1.0)
    if 1.0 / s < cfg.min_zoom_gain:
        return None
    return _square((box[0] + box[2]) / 2, (box[1] + box[3]) / 2, s)


def _square(cx: float, cy: float, s: float) -> list[float]:
    s = min(s, 1.0)
    x0 = min(max(cx - s / 2, 0.0), 1.0 - s)
    y0 = min(max(cy - s / 2, 0.0), 1.0 - s)
    return [round(x0, 5), round(y0, 5), round(x0 + s, 5), round(y0 + s, 5)]


def inside_content(rect: list[float], content: list[float] | None) -> list[float]:
    """Shift a zoomed crop into the picture area (off letterbox bars) on each axis where it fits."""
    if content is None or is_full(rect):
        return rect
    s = rect[2] - rect[0]
    x0, y0 = rect[0], rect[1]
    if s <= content[2] - content[0]:
        x0 = min(max(x0, content[0]), content[2] - s)
    if s <= content[3] - content[1]:
        y0 = min(max(y0, content[1]), content[3] - s)
    return [round(x0, 5), round(y0, 5), round(x0 + s, 5), round(y0 + s, 5)]


def plan(step: Step, tl: Timeline | None, cuts: list[float], cfg: FocusConfig,
         content: list[float] | None = None) -> list[CropSegment]:
    """One CropSegment per (sub-step x shot) piece of the step, in time order, covering [start, end].

    ``content``: the picture area inside letterbox bars; zoomed crops are shifted into it when they fit.
    """
    # Steps without sub-steps (drafted before sub-steps existed) keep the full frame: no focus was chosen.
    phases = step.substeps or [SubStep(start=step.start, end=step.end, caption=step.title, focus=FULL, focus_source="fallback")]
    out: list[CropSegment] = []
    cut_set = set(round(c, 3) for c in cuts)
    for ph in phases:
        for sh in shots(cuts, ph.start, ph.end):
            cut_before = not out or round(sh.start, 3) in cut_set
            rect, reason = FULL_RECT, ""
            if not cfg.enabled or tl is None:
                reason = "focus disabled" if not cfg.enabled else "no hand landmarks"
            elif ph.focus == FULL or ph.focus not in KINDS:
                reason = "full frame requested" if ph.focus == FULL else f"unknown focus '{ph.focus}'"
            else:
                tried = [ph.focus] + (["B1"] if ph.focus != "B1" else [])
                for bid in tried:
                    r = region_box(tl, KINDS[bid], sh.start, sh.end, cfg)
                    if r is None:
                        reason += f"{bid} not supported here; "
                        continue
                    fitted = fit_crop(r.box, cfg)
                    if fitted is None:
                        reason += f"{bid} fills the frame; "
                        break
                    rect, reason = inside_content(fitted, content), reason + f"{bid} (coverage {r.coverage:.2f})"
                    break
                if rect is FULL_RECT:
                    reason += "full frame"
            out.append(CropSegment(start=round(sh.start, 3), end=round(sh.end, 3), rect=list(rect), focus=ph.focus,
                                   reason=reason.strip(), cut_before=cut_before))
    return out


def smoothstep(u: float) -> float:
    u = min(max(u, 0.0), 1.0)
    return u * u * (3 - 2 * u)


def contain(rect: list[float], points: np.ndarray | None, pad: float) -> list[float]:
    """Grow ``rect`` (keeping it square) so every point plus ``pad`` lies inside it."""
    if points is None or len(points) == 0:
        return rect
    pts = np.clip(points[:, :2], 0.0, 1.0)
    lo, hi = pts.min(axis=0) - pad, pts.max(axis=0) + pad
    lo, hi = np.clip(lo, 0, 1), np.clip(hi, 0, 1)
    if lo[0] >= rect[0] and lo[1] >= rect[1] and hi[0] <= rect[2] and hi[1] <= rect[3]:
        return rect
    x0, y0 = min(lo[0], rect[0]), min(lo[1], rect[1])
    x1, y1 = max(hi[0], rect[2]), max(hi[1], rect[3])
    s = max(x1 - x0, y1 - y0)
    if s >= 1.0:
        return list(FULL_RECT)
    # Any offset in [hi - s, lo] contains the union; take the one closest to the old rect (least motion).
    nx0 = min(max(rect[0], x1 - s), x0, 1.0 - s)
    ny0 = min(max(rect[1], y1 - s), y0, 1.0 - s)
    return [float(nx0), float(ny0), float(nx0 + s), float(ny0 + s)]


class CropTrack:
    """Per-time crop rect from a crop plan (eased pans within a shot, hard switches at cuts)."""

    def __init__(self, segments: list[CropSegment], cfg: FocusConfig):
        self.segments = sorted(segments, key=lambda s: s.start)
        self.starts = [s.start for s in self.segments]
        self.cfg = cfg

    def rect_at(self, t: float, hand_points: np.ndarray | None = None) -> list[float]:
        if not self.segments:
            return list(FULL_RECT)
        i = max(bisect.bisect_right(self.starts, t) - 1, 0)
        seg = self.segments[i]
        rect = list(seg.rect)
        if i > 0 and not seg.cut_before and self.cfg.pan_s > 0 and t - seg.start < self.cfg.pan_s:
            u = smoothstep((t - seg.start) / self.cfg.pan_s)
            prev = self.segments[i - 1].rect
            rect = [(1 - u) * a + u * b for a, b in zip(prev, rect)]
        if rect != FULL_RECT:
            rect = contain(rect, hand_points, self.cfg.contain_pad)
        return rect

    def shot_index(self, t: float) -> int:
        """Index of the shot (run of segments with no cut between them) containing ``t``."""
        i = max(bisect.bisect_right(self.starts, t) - 1, 0)
        return sum(1 for s in self.segments[1:i + 1] if s.cut_before)

    def rects(self, times: list[float], points: list[np.ndarray | None], ramp_frames: int) -> list[list[float]]:
        """Per-frame rects for a run of frames, with hand containment eased in and out.

        Each frame's required growth (how far each side must move out to hold its hands) is spread to
        the neighbouring frames of the same shot with a triangular falloff over ``ramp_frames``, taking the
        maximum: the crop opens gradually before a hand reaches the edge and closes gradually afterwards.
        A frame's own growth always counts in full, so no hand is ever outside its frame's crop.
        """
        base = [self.rect_at(t) for t in times]
        need = [self.rect_at(t, p) for t, p in zip(times, points)]
        grow = np.array([[b[0] - n[0], b[1] - n[1], n[2] - b[2], n[3] - b[3]] for b, n in zip(base, need)]).clip(min=0)
        if ramp_frames <= 0 or not grow.any():
            return need
        shot = [self.shot_index(t) for t in times]
        smooth = grow.copy()
        for j in np.nonzero(grow.any(axis=1))[0]:
            for i in range(max(0, j - ramp_frames), min(len(times), j + ramp_frames + 1)):
                if shot[i] == shot[j]:
                    smooth[i] = np.maximum(smooth[i], grow[j] * (1 - abs(i - j) / (ramp_frames + 1)))
        out = []
        for b, n, g in zip(base, need, smooth):
            if not g.any() or is_full(b):
                out.append(n)
                continue
            box = np.array([[b[0] - g[0], b[1] - g[1]], [b[2] + g[2], b[3] + g[3]]])
            # Square it up again (contain keeps aspect and stays inside the frame), then make sure the
            # frame's own requirement is still met.
            r = contain(b, box, 0.0)
            out.append(contain(r, np.array([[n[0], n[1]], [n[2], n[3]]]), 0.0))
        return out


def is_full(rect: list[float]) -> bool:
    return rect[0] <= 1e-4 and rect[1] <= 1e-4 and rect[2] >= 1 - 1e-4 and rect[3] >= 1 - 1e-4


def apply_crop(frame: np.ndarray, rect: list[float], width: int, height: int) -> np.ndarray:
    """Crop ``rect`` out of a BGR frame and scale it to width x height."""
    import cv2

    h, w = frame.shape[:2]
    if is_full(rect):
        return frame if (w, h) == (width, height) else cv2.resize(frame, (width, height), interpolation=cv2.INTER_AREA)
    x0, y0 = int(round(rect[0] * w)), int(round(rect[1] * h))
    x1, y1 = max(int(round(rect[2] * w)), x0 + 2), max(int(round(rect[3] * h)), y0 + 2)
    sub = frame[y0:y1, x0:x1]
    interp = cv2.INTER_LINEAR if (x1 - x0) < width else cv2.INTER_AREA
    return cv2.resize(sub, (width, height), interpolation=interp)


def to_crop(landmarks: np.ndarray, rect: list[float]) -> np.ndarray:
    """Normalized source landmarks -> normalized coordinates inside the crop."""
    out = landmarks.copy()
    out[:, 0] = (landmarks[:, 0] - rect[0]) / max(rect[2] - rect[0], 1e-9)
    out[:, 1] = (landmarks[:, 1] - rect[1]) / max(rect[3] - rect[1], 1e-9)
    return out
