"""Stage 'segment': group candidate intervals into tutorial steps with the LLM, window by window.

Reads ingest/meta.json + video, transcript, gestures and candidates; writes segment/segments.json
(Segmentation) and one representative keyframe per candidate interval in segment/keyframes/.
The window strategy and the cross-window merge are documented in ``tutorialgen.steps.windows``.
"""

from __future__ import annotations

from pydantic import BaseModel

from ..llm import LLMRequest, LLMSettings
from ..prompts import load_prompt
from ..schemas import Segmentation, StepSegment
from ..steps import fakes  # noqa: F401  (registers the fake handlers)
from ..steps.frames import extract_frames
from ..steps.llm_schemas import SegmentWindowOutput
from ..steps.upstream import SEGMENTS, content_range, gesture_line, gestures_in, load_upstream, speech_line, speech_starting_in
from ..steps.windows import Proposal, Window, build_intervals, build_windows, merge_windows, snap
from . import StageContext

TASK = "segment_steps"
KEYFRAMES = "segment/keyframes"


class SegmentConfig(BaseModel):
    window_s: float = 90.0             # max seconds of video per LLM call
    window_overlap_s: float = 15.0     # neighbouring windows share about this much
    max_candidates_per_window: int = 12
    min_step_s: float = 2.0            # shorter steps are merged into a neighbour
    snap_s: float = 1.5                # LLM times within this of a boundary snap to it
    idle_motion: float = 0.02          # activity motion_energy at or below this counts as idle
    min_idle_trim_s: float = 1.5       # leading/trailing idle shorter than this is kept
    max_gestures_per_interval: int = 4
    keyframe_width: int = 640


def use_gesture_text(ctx: StageContext) -> bool:
    return bool(ctx.config.data.get("use_gesture_text", True))


def run(ctx: StageContext) -> None:
    cfg = ctx.config.section("segment", SegmentConfig)
    max_images = ctx.config.section("llm", LLMSettings).max_images_per_call
    with_gestures = use_gesture_text(ctx)
    project = ctx.project
    up = load_upstream(project)
    start, end = content_range(up, cfg.idle_motion, cfg.min_idle_trim_s)

    intervals = build_intervals(up.candidates.boundaries, start, end)
    images = _interval_keyframes(ctx, up.meta.video_path, intervals, cfg.keyframe_width)
    windows = build_windows(intervals, cfg.window_s, cfg.window_overlap_s, cfg.max_candidates_per_window)
    prompt = load_prompt(TASK)

    proposals: list[list[Proposal]] = []
    notes = [f"content range {start:.1f}-{end:.1f}s of {up.duration:.1f}s; {len(intervals)} candidate intervals; "
             f"{len(windows)} window(s); gesture text {'on' if with_gestures else 'off'}"]
    if not up.transcript.available:
        notes.append("no transcript: segmentation used hands and images only")
    for w in windows:
        request = _window_request(prompt, w, len(windows), up, images, cfg, max_images, with_gestures)
        out, key = ctx.llm.call(request)
        props = []
        for s in out.steps:
            a, b = snap(s.start_s, w, cfg.snap_s), snap(s.end_s, w, cfg.snap_s)
            if b - a <= 0:
                continue
            props.append(Proposal(a, b, s.summary.strip(), s.rationale.strip(), min(1.0, max(0.0, s.confidence)), w.index, key))
        if not props:
            notes.append(f"window {w.index}: LLM returned no usable steps; kept as one low-confidence step")
            props = [Proposal(w.start, w.end, f"Activity from {w.start:.1f}s to {w.end:.1f}s", "no usable LLM output", 0.3, w.index, key)]
        proposals.append(props)
        notes += [f"window {w.index}: {n}" for n in out.notes]
        ctx.log.info("window %d (%.1f-%.1fs): %d steps", w.index, w.start, w.end, len(props))

    spans = merge_windows(windows, proposals, start, end, cfg.min_step_s)
    segments = []
    for k, span in enumerate(spans):
        src = span.source
        rationale = src.rationale if src else "no step proposed for this range"
        if span.notes:
            rationale += " [merge: " + "; ".join(span.notes) + "]"
        segments.append(StepSegment(
            id=f"s{k + 1:02d}", start=round(span.start, 3), end=round(span.end, 3),
            summary=src.summary if src else f"Activity from {span.start:.1f}s to {span.end:.1f}s",
            rationale=rationale, confidence=round(src.confidence if src else 0.3, 3),
            llm_calls=[src.call_key] if src else [],
        ))
    project.write(SEGMENTS, Segmentation(segments=segments, notes=notes, content_start=start, content_end=end))
    ctx.log.info("segment: %d steps", len(segments))


