"""Representative frame extraction for vision input (JPEG, downscaled)."""

from __future__ import annotations

import logging
from pathlib import Path

log = logging.getLogger(__name__)


def extract_frames(video: Path, times: list[float], out_paths: list[Path], max_width: int = 640) -> list[Path | None]:
    """Write one JPEG per time; returns the written path or None where the frame could not be read."""
    import cv2

    written: list[Path | None] = [None] * len(times)
    if not Path(video).exists():
        log.warning("video %s not found: no keyframes extracted", video)
        return written
    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        log.warning("cannot open %s: no keyframes extracted", video)
        return written
    fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
    frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    try:
        for i, (t, out) in enumerate(zip(times, out_paths)):
            idx = int(round(t * fps)) if fps > 0 else 0
            if frames > 0:
                idx = min(max(idx, 0), frames - 1)
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ok, frame = cap.read()
            if not ok or frame is None:
                cap.set(cv2.CAP_PROP_POS_MSEC, max(t, 0.0) * 1000)
                ok, frame = cap.read()
            if not ok or frame is None:
                log.warning("no frame at %.2fs in %s", t, video)
                continue
            h, w = frame.shape[:2]
            if w > max_width:
                frame = cv2.resize(frame, (max_width, max(1, round(h * max_width / w))), interpolation=cv2.INTER_AREA)
            out.parent.mkdir(parents=True, exist_ok=True)
            if cv2.imwrite(str(out), frame, [cv2.IMWRITE_JPEG_QUALITY, 85]):
                written[i] = out
    finally:
        cap.release()
    return written


def spread(start: float, end: float, n: int) -> list[float]:
    """n times evenly spread inside [start, end] (centres of n equal slices)."""
    if n <= 0 or end <= start:
        return [start] if n > 0 else []
    return [start + (end - start) * (k + 0.5) / n for k in range(n)]
