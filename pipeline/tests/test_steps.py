"""M3 + M5: segment, draft, refine, questions against synthetic upstream artifacts and the fake LLM."""

from __future__ import annotations

import functools
import json
import logging
import tempfile
from pathlib import Path

import cv2
import numpy as np
import pytest

from tutorialgen.answers import add_answer, load_questions
from tutorialgen.llm import CachedLLM, LLMSettings, make_provider
from tutorialgen.llm import fake as fake_llm
from tutorialgen.project import Project
from tutorialgen.schemas import (ActivitySample, BoundaryCandidate, Candidates, Citation, ComplianceNote, ComplianceReport,
                                 GestureKeyframe, GestureTrack, QuestionSet, Segmentation, StepCompliance, StepList, Transcript,
                                 TranscriptSegment, VideoMeta)
from tutorialgen.stages import StageContext, draft, questions, refine, segment
from tutorialgen.steps.guards import redact, ungrounded
from tutorialgen.steps.llm_schemas import DraftStepOutput, ProposedStep, SegmentWindowOutput, SubStepOutput
from tutorialgen.steps.windows import Proposal, build_intervals, build_windows, merge_windows, snap

DURATION, FPS, W, H = 30.0, 5, 720, 360
SPEECH = [
    (2.5, 5.0, "First, wet your hands under the tap with water."),
    (6.0, 9.5, "Now apply some soap to your palms."),
    (11.0, 16.0, "Next, scrub the backs of your hands and between your fingers."),
    (18.0, 21.5, "Then rinse your hands under the water."),
    (23.0, 26.5, "Finally, dry your hands with a paper towel."),
]
BOUNDARIES = [(5.5, 0.8), (7.5, 0.3), (10.5, 0.7), (13.5, 0.35), (17.0, 0.75), (22.5, 0.8)]


@functools.lru_cache(maxsize=1)
def video_bytes() -> bytes:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "video.mp4"
        out = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), FPS, (W, H))
        for f in range(int(DURATION * FPS)):
            img = np.full((H, W, 3), (f * 3) % 255, np.uint8)
            cv2.putText(img, f"{f / FPS:.1f}s", (20, 200), cv2.FONT_HERSHEY_SIMPLEX, 3, (0, 0, 255), 4)
            out.write(img)
        out.release()
        return path.read_bytes()


def make_project(transcript: bool = True, gestures: bool = True, compliance: bool = False) -> Project:
    p = Project.create("synthetic")
    path = p.path("ingest/video.mp4")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(video_bytes())
    p.write("ingest/meta.json", VideoMeta(source="synthetic", source_kind="file", duration=DURATION, fps=FPS, width=W, height=H,
                                          frame_count=int(DURATION * FPS), has_audio=transcript, video_path="ingest/video.mp4"))
    p.write("transcript/transcript.json", Transcript(
        available=transcript, language="en" if transcript else None,
        segments=[TranscriptSegment(id=i, start=a, end=b, text=t) for i, (a, b, t) in enumerate(SPEECH)] if transcript else []))
    if gestures:
        kfs = [GestureKeyframe(id=f"g{i + 1:04d}", frame=int(t * FPS), t=t, reasons=["grip_change"] if i % 2 else ["interval"],
                               hands=[], interaction="hands_close", activity="active",
                               text=f"Right hand: power grip, moving {'down' if i % 2 else 'left'} slowly; left hand open.")
               for i, t in enumerate(np.arange(2.5, 27.0, 1.5))]
        p.write("gestures/gestures.json", GestureTrack(version="test", config_hash="x", keyframes=kfs))
    activity = [ActivitySample(t=t, motion_energy=0.1 if 2.0 <= t < 27.0 else 0.0, hands_visible=2 if 2.0 <= t < 27.0 else 0)
                for t in np.arange(0, DURATION, 0.5)]
    p.write("candidates/candidates.json", Candidates(
        boundaries=[BoundaryCandidate(t=t, frame=int(t * FPS), score=s, reasons=["hand_state_change", "narration_pause"])
                    for t, s in BOUNDARIES], activity=activity))
    if compliance:
        cite = Citation(chunk_id="d01:3", doc_name="sop.pdf", page=2, quote="Scrub for at least 20 seconds.")
        p.write("compliance/compliance.json", ComplianceReport(
            documents=[],
            steps=[StepCompliance(step_id="s03", no_relevant_guidance=False, notes=[
                ComplianceNote(id="c-s03-1", step_id="s03", kind="conflict", severity="warning",
                               text="The SOP requires scrubbing for a minimum time; the video does not show one.", citations=[cite])])],
            global_notes=[ComplianceNote(id="c-global-1", step_id=None, kind="missing_step", severity="critical",
                                         text="Remove jewellery before washing.", citations=[cite])]))
    return p


