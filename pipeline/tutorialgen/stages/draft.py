"""Stage 'draft': one LLM call per segment drafts the step text and flags missing information.

Reads segment/segments.json plus the transcript, gestures and video; writes draft/steps.json
(StepList revision 0) and draft/keyframes/<step>/k<n>.jpg. Ids, times, keyframe paths, missing-info
keys and provenance are filled in code, never by the LLM.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from ..focus import FocusConfig, candidate_boxes, load_cuts, load_timeline
from ..focus.roi import Timeline, box_at, describe, draw_boxes
from ..gesture.summary import summarize
from ..llm import LLMRequest
from ..prompts import load_prompt
from ..schemas import FocusBox, MissingInfo, Provenance, Segmentation, Step, StepList, StepSegment, TimeRange
from ..steps import fakes  # noqa: F401  (registers the fake handlers)
from ..steps.frames import extract_frames, spread
from ..steps.guards import redact, ungrounded
from ..steps.llm_schemas import DraftStepOutput, MissingItem
from ..steps.substeps import Anchor, anchors, build_substeps
from ..steps.upstream import DRAFT, SEGMENTS, Upstream, gesture_line, gestures_in, load_upstream, speech_in, speech_line
from . import StageContext
from .segment import use_gesture_text

TASK = "draft_step"
KEYFRAMES = "draft/keyframes"


class DraftConfig(BaseModel):
    keyframes_per_step: int = 3        # 2-3 frames from inside each step go to the LLM
    keyframe_width: int = 640
    max_gestures_per_step: int = 8
    unverified_confidence: float = 0.5  # confidence cap when the guard removed an ungrounded number
    # summary: the hands are described per anchor-to-anchor stretch (computed from every landmark sample);
    # keyframes: raw keyframe lines (original format). Without hands/frames.jsonl keyframe lines are used.
    gesture_format: Literal["summary", "keyframes", "both"] = "summary"
    max_anchors: int = 10              # candidate sub-step start times offered to the LLM
    max_substeps: int = 4
    min_substep_s: float = 1.0
    substep_snap_s: float = 1.0        # sub-step starts within this of an anchor snap to it
    caption_max_chars: int = 44        # on-screen caption bound (cut at a word boundary)
    emphasis_max_chars: int = 24


def missing_key(step_id: str, field: str, taken: set[str]) -> str:
    key, n = f"{step_id}:missing:{field}", 2
    while key in taken:
        key, n = f"{step_id}:missing:{field}:{n}", n + 1
    taken.add(key)
    return key


def to_missing(step_id: str, items: list[MissingItem], taken: set[str]) -> list[MissingInfo]:
    return [MissingInfo(field=m.field, description=m.description.strip(), blocking=m.blocking,
                        key=missing_key(step_id, m.field, taken)) for m in items]


def run(ctx: StageContext) -> None:
    cfg = ctx.config.section("draft", DraftConfig)
    with_gestures = use_gesture_text(ctx)
    project = ctx.project
    up = load_upstream(project)
    segments = project.read(SEGMENTS, Segmentation).segments
    prompt = load_prompt(TASK)
    shutil.rmtree(project.path(KEYFRAMES), ignore_errors=True)
    focus = ctx.config.section("focus", FocusConfig)
    need_timeline = focus.boxes_in_prompt or (with_gestures and cfg.gesture_format != "keyframes")
    timeline = load_timeline(project, ctx.config) if need_timeline else None
    cuts = load_cuts(project)

    steps = []
    for k, seg in enumerate(segments):
        prev_seg = segments[k - 1] if k > 0 else None
        next_seg = segments[k + 1] if k + 1 < len(segments) else None
        times = spread(seg.start, seg.end, max(1, cfg.keyframes_per_step))
        out_paths = [project.path(f"{KEYFRAMES}/{seg.id}/k{n + 1}.jpg") for n in range(len(times))]
        extracted = extract_frames(project.path(up.meta.video_path), times, out_paths, cfg.keyframe_width)
        frame_times = [t for t, p in zip(times, extracted) if p]
        frames = [p for p in extracted if p]
        speech = speech_in(up.transcript, seg.start, seg.end)
        gestures = gestures_in(up.gestures, seg.start, seg.end, cfg.max_gestures_per_step) if with_gestures else []
        all_gestures = gestures_in(up.gestures, seg.start, seg.end)
        boxes = candidate_boxes(timeline, cuts, seg.start, seg.end, focus) if focus.boxes_in_prompt and timeline else []
        shown = _annotate(frames, frame_times, boxes) if boxes else list(frames)
        anchor_list = anchors(seg.start, seg.end, speech, all_gestures, cfg.max_anchors)
        hands_tl = timeline if with_gestures and cfg.gesture_format != "keyframes" else None

        request = _request(prompt, seg, k, len(segments), prev_seg, next_seg, up, speech, gestures, shown, frame_times,
                           with_gestures, anchor_list, boxes, hands_tl, cfg)
        out, key = ctx.llm.call(request)
        step = _to_step(seg, k, out, cfg, up, prev_seg, next_seg, anchor_list, boxes, all_gestures)
        step.keyframe_paths = [project.rel(p) for p in frames]
        step.provenance = Provenance(
            time_ranges=[TimeRange(start=seg.start, end=seg.end)],
            gesture_keyframe_ids=[g.id for g in gestures],
            transcript_segment_ids=[s.id for s in speech],
            llm_calls=[*seg.llm_calls, key],
        )
        steps.append(step)
    project.write(DRAFT, StepList(revision=0, steps=steps))
    ctx.log.info("draft: %d steps", len(steps))


def _annotate(frames: list[Path], times: list[float], boxes: list[FocusBox]) -> list[Path]:
    """Copies of the keyframes with the focus boxes present at each frame's time drawn and labelled."""
    import cv2

    out = []
    for path, t in zip(frames, times):
        img = cv2.imread(str(path))
        if img is None or not draw_boxes(img, boxes, t):
            out.append(path)
            continue
        dest = path.with_name(path.stem + "_boxes.jpg")
        cv2.imwrite(str(dest), img, [cv2.IMWRITE_JPEG_QUALITY, 85])
        out.append(dest)
    return out


