"""Hand-driven focus: ROI candidates from synthetic landmarks, crop fitting and smoothing, sub-step
validation (box ids, snapping, bounds), compact gesture summaries, and a render that zooms toward a hand."""

from __future__ import annotations

import numpy as np
import pytest

from tutorialgen.focus.crop import CropTrack, contain, fit_crop, is_full, plan, smoothstep, to_crop
from tutorialgen.focus.roi import FocusConfig, Timeline, box_at, candidate_boxes, region_box, shots
from tutorialgen.gesture import GestureConfig, build_timeline
from tutorialgen.gesture.summary import summarize
from tutorialgen.schemas import (CropSegment, FocusBox, FocusRegion, GestureKeyframe, Hand, HandFrame, Step, SubStep,
                                 Tutorial, TranscriptSegment)
from tutorialgen.steps.llm_schemas import DraftStepOutput, SubStepOutput
from tutorialgen.steps.substeps import anchors, bound_text, build_substeps

from test_gestures import open_hand as gesture_open_hand, to_landmarks  # noqa: E402  (tests dir is on sys.path)

ASPECT = 4 / 3


def open_hand(cx: float, cy: float, handedness: str = "Right", size: float = 0.06) -> Hand:
    """An anatomically plausible open hand (test_gestures' pose) with its wrist at (cx, cy); ``size`` = palm scale."""
    return Hand(handedness=handedness, score=0.95,
                landmarks=to_landmarks(gesture_open_hand(), left=handedness == "Left", scale=size, centre=(cx, cy), aspect=ASPECT))


def make_timeline(samples: list[HandFrame]) -> Timeline:
    return Timeline(build_timeline(samples, ASPECT, GestureConfig()), ASPECT)


def frames(t0: float, t1: float, hands_at, fps: float = 10.0) -> list[HandFrame]:
    out = []
    for k in range(int(round((t1 - t0) * fps))):
        t = round(t0 + k / fps, 3)
        out.append(HandFrame(frame=int(t * 25), t=t, hands=hands_at(t)))
    return out


def all_points(samples: list[HandFrame]) -> np.ndarray:
    return np.array([p[:2] for f in samples for h in f.hands for p in h.landmarks])


# ---- ROI candidates ----------------------------------------------------------------------------


def test_hands_box_contains_every_hand_and_is_per_shot():
    # Shot 1 (0-4 s): a right hand drifting at the left; shot 2 (4-8 s): two hands at the right.
    shot1 = frames(0, 4, lambda t: [open_hand(0.25 + 0.02 * t, 0.5)])
    shot2 = frames(4, 8, lambda t: [open_hand(0.65, 0.45), open_hand(0.85, 0.45, "Left")])
    tl = make_timeline(shot1 + shot2)
    cfg = FocusConfig()
    boxes = {b.id: b for b in candidate_boxes(tl, [4.0], 0.0, 8.0, cfg)}
    hands = boxes["B1"]
    assert [(r.start, r.end) for r in hands.regions] == [(0.0, 4.0), (4.0, 8.0)]
    for region, samples in zip(hands.regions, (shot1, shot2)):
        pts = all_points(samples)
        x0, y0, x1, y1 = region.box
        assert (pts[:, 0] >= x0).all() and (pts[:, 0] <= x1).all() and (pts[:, 1] >= y0).all() and (pts[:, 1] <= y1).all()
        assert x0 < pts[:, 0].min() and x1 > pts[:, 0].max()  # padded
        assert region.coverage == pytest.approx(1.0)
    assert box_at(hands, 2.0)[2] < 0.55 and box_at(hands, 6.0)[0] > 0.45  # each shot keeps its own box


def test_work_zone_is_the_contact_region_and_needs_support():
    # Two hands overlapping around x = 0.5: the work zone sits where they touch and is smaller than B1.
    touching = frames(0, 3, lambda t: [open_hand(0.47, 0.6, size=0.08), open_hand(0.53, 0.6, "Left", size=0.08)])
    tl = make_timeline(touching)
    cfg = FocusConfig()
    hands = region_box(tl, "hands", 0, 3, cfg)
    zone = region_box(tl, "work_zone", 0, 3, cfg)
    assert zone is not None and hands is not None
    area = lambda b: (b[2] - b[0]) * (b[3] - b[1])  # noqa: E731
    assert area(zone.box) < area(hands.box)
    assert zone.box[0] < 0.5 < zone.box[2]
    # Hands far apart and open: no contact, no grip -> no work zone; single-hand boxes are offered instead.
    apart = make_timeline(frames(0, 3, lambda t: [open_hand(0.2, 0.5), open_hand(0.8, 0.5, "Left")]))
    assert region_box(apart, "work_zone", 0, 3, cfg) is None
    ids = [b.id for b in candidate_boxes(apart, [], 0, 3, cfg)]
    assert ids == ["B1", "B3", "B4"]