def ctx_for(p: Project, overrides: dict | None = None) -> StageContext:
    config = p.config(overrides)
    llm = CachedLLM(make_provider(config), p.path("llm_cache"), config.section("llm", LLMSettings).max_images_per_call)
    return StageContext(project=p, config=config, llm=llm, log=logging.getLogger("test"))


def cached(p: Project, task: str) -> list[dict]:
    return [json.loads(f.read_text()) for f in sorted(p.path("llm_cache").glob(f"{task}-*.json"))]


def assert_coverage(seg: Segmentation, min_step: float):
    s = seg.segments
    assert [x.id for x in s] == [f"s{i + 1:02d}" for i in range(len(s))]
    assert s[0].start == pytest.approx(seg.content_start) and s[-1].end == pytest.approx(seg.content_end)
    for a, b in zip(s, s[1:]):
        assert a.end == pytest.approx(b.start)
    assert all(x.end - x.start >= min_step for x in s)


# ---- segment ------------------------------------------------------------------------------------


def test_segment_covers_content_and_extracts_keyframes():
    p = make_project()
    segment.run(ctx_for(p))
    seg = p.read("segment/segments.json", Segmentation)
    assert seg.content_start == pytest.approx(2.0) and seg.content_end == pytest.approx(27.0)  # idle trimmed
    assert_coverage(seg, 2.0)
    assert 3 <= len(seg.segments) <= 7
    assert all(s.summary.startswith("[fake LLM]") and s.llm_calls for s in seg.segments)
    frames = sorted(p.path("segment/keyframes").glob("*.jpg"))
    assert len(frames) == len(BOUNDARIES) + 1
    assert cv2.imread(str(frames[0])).shape[1] == 640  # downscaled from 720
    call = cached(p, "segment_steps")[0]
    assert len(call["images"]) == 6  # llm.max_images_per_call: 5 single frames + one 2-panel sheet
    assert call["user"].count(" panel ") == 2 and "image 6 (frame at" in call["user"]
    assert all(f"i0{k}: " in call["user"] and "image" in call["user"].split(f"i0{k}: ")[1].split("\n")[0] for k in range(1, 8))
    assert "hands g0" in call["user"] and "wet your hands" in call["user"]


def test_segment_small_windows_merge_without_gaps_or_overlaps():
    p = make_project()
    segment.run(ctx_for(p, {"segment": {"window_s": 9, "window_overlap_s": 3, "max_candidates_per_window": 3}}))
    assert len(cached(p, "segment_steps")) >= 3
    assert_coverage(p.read("segment/segments.json", Segmentation), 2.0)


def test_segment_robust_to_bad_llm_boundaries(monkeypatch):
    def nonsense(req):
        w = req.context["window"]
        return SegmentWindowOutput(steps=[
            ProposedStep(start_s=-5, end_s=w["start"] + 3.3, summary="a", rationale="r", confidence=1.7),
            ProposedStep(start_s=w["start"] + 1.0, end_s=w["start"] + 1.2, summary="tiny overlap", rationale="r", confidence=0.5),
            ProposedStep(start_s=w["start"] + 9.7, end_s=999, summary="b", rationale="r", confidence=-1),
            ProposedStep(start_s=50, end_s=40, summary="reversed", rationale="r", confidence=0.5),
        ], notes=[])

    monkeypatch.setitem(fake_llm._HANDLERS, "segment_steps", nonsense)
    p = make_project()
    segment.run(ctx_for(p, {"segment": {"window_s": 12, "window_overlap_s": 4}}))
    seg = p.read("segment/segments.json", Segmentation)
    assert_coverage(seg, 2.0)
    assert all(0 <= s.confidence <= 1 for s in seg.segments)