BOX_MEANING = {"hands": "everything the hands cover", "work_zone": "where the hands meet or hold something, i.e. the object worked on",
               "right_hand": "the right hand alone", "left_hand": "the left hand alone"}


def boxes_text(boxes: list[FocusBox], times: list[float]) -> str:
    """One line per box: what it is and where it is on each attached image (or that it is absent there)."""
    lines = []
    for b in boxes:
        where = []
        for n, t in enumerate(times, 1):
            box = box_at(b, t)
            where.append(f"image {n}: {describe(box)}" if box else f"image {n}: not shown")
        lines.append(f"{b.id} {b.label} ({BOX_MEANING[b.kind]}) - " + "; ".join(where))
    lines.append("full - the whole frame (when the surroundings matter or no box fits)")
    return "\n".join(lines)


def anchors_text(anchor_list: list[Anchor], end: float, gestures, timeline: Timeline | None, with_gestures: bool) -> str:
    lines = []
    by_id = {g.id: g for g in gestures}
    for k, a in enumerate(anchor_list):
        nxt = anchor_list[k + 1].t if k + 1 < len(anchor_list) else end
        line = f"{a.id} @ {a.t:.1f}s ({a.source})"
        if with_gestures and timeline is not None:
            line += f" - hands until {nxt:.1f}s: {summarize(timeline.between(a.t, nxt)).text()}"
        elif with_gestures and a.keyframe_id in by_id:
            line += f" - {gesture_line(by_id[a.keyframe_id])}"
        lines.append(line)
    return "\n".join(lines)