def test_no_box_without_enough_hands():
    sparse = frames(0, 4, lambda t: [open_hand(0.5, 0.5)] if t < 0.5 else [])
    tl = make_timeline(sparse)
    assert region_box(tl, "hands", 0, 4, FocusConfig()) is None  # 12% coverage < min_coverage
    assert candidate_boxes(tl, [], 0, 4, FocusConfig()) == []
    assert [(s.start, s.end) for s in shots([1.0, 9.0, 3.0], 0, 4)] == [(0, 1.0), (1.0, 3.0), (3.0, 4)]


# ---- crop fitting and smoothing ----------------------------------------------------------------


def test_fit_crop_preserves_aspect_and_limits_zoom():
    cfg = FocusConfig(max_zoom=2.0, min_crop_frac=0.4, min_zoom_gain=1.15)
    tiny = fit_crop([0.9, 0.9, 0.95, 0.95], cfg)
    assert tiny[2] - tiny[0] == pytest.approx(0.5) and tiny[3] - tiny[1] == pytest.approx(0.5)  # max zoom 2
    assert tiny[2] == pytest.approx(1.0) and tiny[3] == pytest.approx(1.0)  # shifted inside the frame
    wide = fit_crop([0.1, 0.3, 0.7, 0.5], cfg)
    assert wide[2] - wide[0] == pytest.approx(0.6) == pytest.approx(wide[3] - wide[1])  # square = frame aspect
    assert wide[0] <= 0.1 and wide[2] >= 0.7
    assert fit_crop([0.05, 0.05, 0.95, 0.95], cfg) is None  # zoom 1.1 < min gain: stay full frame
    assert fit_crop([0.4, 0.4, 0.6, 0.6], FocusConfig(max_zoom=1.0)) is None


def test_crop_track_eases_within_a_shot_and_cuts_hard():
    cfg = FocusConfig(pan_s=1.0)
    a, b = [0.0, 0.0, 0.5, 0.5], [0.5, 0.5, 1.0, 1.0]
    segs = [CropSegment(start=0, end=2, rect=a, focus="B1", reason="", cut_before=True),
            CropSegment(start=2, end=4, rect=b, focus="B2", reason="", cut_before=False),
            CropSegment(start=4, end=6, rect=a, focus="B1", reason="", cut_before=True)]
    track = CropTrack(segs, cfg)
    xs = [track.rect_at(t)[0] for t in np.arange(1.9, 3.2, 0.1)]
    assert xs[0] == 0.0 and xs[-1] == pytest.approx(0.5)
    assert all(q >= p - 1e-9 for p, q in zip(xs, xs[1:]))  # monotonic pan
    assert max(abs(q - p) for p, q in zip(xs, xs[1:])) < 0.1  # no jump inside the shot
    assert track.rect_at(3.99) == b and track.rect_at(4.0) == a  # cut: hard switch
    assert smoothstep(0) == 0 and smoothstep(1) == 1 and smoothstep(0.5) == pytest.approx(0.5)


def test_contain_never_crops_a_hand_out():
    rect = [0.2, 0.2, 0.6, 0.6]
    rng = np.random.default_rng(0)
    for _ in range(200):
        pts = rng.uniform(0, 1, size=(21, 2)) * rng.uniform(0.1, 0.6) + rng.uniform(0, 0.5, size=2)
        out = contain(rect, pts, 0.02)
        assert out[2] - out[0] == pytest.approx(out[3] - out[1])  # aspect kept
        assert 0 <= out[0] and out[2] <= 1 + 1e-9 and 0 <= out[1] and out[3] <= 1 + 1e-9
        inside = np.clip(pts, 0, 1)
        assert (inside[:, 0] >= out[0] - 1e-9).all() and (inside[:, 0] <= out[2] + 1e-9).all()
        assert (inside[:, 1] >= out[1] - 1e-9).all() and (inside[:, 1] <= out[3] + 1e-9).all()
    assert contain(rect, np.array([[0.3, 0.3]]), 0.02) == rect  # already inside: unchanged
    lm = np.array([[0.4, 0.4, 0.0]])
    assert to_crop(lm, rect)[0, :2] == pytest.approx([0.5, 0.5])


