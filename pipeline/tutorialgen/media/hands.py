"""MediaPipe Hand Landmarker (Tasks API, mediapipe>=1.x layout), handedness fixes and One Euro smoothing.

Handedness: older MediaPipe docs say labels assume a mirrored (selfie) image. With mediapipe 1.2.0's
Hand Landmarker we checked by eye on the non-mirrored samples (palm/back orientation, thumb side, arm
origin): the raw "Right" already is the demonstrator's right hand. So ``mirror_handedness`` defaults
to False and should be set True only for footage that was flipped horizontally (selfie previews).
"""

from __future__ import annotations

import logging
import math
import os
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

log = logging.getLogger("tutorialgen.media")

MODEL_URL = ("https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/"
             "float16/latest/hand_landmarker.task")
MODELS_DIR = Path(__file__).resolve().parents[2] / "models"
FLIP = {"Left": "Right", "Right": "Left"}


def ensure_model(path: str | Path | None = None) -> Path:
    """Return the model path, downloading the official float16 model to pipeline/models/ on first use."""
    if path:
        p = Path(path).expanduser()
        if not p.exists():
            raise FileNotFoundError(f"hand landmarker model not found at {p}")
        return p
    p = MODELS_DIR / "hand_landmarker.task"
    if p.exists() and p.stat().st_size > 0:
        return p
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(f".{os.getpid()}.part")
    log.info("downloading %s -> %s", MODEL_URL, p)
    with urllib.request.urlopen(MODEL_URL, timeout=60) as r, open(tmp, "wb") as f:
        while block := r.read(1 << 20):
            f.write(block)
    tmp.replace(p)
    return p


@dataclass
class DetectedHand:
    handedness: str
    score: float
    landmarks: np.ndarray                 # 21 x 3, normalized image coords
    world_landmarks: np.ndarray | None    # 21 x 3, metres


class HandLandmarker:
    """Thin wrapper over mediapipe's VIDEO-mode landmarker returning numpy arrays."""

    def __init__(self, model_path: Path, num_hands: int = 2, min_detection: float = 0.5,
                 min_presence: float = 0.5, min_tracking: float = 0.5, device: str = "cpu"):
        from mediapipe.tasks.python.core.base_options import BaseOptions
        from mediapipe.tasks.python.vision import hand_landmarker as hl
        from mediapipe.tasks.python.vision.core.vision_task_running_mode import VisionTaskRunningMode

        def make(delegate):
            return hl.HandLandmarker.create_from_options(hl.HandLandmarkerOptions(
                base_options=BaseOptions(model_asset_path=str(model_path), delegate=delegate),
                running_mode=VisionTaskRunningMode.VIDEO, num_hands=num_hands,
                min_hand_detection_confidence=min_detection, min_hand_presence_confidence=min_presence,
                min_tracking_confidence=min_tracking))

        self.device = "cpu"
        self._task = None
        if device == "cuda":
            try:
                self._task = make(BaseOptions.Delegate.GPU)
                self.device = "gpu"
            except Exception as exc:  # noqa: BLE001 - any delegate failure falls back to CPU
                log.warning("MediaPipe GPU delegate unavailable, falling back to CPU: %s", exc)
        if self._task is None:
            self._task = make(BaseOptions.Delegate.CPU)
        self._last_ts = -1

    def detect(self, rgb: np.ndarray, t: float) -> list[DetectedHand]:
        import mediapipe as mp

        ts = max(int(round(t * 1000)), self._last_ts + 1)
        self._last_ts = ts
        image = mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(rgb))
        res = self._task.detect_for_video(image, ts)
        out = []
        for i, lms in enumerate(res.hand_landmarks):
            cat = res.handedness[i][0]
            world = res.hand_world_landmarks[i] if i < len(res.hand_world_landmarks) else None
            out.append(DetectedHand(
                handedness=cat.category_name, score=float(cat.score),
                landmarks=np.array([[l.x, l.y, l.z] for l in lms], dtype=np.float64),
                world_landmarks=np.array([[l.x, l.y, l.z] for l in world], dtype=np.float64) if world else None,
            ))
        return out

    def close(self) -> None:
        if self._task is not None:
            self._task.close()
            self._task = None

    def __enter__(self) -> "HandLandmarker":
        return self

    def __exit__(self, *exc) -> None:
        self.close()


