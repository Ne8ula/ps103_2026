"""Units and their evidence: spoken lines, gaps, hand presence and pixel motion."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from ..schemas.media import HandFrame, Transcript, Word


@dataclass
class Line:
    start: float
    end: float
    text: str


def subtitle_lines(tr: Transcript, max_s: float = 6.0, max_words: int = 12, gap_s: float = 0.8) -> list[Line]:
    """Short spoken lines from Whisper word timestamps (segments can span long pauses), grouped across
    segment boundaries so no line is a stray word. Without word timestamps, segments are used as-is."""
    words: list[Word] = [w for seg in tr.segments for w in seg.words]
    if not words:
        return [Line(s.start, s.end, s.text.strip()) for s in tr.segments if s.text.strip()]
    out: list[Line] = []
    cur: list[Word] = []

    def flush():
        out.append(Line(cur[0].start, cur[-1].end, " ".join(w.word.strip() for w in cur)))

    for w in words:
        if cur and (w.start - cur[-1].end > gap_s or w.end - cur[0].start > max_s or len(cur) >= max_words):
            flush()
            cur = []
        cur.append(w)
    if cur:
        flush()
    return out


def pixel_motion(video: Path, fps: float = 4.0, size: tuple[int, int] = (160, 90)) -> tuple[np.ndarray, np.ndarray]:
    """(times, motion): mean absolute grey-level change between samples, scaled so this video's
    95th percentile is 1. Works when hands are hidden inside the machine."""
    import cv2

    cap = cv2.VideoCapture(str(video))
    src_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    stride = max(int(round(src_fps / fps)), 1)
    times, values, prev, i = [], [], None, 0
    while True:
        ok = cap.grab()
        if not ok:
            break
        if i % stride == 0:
            ok, frame = cap.retrieve()
            if not ok:
                break
            g = cv2.cvtColor(cv2.resize(frame, size, interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY).astype(np.float32)
            values.append(0.0 if prev is None else float(np.abs(g - prev).mean()))
            times.append(i / src_fps)
            prev = g
        i += 1
    cap.release()
    v = np.array(values)
    scale = np.percentile(v, 95) if len(v) and np.percentile(v, 95) > 0 else 1.0
    return np.array(times), np.clip(v / scale, 0, 2)


@dataclass
class Unit:
    id: str
    start: float
    end: float
    kind: str                     # "speech" | "gap"
    text: str | None = None
    hands: float = 0.0
    motion: float = 0.0
    numbers: set[float] = field(default_factory=set)

    @property
    def duration(self) -> float:
        return self.end - self.start


def _mean_in(times: np.ndarray, values: np.ndarray, a: float, b: float) -> float:
    m = (times >= a) & (times < b)
    return float(values[m].mean()) if m.any() else 0.0


def build_units(step_id: str, start: float, end: float, lines: list[Line], hand_frames: list[HandFrame],
                motion: tuple[np.ndarray, np.ndarray], absorb_gap_s: float = 0.4, pad_s: float = 0.12) -> list[Unit]:
    """Split [start, end] into spoken lines and gaps. Gaps shorter than ``absorb_gap_s`` join the
    neighbouring line; lines are padded by ``pad_s`` into the gaps so cuts never clip a word."""
    from ..steps.guards import numbers_in

    inside = [Line(max(l.start, start), min(l.end, end), l.text) for l in lines if l.end > start and l.start < end]
    spans: list[list] = []                     # [start, end, kind, text]
    t = start
    for l in inside:
        l = Line(max(l.start, t), max(l.end, t), l.text)  # overlapping lines: never go backwards
        if l.end <= l.start:
            continue
        if l.start - t > absorb_gap_s:
            spans.append([t, l.start, "gap", None])
        elif spans:
            spans[-1][1] = l.start             # tiny gap: stretch the previous span to meet this line
        else:
            l = Line(t, l.end, l.text)
        spans.append([l.start, l.end, "speech", l.text])
        t = l.end
    if end - t > absorb_gap_s or not spans:
        spans.append([t, end, "gap", None])
    else:
        spans[-1][1] = end
    for a, b in zip(spans, spans[1:]):           # pad lines into neighbouring gaps
        if a[2] == "speech" and b[2] == "gap":
            shift = min(pad_s, (b[1] - b[0]) / 2)
            a[1] += shift
            b[0] += shift
        elif a[2] == "gap" and b[2] == "speech":
            shift = min(pad_s, (a[1] - a[0]) / 2)
            a[1] -= shift
            b[0] -= shift

    ht = np.array([f.t for f in hand_frames]) if hand_frames else np.zeros(0)
    hv = np.array([1.0 if f.hands else 0.0 for f in hand_frames]) if hand_frames else np.zeros(0)
    mt, mv = motion
    units = []
    for n, (a, b, kind, text) in enumerate(spans, 1):
        units.append(Unit(id=f"{step_id}-u{n:02d}", start=round(a, 3), end=round(b, 3), kind=kind, text=text,
                          hands=round(_mean_in(ht, hv, a, b), 3), motion=round(_mean_in(mt, mv, a, b), 3),
                          numbers=numbers_in(text) if text else set()))
    return units