def test_windows_snap_and_merge_unit():
    bs = [BoundaryCandidate(t=t, frame=0, score=0.5, reasons=[]) for t in (10, 20, 30, 40, 50)]
    intervals = build_intervals(bs, 0, 60)
    windows = build_windows(intervals, window_s=30, overlap_s=10, max_intervals=10)
    assert len(windows) >= 2 and windows[0].start == 0 and windows[-1].end == 60
    assert all(b.start < a.end for a, b in zip(windows, windows[1:]))  # overlapping
    assert snap(19.2, windows[0], 1.5) == 20 and snap(15.0, windows[0], 1.5) == 15.0 and snap(-3, windows[0], 1.5) == 0
    props = [[Proposal(0, 20, "A", "", 0.8, 0, "k0"), Proposal(20, 30, "B", "", 0.8, 0, "k0")],
             [Proposal(20, 31, "B'", "", 0.6, 1, "k1"), Proposal(31, 60, "C", "", 0.7, 1, "k1")]]
    spans = merge_windows(windows[:2] if len(windows) > 2 else windows, props, 0, 60, 2.0)
    assert spans[0].start == 0 and spans[-1].end == 60
    assert all(abs(a.end - b.start) < 1e-9 for a, b in zip(spans, spans[1:]))


def test_gesture_text_ablation_changes_prompt_and_cache_key():
    on, off = make_project(), make_project()
    segment.run(ctx_for(on))
    segment.run(ctx_for(off, {"use_gesture_text": False}))
    c_on, c_off = cached(on, "segment_steps")[0], cached(off, "segment_steps")[0]
    assert "hands g0" in c_on["user"] and "hand poses" in c_on["system"]
    assert "  hands " not in c_off["user"] and "hand poses" not in c_off["system"]
    keys_on = {f.name for f in on.path("llm_cache").glob("*.json")}
    keys_off = {f.name for f in off.path("llm_cache").glob("*.json")}
    assert keys_on.isdisjoint(keys_off)
    draft.run(ctx_for(off, {"use_gesture_text": False}))
    steps = off.read("draft/steps.json", StepList).steps
    assert all(not s.provenance.gesture_keyframe_ids for s in steps)
    assert all("Hand poses" not in c["user"] for c in cached(off, "draft_step"))


def test_no_transcript_no_gestures():
    p = make_project(transcript=False, gestures=False)
    ctx = ctx_for(p)
    segment.run(ctx)
    seg = p.read("segment/segments.json", Segmentation)
    assert_coverage(seg, 2.0)
    assert any("no transcript" in n for n in seg.notes)
    assert "no narration" in cached(p, "segment_steps")[0]["user"]
    draft.run(ctx)
    steps = p.read("draft/steps.json", StepList).steps
    assert all(s.confidence < 0.6 and any(m.field == "purpose" for m in s.missing_info) for s in steps)
    assert all(not s.provenance.transcript_segment_ids and not s.provenance.gesture_keyframe_ids for s in steps)


# ---- draft --------------------------------------------------------------------------------------


def test_draft_fills_provenance_keyframes_and_keys():
    p = make_project()
    ctx = ctx_for(p)
    segment.run(ctx)
    draft.run(ctx)
    seg = p.read("segment/segments.json", Segmentation).segments
    steps = p.read("draft/steps.json", StepList)
    assert steps.revision == 0 and [s.id for s in steps.steps] == [s.id for s in seg]
    for s, sg in zip(steps.steps, seg):
        assert s.title.startswith("[fake LLM]") and (s.start, s.end) == (sg.start, sg.end)
        assert len(s.keyframe_paths) == 3 and all(p.exists(k) and f"draft/keyframes/{s.id}/" in k for k in s.keyframe_paths)
        assert s.provenance.time_ranges[0].start == sg.start
        assert s.provenance.llm_calls[0] in sg.llm_calls and s.provenance.llm_calls[-1].startswith("draft_step-")
        assert all(m.key and m.key.startswith(f"{s.id}:missing:") for m in s.missing_info)
    ids = [i for s in steps.steps for i in s.provenance.transcript_segment_ids]
    assert sorted(ids) == list(range(len(SPEECH)))  # every narration segment belongs to exactly one step
    assert any(m.field == "duration" and m.blocking for s in steps.steps for m in s.missing_info)  # "scrub ..." step
    call = cached(p, "draft_step")[1]
    assert "Previous step:" in call["user"] and len(call["images"]) == 3