def _interval_keyframes(ctx: StageContext, video_rel: str, intervals, width: int) -> dict[str, str]:
    """interval id -> keyframe path (absolute), one frame at each interval's midpoint."""
    out_dir = ctx.project.stage_dir(KEYFRAMES)
    for old in out_dir.glob("*.jpg"):
        old.unlink()
    paths = [out_dir / f"{iv.id}_{iv.mid:07.2f}s.jpg" for iv in intervals]
    written = extract_frames(ctx.project.path(video_rel), [iv.mid for iv in intervals], paths, width)
    return {iv.id: str(p) for iv, p in zip(intervals, written) if p is not None}


def _pick_images(w: Window, images: dict[str, str], max_images: int) -> dict[str, int]:
    """interval id -> 1-based image number, evenly spread when the window has more intervals than images."""
    have = [iv for iv in w.intervals if iv.id in images]
    if len(have) > max_images:
        have = [have[int(k * len(have) / max_images)] for k in range(max_images)]
    return {iv.id: n + 1 for n, iv in enumerate(have)}


def _window_request(prompt, w: Window, window_count: int, up, images: dict[str, str], cfg: SegmentConfig,
                    max_images: int, with_gestures: bool) -> LLMRequest:
    chosen = _pick_images(w, images, max_images)
    boundary_lines, interval_lines, ctx_intervals = [], [], []
    for p in w.points:
        detail = f"score {p.score:.2f} ({', '.join(p.reasons)})" if p.score is not None else "window edge"
        boundary_lines.append(f"{p.id} @ {p.t:.1f}s  {detail}")
    for n, iv in enumerate(w.intervals):
        # Narration is listed where it starts (its own times show if it runs on), so a spoken cue lands on its boundary.
        speech = speech_starting_in(up.transcript, iv.start.t, iv.end.t, include_running=n == 0)
        gestures = gestures_in(up.gestures, iv.start.t, iv.end.t, cfg.max_gestures_per_interval) if with_gestures else []
        head = f"{iv.id}: {iv.start.t:.1f}-{iv.end.t:.1f}s (from {iv.start.id} to {iv.end.id})"
        if iv.id in chosen:
            head += f", image {chosen[iv.id]}"
        lines = [head]
        lines += [f"  speech {speech_line(s)}" for s in speech] or (["  speech: (none)"] if up.transcript.available else [])
        if with_gestures:
            lines += [f"  hands {gesture_line(g)}" for g in gestures] or ["  hands: (no gesture keyframes)"]
        interval_lines.append("\n".join(lines))
        ctx_intervals.append({
            "id": iv.id, "start": iv.start.t, "end": iv.end.t,
            "start_boundary": {"id": iv.start.id, "t": iv.start.t, "score": iv.start.score, "reasons": iv.start.reasons},
            "speech": [s.text.strip() for s in speech],
            "gestures": [{"id": g.id, "t": g.t, "activity": g.activity, "text": g.text} for g in gestures],
            "image": chosen.get(iv.id),
        })
    evidence = "the narration spoken in it (if any), " + (
        "a text description of the hand poses at gesture keyframes (finger states, grip, movement; derived from hand "
        "landmarks, so it can be wrong when hands are occluded), " if with_gestures else "") + (
        "and a representative frame (attached images, numbered as listed)")
    narration = "" if up.transcript.available else "There is no narration for this video: rely on the images" + (
        " and hand descriptions." if with_gestures else ".")
    system = prompt.system.format(evidence_kinds=evidence, min_step_s=cfg.min_step_s)
    user = prompt.render(
        duration=up.duration, window_index=w.index + 1, window_count=window_count, window_start=w.start, window_end=w.end,
        narration_note=narration, boundaries="\n".join(boundary_lines), intervals="\n\n".join(interval_lines),
    )
    by_number = sorted(chosen.items(), key=lambda kv: kv[1])
    return LLMRequest(
        task=TASK, system=system, user=user, schema=SegmentWindowOutput, prompt_version=prompt.version,
        images=[images[iid] for iid, _ in by_number],
        context={"window": {"index": w.index, "start": w.start, "end": w.end}, "duration": up.duration,
                 "min_step_s": cfg.min_step_s, "use_gesture_text": with_gestures, "intervals": ctx_intervals},
    )
