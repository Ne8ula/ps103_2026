"""Hard-cut detection from HSV colour-histogram distance between consecutive sampled frames."""

from __future__ import annotations

from dataclasses import dataclass, field

import cv2
import numpy as np


def hsv_hist(rgb: np.ndarray, bins: tuple[int, int, int] = (16, 8, 8), width: int = 160) -> np.ndarray:
    """L1-normalized 3D HSV histogram of a downscaled frame."""
    h, w = rgb.shape[:2]
    small = cv2.resize(rgb, (width, max(1, int(h * width / w))), interpolation=cv2.INTER_AREA)
    hsv = cv2.cvtColor(small, cv2.COLOR_RGB2HSV)
    hist = cv2.calcHist([hsv], [0, 1, 2], None, list(bins), [0, 180, 0, 256, 0, 256])
    return (hist / max(float(hist.sum()), 1.0)).astype(np.float32)


def hist_distance(a: np.ndarray, b: np.ndarray) -> float:
    """Bhattacharyya distance in [0, 1]: 0 identical, 1 disjoint."""
    return float(cv2.compareHist(a, b, cv2.HISTCMP_BHATTACHARYYA))


@dataclass
class SceneCutDetector:
    """Feed frames in order; ``update`` returns the distance score when a cut starts at this frame."""

    threshold: float = 0.4
    min_gap_s: float = 0.5
    _prev: np.ndarray | None = None
    _last_cut: float = field(default=-1e9)

    def update(self, rgb: np.ndarray, t: float) -> float | None:
        hist = hsv_hist(rgb)
        prev, self._prev = self._prev, hist
        if prev is None:
            return None
        score = hist_distance(prev, hist)
        if score >= self.threshold and t - self._last_cut >= self.min_gap_s:
            self._last_cut = t
            return score
        return None
