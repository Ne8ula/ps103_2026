"""Stage 'draft': one LLM call per segment drafts the step text and flags missing information.

Reads segment/segments.json plus the transcript, gestures and video; writes draft/steps.json
(StepList revision 0) and draft/keyframes/<step>/k<n>.jpg. Ids, times, keyframe paths, missing-info
keys and provenance are filled in code, never by the LLM.
"""

from __future__ import annotations

import shutil

from pydantic import BaseModel

from ..llm import LLMRequest
from ..prompts import load_prompt
from ..schemas import MissingInfo, Provenance, Segmentation, Step, StepList, StepSegment, TimeRange
from ..steps import fakes  # noqa: F401  (registers the fake handlers)
from ..steps.frames import extract_frames, spread
from ..steps.guards import redact, ungrounded
from ..steps.llm_schemas import DraftStepOutput, MissingItem
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

    steps = []
    for k, seg in enumerate(segments):
        prev_seg = segments[k - 1] if k > 0 else None
        next_seg = segments[k + 1] if k + 1 < len(segments) else None
        times = spread(seg.start, seg.end, max(1, cfg.keyframes_per_step))
        out_paths = [project.path(f"{KEYFRAMES}/{seg.id}/k{n + 1}.jpg") for n in range(len(times))]
        frames = [p for p in extract_frames(project.path(up.meta.video_path), times, out_paths, cfg.keyframe_width) if p]
        speech = speech_in(up.transcript, seg.start, seg.end)
        gestures = gestures_in(up.gestures, seg.start, seg.end, cfg.max_gestures_per_step) if with_gestures else []

        request = _request(prompt, seg, k, len(segments), prev_seg, next_seg, up, speech, gestures, frames, with_gestures)
        out, key = ctx.llm.call(request)
        step = _to_step(seg, k, out, cfg, up, prev_seg, next_seg)
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


def _request(prompt, seg: StepSegment, k: int, count: int, prev_seg, next_seg, up: Upstream, speech, gestures, frames,
             with_gestures: bool) -> LLMRequest:
    if up.transcript.available:
        speech_text = "\n".join(speech_line(s) for s in speech) or "(nothing said during this step)"
    else:
        speech_text = "(this video has no narration)"
    gesture_text = ""
    if with_gestures:
        gesture_text = "\nHand poses at gesture keyframes (derived from landmarks; may be wrong when hands are occluded):\n" + (
            "\n".join(gesture_line(g) for g in gestures) or "(no gesture keyframes in this step)") + "\n"
    evidence = "the narration spoken during the step, " + (
        "text descriptions of the hand poses at gesture keyframes, " if with_gestures else "") + (
        "and a few frames from inside the step (attached images, in time order)")
    system = prompt.system.format(evidence_kinds=evidence)
    user = prompt.render(
        step_number=k + 1, step_count=count, start=seg.start, end=seg.end, summary=seg.summary,
        prev_summary=prev_seg.summary if prev_seg else "(none, this is the first step)",
        next_summary=next_seg.summary if next_seg else "(none, this is the last step)",
        speech=speech_text, gestures=gesture_text,
        image_note=f"{len(frames)} attached, at " + ", ".join(f"{t:.1f}s" for t in spread(seg.start, seg.end, len(frames)))
        if frames else "none available",
    )
    return LLMRequest(
        task=TASK, system=system, user=user, schema=DraftStepOutput, prompt_version=prompt.version, images=list(frames),
        context={"step_id": seg.id, "index": k, "start": seg.start, "end": seg.end, "summary": seg.summary,
                 "prev_summary": prev_seg.summary if prev_seg else None, "next_summary": next_seg.summary if next_seg else None,
                 "transcript_available": up.transcript.available, "use_gesture_text": with_gestures,
                 "speech": [s.text.strip() for s in speech],
                 "gestures": [{"id": g.id, "t": g.t, "activity": g.activity, "text": g.text} for g in gestures]},
    )


def _to_step(seg: StepSegment, k: int, out: DraftStepOutput, cfg: DraftConfig, up: Upstream, prev_seg, next_seg) -> Step:
    taken: set[str] = set()
    missing = to_missing(seg.id, out.missing_info, taken)
    confidence = min(1.0, max(0.0, out.confidence))
    # Guard: numbers must come from the narration of this step or its neighbours.
    lo = prev_seg.start if prev_seg else seg.start
    hi = next_seg.end if next_seg else seg.end
    # The prompt's own step number and times are not invented values either.
    evidence = " ".join([*(s.text for s in speech_in(up.transcript, lo, hi)), f"{k + 1} {seg.start:.1f} {seg.end:.1f}"])
    fields = {"title": out.title, "instruction": out.instruction, "expected_result": out.expected_result or ""}
    lists = {"details": out.details, "tools": out.tools, "materials": out.materials, "cautions": out.cautions}
    bad = ungrounded([*fields.values(), *(x for v in lists.values() for x in v)], evidence)
    if bad:
        fields = {n: redact(v, bad) for n, v in fields.items()}
        lists = {n: [redact(x, bad) for x in v] for n, v in lists.items()}
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
    )