def test_letterbox_is_detected_and_zoomed_crops_avoid_it(tmp_path):
    import cv2

    from tutorialgen.focus import content_box
    from tutorialgen.focus.crop import inside_content

    path = tmp_path / "lb.mp4"
    out = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 10, (160, 120))
    for k in range(20):
        f = np.zeros((120, 160, 3), np.uint8)
        f[15:105] = 60 + 5 * k  # picture rows 15..104: bars of 15 px top and bottom
        out.write(f)
    out.release()
    box = content_box(path)
    assert box[0] == 0 and box[2] == 1 and box[1] == pytest.approx(15 / 120, abs=0.02) and box[3] == pytest.approx(105 / 120, abs=0.02)
    content = [0.0, 0.125, 1.0, 0.875]
    assert inside_content([0.1, 0.0, 0.6, 0.5], content) == [0.1, 0.125, 0.6, 0.625]  # moved off the top bar
    assert inside_content([0.1, 0.05, 0.9, 0.85], content)[1] == pytest.approx(0.05)  # taller than the picture: left as is
    assert inside_content([0.0, 0.0, 1.0, 1.0], content) == [0.0, 0.0, 1.0, 1.0]  # full frame untouched


def test_containment_is_eased_but_never_violated():
    seg = CropSegment(start=0, end=2, rect=[0.3, 0.3, 0.7, 0.7], focus="B1", reason="", cut_before=True)
    track = CropTrack([seg], FocusConfig())
    times = [k / 25 for k in range(50)]
    spike = np.array([[0.9, 0.5], [0.95, 0.55]])  # a hand near the right edge for one frame only
    points = [spike if k == 25 else None for k in range(50)]
    raw = [track.rect_at(t, p) for t, p in zip(times, points)]
    eased = track.rects(times, points, ramp_frames=10)
    r = eased[25]  # the spike frame holds the hand
    assert r[0] <= 0.9 and r[2] >= 0.95 and r[1] <= 0.5 and r[3] >= 0.55
    jump = lambda rs: max(abs(b[2] - a[2]) for a, b in zip(rs, rs[1:]))  # noqa: E731
    assert jump(raw) > 0.2 and jump(eased) < 0.06  # one-frame pop vs. a ramp
    assert eased[0] == seg.rect and eased[49] == seg.rect  # far from the spike: the planned crop
    assert all(abs((r[2] - r[0]) - (r[3] - r[1])) < 1e-9 for r in eased)  # aspect kept throughout


def test_plan_uses_requested_box_falls_back_and_respects_cuts():
    samples = frames(0, 6, lambda t: [open_hand(0.3, 0.5)] if t < 4 else [])
    tl = make_timeline(samples)
    step = Step(id="s01", index=0, start=0, end=6, title="t", instruction="i", confidence=0.9, substeps=[
        SubStep(start=0, end=2, caption="a", focus="B2"),     # no work zone here -> B1
        SubStep(start=2, end=6, caption="b", focus="B1")])    # hands gone after the cut at 4 s -> full
    segs = plan(step, tl, [4.0], FocusConfig())
    assert [(s.start, s.end) for s in segs] == [(0, 2), (2, 4), (4, 6)]
    assert "B1" in segs[0].reason and not is_full(segs[0].rect) and segs[0].cut_before
    assert not segs[1].cut_before and segs[2].cut_before
    assert is_full(segs[2].rect) and "full frame" in segs[2].reason
    assert all(is_full(s.rect) for s in plan(step, tl, [4.0], FocusConfig(enabled=False)))
    old = step.model_copy(update={"substeps": []})  # steps drafted before sub-steps: no zoom
    assert all(is_full(s.rect) for s in plan(old, tl, [], FocusConfig()))


# ---- sub-steps: anchors, snapping, ids, bounds ---------------------------------------------------


def _kf(i: int, t: float, reasons: list[str]) -> GestureKeyframe:
    return GestureKeyframe(id=f"g{i:04d}", frame=int(t * 25), t=t, reasons=reasons, hands=[], interaction="none",
                           activity="active", text=".")