def test_draft_guard_removes_invented_numbers(monkeypatch):
    def inventive(req):
        return DraftStepOutput(title="Scrub hands", instruction="Scrub for 20 seconds in 40 °C water.", details=[], tools=[],
                               materials=["soap"], expected_result=None, cautions=[], confidence=0.9, missing_info=[],
                               substeps=[SubStepOutput(start_s=0, caption="Scrub 20 s", focus_box="B9", emphasis="40 °C",
                                                       emphasis_s=None)])

    monkeypatch.setitem(fake_llm._HANDLERS, "draft_step", inventive)
    p = make_project()
    ctx = ctx_for(p)
    segment.run(ctx)
    draft.run(ctx)
    s = p.read("draft/steps.json", StepList).steps[0]
    assert "20" not in s.instruction and "[?]" in s.instruction
    assert s.missing_info[0].blocking and "unverified" in s.missing_info[0].key and s.confidence <= 0.5
    # On-screen text obeys the same guard; an unknown box id falls back (no hands here -> full frame).
    sub = s.substeps[0]
    assert "20" not in sub.caption and "[?]" in sub.caption and sub.emphasis == "[?]" and (sub.start, sub.end) == (s.start, s.end)
    assert sub.focus == "full" and sub.focus_source == "fallback"


def test_guard_helpers():
    assert ungrounded(["Wait 20 seconds", "use two cups"], "rub for twenty seconds") == []
    assert ungrounded(["Heat to 180 °C for 5 min"], "heat it up for five minutes") == ["180 °C"]
    assert redact("Heat to 180 °C now", ["180 °C"]) == "Heat to [?] now"


# ---- refine + questions loop -------------------------------------------------------------------


def test_full_loop_only_affected_step_changes():
    p = make_project(compliance=True)
    ctx = ctx_for(p)
    segment.run(ctx)
    draft.run(ctx)
    refine.run(ctx)
    d = p.read("draft/steps.json", StepList)
    r0 = p.read("refine/steps.json", StepList)
    assert r0.revision == 0 and r0.steps == d.steps and not cached(p, "refine_step")

    questions.run(ctx)
    q1 = load_questions(p)
    assert q1.round == 1 and q1.questions and all(q.status == "open" for q in q1.questions)
    assert any(q.kind == "sop_conflict" for q in q1.questions) and any(q.kind == "sop_missing_step" for q in q1.questions)
    assert q1.questions[0].blocking and q1.questions[0].priority == 1
    target = next(q for q in q1.questions if q.kind == "missing_info" and q.step_id)
    ids_before = {tuple(q.source_refs): q.id for q in q1.questions}

    questions.run(ctx)  # re-running without new answers: same round, same ids
    assert load_questions(p) == q1

    a1 = add_answer(p, target.id, "Scrub for at least 20 seconds")
    refine.run(ctx)
    r1 = p.read("refine/steps.json", StepList)
    assert r1.revision == 1 and r1.applied_answer_ids == [a1.id]
    changed = [a.id for a, b in zip(r0.steps, r1.steps) if a != b]
    assert changed == [target.step_id]
    step = next(s for s in r1.steps if s.id == target.step_id)
    assert any("20 seconds" in f for f in step.user_supplied)
    assert not any(m.key in target.source_refs for m in step.missing_info)
    assert step.provenance.answer_ids == [a1.id] and step.provenance.llm_calls[-1].startswith("refine_step-")

    questions.run(ctx)
    q2 = load_questions(p)
    assert q2.round == 2
    by_id = {q.id: q for q in q2.questions}
    assert by_id[target.id].status == "answered"
    open1 = {q.id for q in q1.questions if q.id != target.id}
    open2 = {q.id for q in q2.questions if q.status == "open"}
    assert open1 <= open2 and target.id not in open2  # same ids; a capped-out question may move up
    for q in q2.questions:
        assert ids_before.get(tuple(q.source_refs), q.id) == q.id

    refine.run(ctx)  # nothing new: same revision, no extra LLM call
    assert p.read("refine/steps.json", StepList) == r1 and len(cached(p, "refine_step")) == 1