def fix_handedness(hands: list[DetectedHand], mirror: bool, dedupe: bool = True) -> list[DetectedHand]:
    """Flip labels for non-mirrored footage; if two hands share a label, the less confident one takes the other."""
    for h in hands:
        if mirror:
            h.handedness = FLIP.get(h.handedness, h.handedness)
    if dedupe and len(hands) == 2 and hands[0].handedness == hands[1].handedness:
        weaker = min(hands, key=lambda h: h.score)
        weaker.handedness = FLIP[weaker.handedness]
    return hands


def _alpha(cutoff: np.ndarray | float, dt: float) -> np.ndarray | float:
    tau = 1.0 / (2 * math.pi * cutoff)
    return 1.0 / (1.0 + tau / dt)


@dataclass
class OneEuroFilter:
    """One Euro filter (Casiez et al. 2012) over an array of any shape, timestamps in seconds.

    Speeds are measured in units of ``scale`` per second (a hand's size for landmarks), so the same
    beta works for near and far hands.
    """

    min_cutoff: float = 1.0
    beta: float = 1.0
    d_cutoff: float = 1.0
    x_prev: np.ndarray | None = None
    dx_prev: np.ndarray | None = None
    t_prev: float | None = None

    def reset(self) -> None:
        self.x_prev = self.dx_prev = self.t_prev = None

    def __call__(self, x: np.ndarray, t: float, scale: float = 1.0) -> np.ndarray:
        x = np.asarray(x, dtype=np.float64)
        if self.x_prev is None or self.t_prev is None or t <= self.t_prev:
            self.x_prev, self.dx_prev, self.t_prev = x.copy(), np.zeros_like(x), t
            return x.copy()
        dt = t - self.t_prev
        dx = (x - self.x_prev) / dt
        a_d = _alpha(self.d_cutoff, dt)
        dx_hat = a_d * dx + (1 - a_d) * self.dx_prev
        cutoff = self.min_cutoff + self.beta * np.abs(dx_hat) / max(scale, 1e-6)
        a = _alpha(cutoff, dt)
        x_hat = a * x + (1 - a) * self.x_prev
        self.x_prev, self.dx_prev, self.t_prev = x_hat, dx_hat, t
        return x_hat


def hand_scale(points: np.ndarray) -> float:
    """Mean of the x and y extents of a landmark set."""
    ext = points[:, :2].max(axis=0) - points[:, :2].min(axis=0)
    return float(max(ext.mean(), 1e-6))


@dataclass
class HandSmoother:
    """One Euro filters per handedness track; a track resets after ``reset_gap_s`` without that hand."""

    min_cutoff: float = 1.0
    beta: float = 1.0
    d_cutoff: float = 1.0
    reset_gap_s: float = 0.5
    _tracks: dict[str, tuple[OneEuroFilter, OneEuroFilter, float]] = field(default_factory=dict)

    def __call__(self, hands: list[DetectedHand], t: float) -> list[DetectedHand]:
        for h in hands:
            track = self._tracks.get(h.handedness)
            if track is None or t - track[2] > self.reset_gap_s:
                track = (OneEuroFilter(self.min_cutoff, self.beta, self.d_cutoff),
                         OneEuroFilter(self.min_cutoff, self.beta, self.d_cutoff), t)
            img_f, world_f, _ = track
            h.landmarks = img_f(h.landmarks, t, hand_scale(h.landmarks))
            if h.world_landmarks is not None:
                h.world_landmarks = world_f(h.world_landmarks, t, hand_scale(h.world_landmarks))
            self._tracks[h.handedness] = (img_f, world_f, t)
        return hands