def test_build_substeps_validates_ids_snaps_and_bounds():
    speech = [TranscriptSegment(id=0, start=10.2, end=12.0, text="Scrub the palms."),
              TranscriptSegment(id=1, start=13.1, end=15.0, text="Now between your fingers.")]
    gestures = [_kf(1, 11.0, ["interval"]), _kf(2, 13.4, ["grip_change"]), _kf(3, 16.0, ["interaction_change"])]
    anc = anchors(10.0, 18.0, speech, gestures)
    assert [a.t for a in anc] == [10.0, 13.1, 16.0]  # step start, narration, grip change folded into 13.1, interaction
    assert anc[1].keyframe_id == "g0002" and "grip change" in anc[1].source
    boxes = [FocusBox(id="B1", kind="hands", label="both hands", regions=[FocusRegion(start=10, end=18, box=[0, 0, 1, 1], coverage=1)])]
    out = [SubStepOutput(start_s=10.4, caption="Scrub the palms together firmly with soap until foamy", focus_box="B1",
                         emphasis=None, emphasis_s=None),
           SubStepOutput(start_s=13.5, caption="Scrub between fingers.", focus_box="B2", emphasis="between fingers",
                         emphasis_s=99.0),
           SubStepOutput(start_s=17.6, caption="too short", focus_box="FULL", emphasis=None, emphasis_s=None)]
    subs = build_substeps(out, 10.0, 18.0, anc, boxes, gestures, caption_chars=30)
    assert [(s.start, s.end) for s in subs] == [(10.0, 13.1), (13.1, 18.0)]  # snapped; the 0.4 s phase dropped
    assert subs[0].caption == "Scrub the palms together" and len(subs[0].caption) <= 30
    assert subs[1].caption == "Scrub between fingers"
    assert subs[0].focus == "B1" and subs[0].focus_source == "llm"
    assert subs[1].focus == "B1" and subs[1].focus_source == "fallback"  # B2 was never offered
    assert subs[1].emphasis == "between fingers" and 13.1 <= subs[1].emphasis_t <= 18.0
    assert subs[1].gesture_keyframe_ids == ["g0002", "g0003"]
    empty = build_substeps([], 0, 5, [], [], [], default_caption="Rinse your hands")
    assert len(empty) == 1 and empty[0].caption == "Rinse your hands" and empty[0].focus == "full"
    assert bound_text("  a  b. ", 10) == "a b"


def test_llm_schemas_are_strict_output_friendly():
    for model in (SubStepOutput, DraftStepOutput):
        schema = model.model_json_schema()
        assert set(schema["required"]) == set(schema["properties"]), model.__name__
        assert schema.get("additionalProperties") is False
        assert not any("default" in p for p in schema["properties"].values())
    from openai.lib._pydantic import to_strict_json_schema  # what the OpenAI and Gemini adapters send

    strict = to_strict_json_schema(DraftStepOutput)
    sub = strict["$defs"]["SubStepOutput"]
    assert sub["additionalProperties"] is False and set(sub["required"]) == set(sub["properties"])


def test_draft_with_substeps_round_trips_through_gemini_adapter(monkeypatch, tmp_path):
    """Mocked HTTP: the strict schema with sub-steps is sent, and a reply with sub-steps parses."""
    import json

    import httpx
    from test_llm_providers import completion, provider_with

    from tutorialgen.llm import LLMRequest

    reply = {"title": "Scrub hands", "instruction": "Scrub all surfaces.", "details": [], "tools": [], "materials": ["soap"],
             "expected_result": None, "cautions": [], "confidence": 0.8, "missing_info": [],
             "substeps": [{"start_s": 14.4, "caption": "Scrub palms", "focus_box": "B2", "emphasis": None, "emphasis_s": None},
                          {"start_s": 18.3, "caption": "Scrub between fingers", "focus_box": "B1",
                           "emphasis": "between fingers", "emphasis_s": 19.0}]}
    bodies: list[dict] = []
    p = provider_with(monkeypatch, [httpx.Response(200, json=completion(json.dumps(reply)))], bodies)
    out = p.generate(LLMRequest(task="draft_step", system="S", user="U", schema=DraftStepOutput))
    assert [s.focus_box for s in out.substeps] == ["B2", "B1"] and out.substeps[1].emphasis == "between fingers"
    sent = bodies[0]["response_format"]["json_schema"]
    assert sent["strict"] is True and "SubStepOutput" in sent["schema"]["$defs"]


# ---- compact gesture summaries ------------------------------------------------------------------


