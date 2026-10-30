"""Hand-skeleton overlay: map video frames to sampled hand landmarks and draw them.

``hands/frames.jsonl`` is sampled at a lower rate than the video. ``HandTrack.hands_at(t)`` returns
the hands to draw at any video time: linearly interpolated between the two neighbouring samples when
the same hand appears in both, the nearest sample's hands when only one side is close enough, and
nothing when no sample is near. ``draw_hands`` draws them on a BGR frame in place. Both are reusable
outside the render stage (e.g. perception debug renders).
"""

from __future__ import annotations

import bisect
from dataclasses import dataclass
from statistics import median
from typing import Iterable

import cv2
import numpy as np

from ..schemas.media import HandFrame

# MediaPipe hand landmark topology (21 points).
HAND_CONNECTIONS: tuple[tuple[int, int], ...] = (
    (0, 1), (1, 2), (2, 3), (3, 4),            # thumb
    (0, 5), (5, 6), (6, 7), (7, 8),            # index
    (5, 9), (9, 10), (10, 11), (11, 12),       # middle
    (9, 13), (13, 14), (14, 15), (15, 16),     # ring
    (13, 17), (0, 17), (17, 18), (18, 19), (19, 20),  # pinky + palm
)
FINGERTIPS = (4, 8, 12, 16, 20)

# BGR. Right = brand lime, Left = light brand blue; both read well on most footage.
HAND_COLORS: dict[str, tuple[int, int, int]] = {"Right": (121, 232, 214), "Left": (255, 150, 92)}
OUTLINE_COLOR = (51, 39, 41)  # brand dark, drawn under the skeleton for contrast


@dataclass
class PoseHand:
    handedness: str
    landmarks: np.ndarray  # (21, 3): x, y normalized to image size, z relative depth
    score: float


def _hands(sample: HandFrame) -> list[PoseHand]:
    out = []
    for h in sample.hands:
        lm = np.asarray(h.landmarks, dtype=np.float32)
        if lm.shape[0] != 21:
            continue
        if lm.shape[1] == 2:
            lm = np.hstack([lm, np.zeros((21, 1), np.float32)])
        out.append(PoseHand(h.handedness, lm[:, :3], h.score))
    return out


def _match(a: PoseHand, candidates: list[PoseHand], max_dist: float) -> PoseHand | None:
    """Same-handedness hand in ``candidates`` closest to ``a`` (mean landmark distance), if close enough."""
    best, best_d = None, max_dist
    for c in candidates:
        if c.handedness != a.handedness:
            continue
        d = float(np.linalg.norm(a.landmarks[:, :2] - c.landmarks[:, :2], axis=1).mean())
        if d <= best_d:
            best, best_d = c, d
    return best


class HandTrack:
    """Time-indexed hand samples with nearest/interpolated lookup.

    tolerance: max distance (s) to the nearest sample for showing it un-interpolated.
    max_gap: max spacing (s) between two samples for interpolating across them.
    Both default to multiples of the median sample spacing.
    """

    def __init__(self, samples: Iterable[HandFrame], tolerance: float | None = None, max_gap: float | None = None,
                 max_match_dist: float = 0.2):
        self.samples = sorted(samples, key=lambda s: s.t)
        self.times = [s.t for s in self.samples]
        self._hands = [_hands(s) for s in self.samples]
        diffs = [b - a for a, b in zip(self.times, self.times[1:]) if b > a]
        step = median(diffs) if diffs else 0.1
        self.tolerance = tolerance if tolerance is not None else max(0.6 * step, 0.05)
        self.max_gap = max_gap if max_gap is not None else 2.5 * step
        self.max_match_dist = max_match_dist

    def __len__(self) -> int:
        return len(self.samples)

    def hands_at(self, t: float) -> list[PoseHand]:
        if not self.samples:
            return []
        i = bisect.bisect_right(self.times, t)  # samples[i-1].t <= t < samples[i].t
        prev = i - 1 if i > 0 else None
        nxt = i if i < len(self.samples) else None
        if prev is not None and abs(self.times[prev] - t) < 1e-6:
            return [PoseHand(h.handedness, h.landmarks.copy(), h.score) for h in self._hands[prev]]

        out: list[PoseHand] = []
        used_next: set[int] = set()
        if prev is not None and nxt is not None and self.times[nxt] - self.times[prev] <= self.max_gap:
            t0, t1 = self.times[prev], self.times[nxt]
            w = (t - t0) / (t1 - t0)
            nxt_hands = self._hands[nxt]
            for h in self._hands[prev]:
                m = _match(h, [c for k, c in enumerate(nxt_hands) if k not in used_next], self.max_match_dist)
                if m is not None:
                    used_next.add(next(k for k, c in enumerate(nxt_hands) if c is m))
                    out.append(PoseHand(h.handedness, (1 - w) * h.landmarks + w * m.landmarks,
                                        (1 - w) * h.score + w * m.score))
                elif t - t0 <= self.tolerance:
                    out.append(h)
            for k, h in enumerate(nxt_hands):
                if k not in used_next and t1 - t <= self.tolerance:
                    out.append(h)
            return out

        # No interpolation possible: nearest sample within tolerance, if any.
        best = None
        for j in (prev, nxt):
            if j is not None and abs(self.times[j] - t) <= self.tolerance:
                if best is None or abs(self.times[j] - t) < abs(self.times[best] - t):
                    best = j
        return list(self._hands[best]) if best is not None else []


def draw_hands(frame: np.ndarray, hands: list[PoseHand], label: bool = False, scale: float | None = None) -> np.ndarray:
    """Draw skeletons in place on a BGR frame and return it. Line width scales with frame height."""
    h, w = frame.shape[:2]
    s = scale if scale is not None else max(h / 720.0, 0.4)
    line = max(int(round(3 * s)), 1)
    outline = line + max(int(round(2 * s)), 1)
    radius = max(int(round(4 * s)), 2)
    for hand in hands:
        color = HAND_COLORS.get(hand.handedness, (255, 255, 255))
        pts = np.round(hand.landmarks[:, :2] * [w, h]).astype(np.int32)
        for a, b in HAND_CONNECTIONS:
            cv2.line(frame, tuple(pts[a]), tuple(pts[b]), OUTLINE_COLOR, outline, cv2.LINE_AA)
        for a, b in HAND_CONNECTIONS:
            cv2.line(frame, tuple(pts[a]), tuple(pts[b]), color, line, cv2.LINE_AA)
        for k, p in enumerate(pts):
            r = radius + (1 if k in FINGERTIPS else 0)
            cv2.circle(frame, tuple(p), r + max(line // 2, 1), OUTLINE_COLOR, -1, cv2.LINE_AA)
            cv2.circle(frame, tuple(p), r, color, -1, cv2.LINE_AA)
        if label:
            text = hand.handedness[0]
            fs = 0.5 * s
            x, y = int(pts[0][0]) + radius * 2, int(pts[0][1]) + radius * 2
            (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, fs, max(line - 1, 1))
            cv2.rectangle(frame, (x - 3, y - th - 4), (x + tw + 3, y + 4), OUTLINE_COLOR, -1)
            cv2.putText(frame, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX, fs, color, max(line - 1, 1), cv2.LINE_AA)
    return frame


def draw_at(frame: np.ndarray, track: HandTrack, t: float, label: bool = False) -> np.ndarray:
    """Convenience: draw whatever the track has at time ``t``."""
    return draw_hands(frame, track.hands_at(t), label=label)
