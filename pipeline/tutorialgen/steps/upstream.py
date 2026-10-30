"""Tolerant loaders for the artifacts the LLM stages read, and per-time-range views of them.

Missing optional artifacts degrade gracefully: no transcript -> ``Transcript(available=False)``,
no gestures -> no keyframes, no candidates -> one interval spanning the video.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..project import Project
from ..schemas import Candidates, GestureKeyframe, GestureTrack, Transcript, TranscriptSegment, VideoMeta

META = "ingest/meta.json"
TRANSCRIPT = "transcript/transcript.json"
GESTURES = "gestures/gestures.json"
CANDIDATES = "candidates/candidates.json"
SEGMENTS = "segment/segments.json"
DRAFT = "draft/steps.json"
REFINED = "refine/steps.json"
COMPLIANCE = "compliance/compliance.json"
QUESTIONS = "questions/questions.json"

GESTURE_TEXT_MAX = 300


@dataclass
class Upstream:
    meta: VideoMeta
    transcript: Transcript
    gestures: list[GestureKeyframe]
    candidates: Candidates

    @property
    def duration(self) -> float:
        return self.meta.duration


def load_upstream(project: Project) -> Upstream:
    meta = project.read(META, VideoMeta)
    transcript = project.read(TRANSCRIPT, Transcript) if project.exists(TRANSCRIPT) else Transcript(available=False)
    gestures = project.read(GESTURES, GestureTrack).keyframes if project.exists(GESTURES) else []
    candidates = project.read(CANDIDATES, Candidates) if project.exists(CANDIDATES) else Candidates(boundaries=[], activity=[])
    return Upstream(meta, transcript, sorted(gestures, key=lambda g: g.t), candidates)


def speech_in(transcript: Transcript, start: float, end: float) -> list[TranscriptSegment]:
    """Transcript segments whose midpoint lies in [start, end): each segment belongs to exactly one range."""
    if not transcript.available:
        return []
    return [s for s in transcript.segments if start <= (s.start + s.end) / 2 < end]


def speech_starting_in(transcript: Transcript, start: float, end: float, include_running: bool = False) -> list[TranscriptSegment]:
    """Segments that start in [start, end) (plus, if ``include_running``, one already running at ``start``)."""
    if not transcript.available:
        return []
    return [s for s in transcript.segments if start <= s.start < end or (include_running and s.start < start < s.end)]


def gestures_in(gestures: list[GestureKeyframe], start: float, end: float, limit: int | None = None) -> list[GestureKeyframe]:
    """Gesture keyframes in [start, end); if over ``limit``, keep evenly spaced ones, preferring non-interval reasons."""
    inside = [g for g in gestures if start <= g.t < end]
    if limit is None or len(inside) <= limit:
        return inside
    salient = [g for g in inside if any(r != "interval" for r in g.reasons)] or inside
    if len(salient) <= limit:
        return salient
    step = len(salient) / limit
    return [salient[int(i * step)] for i in range(limit)]


def gesture_line(g: GestureKeyframe) -> str:
    text = " ".join(g.text.split())
    if len(text) > GESTURE_TEXT_MAX:
        text = text[: GESTURE_TEXT_MAX - 3] + "..."
    return f"{g.id} @ {g.t:.1f}s [{g.activity}]: {text}"


def speech_line(s: TranscriptSegment) -> str:
    return f"[{s.start:.1f}-{s.end:.1f}s] \"{s.text.strip()}\""


def content_range(up: Upstream, idle_motion: float, min_idle_s: float) -> tuple[float, float]:
    """[start, end] of the video minus leading/trailing idle.

    Active = an activity sample with hands visible and motion above ``idle_motion``, or narration.
    Trimming only happens when the idle stretch is at least ``min_idle_s`` and something active exists.
    """
    duration = up.duration
    activity = sorted(up.candidates.activity, key=lambda a: a.t)
    active_t = [a.t for a in activity if a.hands_visible > 0 and a.motion_energy > idle_motion]
    spans = [(s.start, s.end) for s in up.transcript.segments] if up.transcript.available else []
    if not active_t and not spans:
        return 0.0, duration
    spacing = (activity[-1].t - activity[0].t) / max(len(activity) - 1, 1) if len(activity) > 1 else 0.0
    first = min([*active_t, *(a for a, _ in spans)])
    last = max([*(t + spacing for t in active_t), *(b for _, b in spans)])
    start = first if first >= min_idle_s else 0.0
    end = last if duration - last >= min_idle_s else duration
    start, end = max(0.0, start), min(duration, end)
    if end - start < min(min_idle_s, duration):  # degenerate: keep everything
        return 0.0, duration
    return round(start, 3), round(end, 3)