def test_summary_reports_visibility_contact_and_back_and_forth():
    def rubbing(t):  # right hand oscillates left-right over the left hand, ~2 Hz
        x = 0.5 + 0.04 * np.sin(2 * np.pi * 2 * t)
        return [open_hand(x, 0.6, size=0.08), open_hand(0.52, 0.62, "Left", size=0.08)]
    s = summarize(make_timeline(frames(0, 3, rubbing, fps=15)).frames)
    assert s.both == pytest.approx(1.0) and s.contact > 0.9
    assert s.motion == "back-and-forth left-right"
    text = s.text()
    assert "both hands 100%" in text and "back-and-forth left-right" in text and "touching" in text
    gone = summarize(make_timeline(frames(0, 2, lambda t: [])).frames)
    assert gone.text() == "no hands visible"


# ---- render: the crop zooms toward the hand ----------------------------------------------------


def test_render_zooms_toward_the_hand():
    import logging

    from test_render import FAST, FPS, H, W, decode, make_project

    from tutorialgen.config import Config
    from tutorialgen.render.overlay import HAND_COLORS
    from tutorialgen.stages import StageContext
    from tutorialgen.stages.render import run as render_run
    from tutorialgen.schemas import StepList

    def hand_pixels(frame):
        diff = np.abs(frame.astype(int) - np.array(HAND_COLORS["Right"])).max(axis=2)
        ys, xs = np.nonzero(diff < 40)
        return xs, ys

    sizes = {}
    for enabled in (False, True):
        p = make_project(audio=False, compliance=False, questions=False)
        steps = p.read("refine/steps.json", StepList)
        for s in steps.steps:
            s.substeps = [SubStep(start=s.start, end=s.end, caption="Look closely", focus="B1")]
        p.write("refine/steps.json", steps)
        # A plausible right hand, wrist at (0.45, 0.75), filling about a third of the frame height.
        p.write_jsonl("hands/frames.jsonl", [HandFrame(frame=k, t=k / FPS, hands=[open_hand(0.45, 0.75, size=0.08)])
                                             for k in range(int(3.0 * FPS))])
        config = Config.load(overrides={"render": {**FAST, "include_cards": False, "step_clips": False, "caption": False,
                                                   "progress_bar": False, "callouts": False},
                                        "focus": {"enabled": enabled}})
        render_run(StageContext(project=p, config=config, llm=None, log=logging.getLogger("test")))
        t = p.read("render/tutorial.json", Tutorial)
        frames_ = decode(p.path("render/tutorial.mp4"))
        xs, ys = hand_pixels(frames_[int(0.5 * FPS)])
        assert len(xs) > 20
        sizes[enabled] = (xs.max() - xs.min(), ys.max() - ys.min())
        # Hand skeleton always fully inside the output frame (never cropped out).
        assert xs.min() > 0 and xs.max() < W - 1 and ys.min() > 0 and ys.max() < H - 1
        if enabled:
            plan_ = t.steps[0].crop_plan
            assert plan_ and not is_full(plan_[0].rect) and plan_[0].focus == "B1"
            zoom = 1 / (plan_[0].rect[2] - plan_[0].rect[0])
            assert 1.15 <= zoom <= 2.0
        else:
            assert all(not ts.crop_plan for ts in t.steps)
    assert sizes[True][0] > 1.2 * sizes[False][0] and sizes[True][1] > 1.2 * sizes[False][1]


def test_render_structured_layout_in_tutorial_json():
    from test_render import make_project, render

    from tutorialgen.schemas import StepList

    p = make_project(audio=False)
    steps = p.read("refine/steps.json", StepList)
    s1, s2 = steps.steps
    s1.substeps = [SubStep(start=0.0, end=0.8, caption="Turn on the tap", focus="full"),
                   SubStep(start=0.8, end=1.5, caption="Wet both hands with water", focus="B1", emphasis="wrists", emphasis_t=0.9)]
    p.write("refine/steps.json", steps)
    t: Tutorial = render(p)
    c1 = {c.kind: c for c in t.steps[0].callouts}
    assert c1["items"].text == "Uses: Sink · Water" and c1["items"].start == 0.0
    # Starts at its time, but never so late that it would flash: a short phase pulls it back to stay readable.
    assert c1["emphasis"].text == "wrists" and c1["emphasis"].substep == 1 and 0.8 <= c1["emphasis"].start <= 0.9
    assert c1["emphasis"].end == 1.5
    # The compliance note mentions water: linked to the "Wet both hands" phase, by id, verbatim.
    assert c1["safety"].note_id == "n1" and c1["safety"].substep == 1 and c1["safety"].text.startswith("Use clean running water")
    assert (c1["safety"].start, c1["safety"].end) == (0.8, 1.5)
    assert [c.kind for c in t.steps[1].callouts] == []  # s2 has no tools, no sub-steps, no notes