def _request(prompt, seg: StepSegment, k: int, count: int, prev_seg, next_seg, up: Upstream, speech, gestures, frames,
             frame_times: list[float], with_gestures: bool, anchor_list: list[Anchor], boxes: list[FocusBox],
             timeline: Timeline | None, cfg: DraftConfig) -> LLMRequest:
    if up.transcript.available:
        speech_text = "\n".join(speech_line(s) for s in speech) or "(nothing said during this step)"
    else:
        speech_text = "(this video has no narration)"
    gesture_text = ""
    if with_gestures and (timeline is None or cfg.gesture_format == "both"):
        gesture_text = "\nHand poses at gesture keyframes (derived from landmarks; may be wrong when hands are occluded):\n" + (
            "\n".join(gesture_line(g) for g in gestures) or "(no gesture keyframes in this step)") + "\n"
    summarized = with_gestures and timeline is not None
    evidence = "the narration spoken during the step, " + (
        "text descriptions of the hands (from hand landmarks; may be wrong when hands are occluded), " if with_gestures else "") + (
        "and a few frames from inside the step (attached images, in time order)")
    system = prompt.system.format(evidence_kinds=evidence, max_substeps=cfg.max_substeps, caption_chars=cfg.caption_max_chars,
                                  emphasis_chars=cfg.emphasis_max_chars)
    user = prompt.render(
        step_number=k + 1, step_count=count, start=seg.start, end=seg.end, summary=seg.summary,
        prev_summary=prev_seg.summary if prev_seg else "(none, this is the first step)",
        next_summary=next_seg.summary if next_seg else "(none, this is the last step)",
        speech=speech_text, gestures=gesture_text,
        image_note=f"{len(frames)} attached: " + ", ".join(f"image {n} at {t:.1f}s" for n, t in enumerate(frame_times, 1))
        if frames else "none available",
        anchors=anchors_text(anchor_list, seg.end, gestures, timeline, with_gestures),
        anchor_note=", each with a summary of the hands until the next anchor" if summarized else "",
        boxes=boxes_text(boxes, frame_times) if boxes else "(no hand boxes for this step: use full)",
        box_note=" They are drawn and labelled on the images." if boxes else "",
    )
    return LLMRequest(
        task=TASK, system=system, user=user, schema=DraftStepOutput, prompt_version=prompt.version, images=list(frames),
        context={"step_id": seg.id, "index": k, "start": seg.start, "end": seg.end, "summary": seg.summary,
                 "prev_summary": prev_seg.summary if prev_seg else None, "next_summary": next_seg.summary if next_seg else None,
                 "transcript_available": up.transcript.available, "use_gesture_text": with_gestures,
                 "speech": [s.text.strip() for s in speech],
                 "speech_segments": [{"start": s.start, "end": s.end, "text": s.text.strip()} for s in speech],
                 "gestures": [{"id": g.id, "t": g.t, "activity": g.activity, "text": g.text} for g in gestures],
                 "anchors": [{"id": a.id, "t": a.t, "source": a.source} for a in anchor_list],
                 "boxes": [b.id for b in boxes]},
    )


def _to_step(seg: StepSegment, k: int, out: DraftStepOutput, cfg: DraftConfig, up: Upstream, prev_seg, next_seg,
             anchor_list: list[Anchor] | None = None, boxes: list[FocusBox] | None = None, gestures=None) -> Step:
    taken: set[str] = set()
    missing = to_missing(seg.id, out.missing_info, taken)
    confidence = min(1.0, max(0.0, out.confidence))
    substeps = build_substeps(out.substeps, seg.start, seg.end, anchor_list or [], boxes or [], gestures or [],
                              max_substeps=cfg.max_substeps, min_s=cfg.min_substep_s, snap_s=cfg.substep_snap_s,
                              caption_chars=cfg.caption_max_chars, emphasis_chars=cfg.emphasis_max_chars,
                              default_caption=out.title)
    # Guard: numbers must come from the narration of this step or its neighbours.
    lo = prev_seg.start if prev_seg else seg.start
    hi = next_seg.end if next_seg else seg.end
    # The prompt's own step number and times are not invented values either.
    evidence = " ".join([*(s.text for s in speech_in(up.transcript, lo, hi)), f"{k + 1} {seg.start:.1f} {seg.end:.1f}"])
    fields = {"title": out.title, "instruction": out.instruction, "expected_result": out.expected_result or ""}
    lists = {"details": out.details, "tools": out.tools, "materials": out.materials, "cautions": out.cautions}
    on_screen = [x for s in substeps for x in (s.caption, s.emphasis or "")]
    bad = ungrounded([*fields.values(), *(x for v in lists.values() for x in v), *on_screen], evidence)
    if bad:
        fields = {n: redact(v, bad) for n, v in fields.items()}
        lists = {n: [redact(x, bad) for x in v] for n, v in lists.items()}
        for s in substeps:  # on-screen text obeys the same rule as the step text
            s.caption = redact(s.caption, bad)
            s.emphasis = redact(s.emphasis, bad) if s.emphasis else None
        missing.insert(0, MissingInfo(
            field="setting" if any(c.isalpha() for c in "".join(bad)) else "quantity", blocking=True,
            description=f"The draft stated {', '.join(repr(b) for b in bad)}, which the narration does not support; "
                        "the value was removed and needs confirming.",
            key=missing_key(seg.id, "unverified", taken)))
        confidence = min(confidence, cfg.unverified_confidence)
    missing.sort(key=lambda m: not m.blocking)
    return Step(
        id=seg.id, index=k, start=seg.start, end=seg.end, title=fields["title"].strip(),
        instruction=fields["instruction"].strip(), details=lists["details"], tools=lists["tools"],
        materials=lists["materials"], expected_result=fields["expected_result"].strip() or None,
        cautions=lists["cautions"], confidence=round(confidence, 3), missing_info=missing,
        substeps=substeps, focus_boxes=boxes or [],
    )
