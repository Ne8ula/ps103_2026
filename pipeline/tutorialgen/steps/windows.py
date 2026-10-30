"""Candidate intervals, overlapping LLM windows, and the deterministic merge across windows.

Strategy
--------
1. Boundary points = content start, every candidate boundary inside the content range, content end
   (candidates closer than ``MIN_GAP`` are collapsed). Consecutive points form candidate intervals.
2. Windows are runs of consecutive intervals, closed when they reach ``window_s`` seconds or
   ``max_intervals`` intervals. The next window starts at the first interval that begins at or after
   ``end - overlap_s`` (always moving forward), so neighbouring windows share roughly ``overlap_s``.
3. Each window's LLM answer (steps with start/end seconds) is snapped to that window's boundary
   points (within ``snap_s``) and clamped to the window, so unknown or hallucinated boundaries are safe.
4. Ownership: the overlap between windows i and i+1 is cut at its midpoint; each window contributes
   only the boundaries it proposes inside the region it owns. The union of contributed boundaries
   defines the final intervals, each labelled with the owning window's step that overlaps it most.
5. Intervals no step covers (idle gaps) join the previous step; adjacent intervals labelled with the
   same proposed step are fused; steps shorter than ``min_step_s`` merge into their shorter neighbour.
The result covers [content start, content end] contiguously with no overlaps.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..schemas import BoundaryCandidate

MIN_GAP = 0.25


@dataclass
class Point:
    id: str
    t: float
    score: float | None = None
    reasons: list[str] = field(default_factory=list)


@dataclass
class Interval:
    id: str
    start: Point
    end: Point

    @property
    def duration(self) -> float:
        return self.end.t - self.start.t

    @property
    def mid(self) -> float:
        return (self.start.t + self.end.t) / 2


@dataclass
class Window:
    index: int
    intervals: list[Interval]

    @property
    def start(self) -> float:
        return self.intervals[0].start.t

    @property
    def end(self) -> float:
        return self.intervals[-1].end.t

    @property
    def points(self) -> list[Point]:
        return [self.intervals[0].start] + [iv.end for iv in self.intervals]


@dataclass
class Proposal:
    """One step proposed by one window, after snapping."""

    start: float
    end: float
    summary: str
    rationale: str
    confidence: float
    window: int
    call_key: str


@dataclass
class Span:
    start: float
    end: float
    source: Proposal | None
    notes: list[str] = field(default_factory=list)

    @property
    def duration(self) -> float:
        return self.end - self.start


def build_intervals(boundaries: list[BoundaryCandidate], start: float, end: float) -> list[Interval]:
    inner = sorted((b for b in boundaries if start + MIN_GAP <= b.t <= end - MIN_GAP), key=lambda b: b.t)
    points = [Point("start", start)]
    for b in inner:
        if b.t - points[-1].t < MIN_GAP:
            continue
        points.append(Point(f"b{len(points):02d}", round(b.t, 3), b.score, list(b.reasons)))
    points.append(Point("end", end))
    return [Interval(f"i{k + 1:02d}", a, b) for k, (a, b) in enumerate(zip(points, points[1:]))]


def build_windows(intervals: list[Interval], window_s: float, overlap_s: float, max_intervals: int) -> list[Window]:
    windows: list[Window] = []
    i = 0
    while i < len(intervals):
        j = i
        while j + 1 < len(intervals) and (j + 1 - i) < max_intervals and intervals[j + 1].end.t - intervals[i].start.t <= window_s:
            j += 1
        windows.append(Window(len(windows), intervals[i : j + 1]))
        if j == len(intervals) - 1:
            break
        w_end = intervals[j].end.t
        nxt = next((k for k in range(i + 1, j + 1) if intervals[k].start.t >= w_end - overlap_s), j + 1)
        i = max(nxt, i + 1)
    return windows


def snap(t: float, window: Window, snap_s: float) -> float:
    """Nearest window boundary point within ``snap_s``; otherwise ``t`` clamped to the window."""
    t = min(max(t, window.start), window.end)
    nearest = min(window.points, key=lambda p: abs(p.t - t))
    return nearest.t if abs(nearest.t - t) <= snap_s else round(t, 3)


def _cuts(windows: list[Window]) -> list[float]:
    cuts = []
    for a, b in zip(windows, windows[1:]):
        cuts.append((b.start + a.end) / 2 if b.start < a.end else b.start)
    return cuts


def _owner(t: float, windows: list[Window], cuts: list[float]) -> int:
    for k, c in enumerate(cuts):
        if t < c:
            return k
    return len(windows) - 1


def merge_windows(windows: list[Window], proposals: list[list[Proposal]], start: float, end: float, min_step_s: float) -> list[Span]:
    cuts = _cuts(windows)
    points = {start, end}
    for w, props in zip(windows, proposals):
        for p in props:
            for t in (p.start, p.end):
                if start < t < end and _owner(t, windows, cuts) == w.index:
                    points.add(t)
    ordered: list[float] = []
    for t in sorted(points):
        if ordered and t - ordered[-1] < MIN_GAP:
            if t == end:
                ordered[-1] = end
            continue
        ordered.append(t)

    spans: list[Span] = []
    for a, b in zip(ordered, ordered[1:]):
        owner = _owner((a + b) / 2, windows, cuts)
        spans.append(Span(a, b, _best(proposals[owner], a, b) or _best([p for ps in proposals for p in ps], a, b)))

    # Idle gaps (no step covers them) join the previous step, or the next one at the very start.
    merged: list[Span] = []
    for s in spans:
        if merged and (s.source is None or s.source is merged[-1].source):
            if s.source is None:
                merged[-1].notes.append(f"absorbed uncovered {s.start:.1f}-{s.end:.1f}s")
            merged[-1].end = s.end
        elif merged and merged[-1].source is None:
            s.start = merged[-1].start
            s.notes = merged[-1].notes + [f"absorbed uncovered {merged[-1].start:.1f}-{merged[-1].end:.1f}s"]
            merged[-1] = s
        else:
            merged.append(s)

    while len(merged) > 1:
        k = min(range(len(merged)), key=lambda i: merged[i].duration)
        if merged[k].duration >= min_step_s:
            break
        if k == 0:
            n = 1
        elif k == len(merged) - 1:
            n = k - 1
        else:
            n = k - 1 if merged[k - 1].duration <= merged[k + 1].duration else k + 1
        short, keep = merged[k], merged[n]
        lo, hi = min(short.start, keep.start), max(short.end, keep.end)
        merged[min(k, n)] = Span(lo, hi, keep.source or short.source,
                                 keep.notes + short.notes + [f"merged short fragment {short.start:.1f}-{short.end:.1f}s"])
        del merged[max(k, n)]
    return merged


def _best(props: list[Proposal], a: float, b: float) -> Proposal | None:
    best, best_overlap = None, 0.0
    for p in props:
        overlap = min(b, p.end) - max(a, p.start)
        if overlap > best_overlap + 1e-9:
            best, best_overlap = p, overlap
    return best