def test_global_answer_becomes_note_and_replaced_answer_reapplies():
    p = make_project(compliance=True)
    ctx = ctx_for(p)
    for stage in (segment, draft, refine, questions):
        stage.run(ctx)
    qs = load_questions(p).questions
    glob = next(q for q in qs if q.kind == "sop_missing_step")
    assert glob.step_id is None and glob.source_refs == ["c:global:missing_step:d01:3"] and glob.answer_type == "yes_no"
    add_answer(p, glob.id, "Yes, always")
    refine.run(ctx)
    r1 = p.read("refine/steps.json", StepList)
    assert r1.revision == 1 and r1.notes[0].question_id == glob.id and "Yes, always" in r1.notes[0].text
    assert r1.steps == p.read("draft/steps.json", StepList).steps  # no step touched, no LLM call
    assert not cached(p, "refine_step")
    questions.run(ctx)
    assert next(q for q in load_questions(p).questions if q.id == glob.id).status == "answered"

    target = next(q for q in qs if q.kind == "missing_info" and q.step_id)
    add_answer(p, target.id, "About a while")
    refine.run(ctx)
    add_answer(p, target.id, "At least 20 seconds")  # replaces the first answer; new answer id
    refine.run(ctx)
    r3 = p.read("refine/steps.json", StepList)
    assert r3.revision == 3
    step = next(s for s in r3.steps if s.id == target.step_id)
    assert any("20 seconds" in f for f in step.user_supplied) and not any("a while" in f for f in step.user_supplied)


def test_persisting_gap_is_reasked_with_same_id_and_cap(monkeypatch):
    p = make_project(compliance=True)
    ctx = ctx_for(p, {"questions": {"max_open": 2}})
    for stage in (segment, draft, refine, questions):
        stage.run(ctx)
    q1 = load_questions(p)
    assert len([q for q in q1.questions if q.status == "open"]) == 2
    target = next(q for q in q1.questions if q.kind == "missing_info")

    # A refine that resolves nothing: the gap persists, so the question is re-opened under the same id.
    orig = fake_llm._HANDLERS["refine_step"]
    monkeypatch.setitem(fake_llm._HANDLERS, "refine_step", lambda req: orig(req).model_copy(update={"resolved_missing_keys": []}))
    add_answer(p, target.id, "not sure")
    refine.run(ctx)
    questions.run(ctx)
    q2 = load_questions(p)
    again = next(q for q in q2.questions if q.id == target.id)
    assert again.status == "open" and "did not fully resolve" in again.why and again.source_refs == target.source_refs
    state = json.loads(p.path("questions/state.json").read_text())
    assert len(state["key_to_id"]) > 2  # capped-out gaps still have reserved ids


def test_answered_question_id_is_not_reused_for_a_different_gap():
    p = make_project(compliance=True)
    ctx = ctx_for(p)
    for stage in (segment, draft, refine, questions):
        stage.run(ctx)
    q1 = load_questions(p)
    target = next(q for q in q1.questions if q.kind == "missing_info" and q.step_id)
    other = next(k for k, v in json.loads(p.path("questions/state.json").read_text())["key_to_id"].items()
                 if v != target.id and k.split(":")[0] != target.step_id and ":missing:" in k)
    # An earlier round once grouped another step's gap with the target question.
    state = json.loads(p.path("questions/state.json").read_text())
    state["key_to_id"][other] = target.id
    p.write_json("questions/state.json", state)

    add_answer(p, target.id, "Use warm water")
    refine.run(ctx)
    questions.run(ctx)
    q2 = {q.id: q for q in load_questions(p).questions}
    assert q2[target.id].status == "answered" and q2[target.id].text == target.text
    reopened = [q for q in q2.values() if other in q.source_refs]
    assert reopened and all(q.id != target.id and "did not fully resolve" not in q.why for q in reopened)


def test_questions_without_compliance_and_low_confidence():
    p = make_project(transcript=False)
    ctx = ctx_for(p)
    for stage in (segment, draft, refine, questions):
        stage.run(ctx)
    qs = load_questions(p)
    assert isinstance(qs, QuestionSet) and qs.round == 1
    kinds = {q.kind for q in qs.questions}
    assert "low_confidence" in kinds and "missing_info" in kinds
    lc = next(q for q in qs.questions if q.kind == "low_confidence")
    assert lc.answer_type == "choice" and lc.choices
    assert len(qs.questions) <= 8


def test_number_guard_names_and_spoken_fractions():
    from tutorialgen.steps.guards import ungrounded

    assert ungrounded(["Open the 3D printer and fit an M3 screw, then send G28."], "no digits here") == []
    assert ungrounded(["Use a 1/8 inch bit, then a 1/16 inch bit."], "open them to one-eighth after one-sixteenth") == []
    assert ungrounded(["Rub for 20s."], "for twenty seconds") == []
    assert ungrounded(["Rub for 30s."], "for twenty seconds") == ["30"]
    assert ungrounded(["Use a 1/4 inch bit."], "open them to one-eighth") == ["4 inch"]
