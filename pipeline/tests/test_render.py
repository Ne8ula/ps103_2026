"""M6: tutorial render (overlay, cards, assembly, tutorial.json) on synthetic projects."""

from __future__ import annotations

import json
import logging
import subprocess

import av
import cv2
import numpy as np
import pytest

from tutorialgen.config import Config
from tutorialgen.project import Project
from tutorialgen.render import cards
from tutorialgen.render.overlay import HAND_COLORS, HandTrack, draw_hands
from tutorialgen.render.video import ffmpeg_exe, output_size
from tutorialgen.schemas import (Citation, ComplianceNote, ComplianceReport, GestureKeyframe, GestureTrack, Hand,
                                 HandFrame, MissingInfo, Question, QuestionSet, Step, StepCompliance, StepList,
                                 Tutorial, VideoMeta)
from tutorialgen.stages import StageContext
from tutorialgen.stages.render import run as render_run

FPS, W, H, SECONDS = 15, 320, 240, 3.0
FAST = {"intro_seconds": 1, "card_min_seconds": 1, "card_max_seconds": 1, "outro_min_seconds": 1,
        "outro_max_seconds": 1, "preset": "ultrafast"}


def hand_pose(cx: float = 0.5, cy: float = 0.4, handedness: str = "Right") -> Hand:
    """A plausible open hand around (cx, cy); landmark 8 (index tip) sits exactly at (cx, cy - 0.2)."""
    pts = [[cx, cy + 0.15, 0.0]]
    for f, dx in enumerate((-0.12, -0.05, 0.0, 0.05, 0.1)):
        for j in range(1, 5):
            pts.append([cx + dx * (0.4 + 0.15 * j), cy + 0.15 - 0.0875 * j, 0.0])
    pts[8] = [cx, cy - 0.2, 0.0]
    return Hand(handedness=handedness, score=0.9, landmarks=pts)


def make_project(audio: bool = True, hands: bool = True, compliance: bool = True, questions: bool = True) -> Project:
    p = Project.create("Synthetic demo")
    raw = p.path("ingest/raw.mp4")
    raw.parent.mkdir(parents=True, exist_ok=True)
    vw = cv2.VideoWriter(str(raw), cv2.VideoWriter_fourcc(*"mp4v"), FPS, (W, H))
    for i in range(int(SECONDS * FPS)):
        frame = np.full((H, W, 3), 70, np.uint8)
        cv2.rectangle(frame, (10 + 3 * i, 180), (40 + 3 * i, 210), (40, 40, 200), -1)
        vw.write(frame)
    vw.release()
    video = p.path("ingest/video.mp4")
    cmd = [ffmpeg_exe(), "-loglevel", "error", "-y", "-i", str(raw)]
    if audio:
        cmd += ["-f", "lavfi", "-i", f"sine=frequency=440:duration={SECONDS}", "-c:a", "aac", "-shortest"]
    subprocess.run(cmd + ["-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", str(video)], check=True)
    raw.unlink()
    p.write("ingest/meta.json", VideoMeta(
        source="https://example.org/demo", source_kind="url", title="Wash your hands properly", uploader="SF DPH",
        license="CC BY 4.0", duration=SECONDS, fps=FPS, width=W, height=H, frame_count=int(SECONDS * FPS),
        has_audio=audio, video_path="ingest/video.mp4"))
    steps = [
        Step(id="s01", index=0, start=0.0, end=1.5, title="Wet your hands", confidence=0.9,
             instruction="Wet your hands with clean, running water and turn off the tap.",
             tools=["Sink"], materials=["Water"], cautions=["Do not use hot water above the posted limit."],
             provenance={"llm_calls": ["draft_step-abc"]}),
        Step(id="s02", index=1, start=1.5, end=3.0, title="Lather with soap", confidence=0.6,
             instruction="Apply soap and lather the backs of your hands, between your fingers and under your nails.",
             missing_info=[MissingInfo(field="duration", description="How long to scrub", blocking=True)]),
    ]
    p.write("refine/steps.json", StepList(revision=1, steps=steps))
    cache = p.path("llm_cache")
    cache.mkdir()
    (cache / "draft_step-abc.json").write_text(json.dumps({"task": "draft_step", "provider": "openai:gpt-5.4-mini"}))
    if compliance:
        cite = Citation(chunk_id="d01:12", doc_name="fda-food-code-2022.pdf", page=61, quote="Clean hands with water.")
        p.write("compliance/compliance.json", ComplianceReport(documents=[], steps=[
            StepCompliance(step_id="s01", no_relevant_guidance=False, notes=[ComplianceNote(
                id="n1", step_id="s01", kind="requirement", severity="warning",
                text="Use clean running water at least 38 °C.", citations=[cite])]),
            StepCompliance(step_id="s02", no_relevant_guidance=True)],
            global_notes=[ComplianceNote(id="n9", step_id=None, kind="missing_step", severity="info",
                                         text="Dry hands with a single-use towel.", citations=[cite])]))
    if questions:
        p.write("questions/questions.json", QuestionSet(round=1, questions=[
            Question(id="q001", step_id="s02", kind="missing_info", text="How many seconds should hands be scrubbed?",
                     why="duration unknown", priority=1, blocking=True),
            Question(id="q002", step_id="s01", kind="other", text="Old?", why="x", priority=3, blocking=False,
                     status="answered")]))
    if hands:
        samples = [HandFrame(frame=k * 3, t=k * 3 / FPS, hands=[hand_pose()]) for k in range(int(SECONDS * FPS / 3))]
        p.write_jsonl("hands/frames.jsonl", samples)
        p.write("gestures/gestures.json", GestureTrack(version="1", config_hash="x", keyframes=[
            GestureKeyframe(id="g0001", frame=3, t=0.2, reasons=["interval"], hands=[], interaction="none",
                            activity="active", text="."),
            GestureKeyframe(id="g0002", frame=30, t=2.0, reasons=["interval"], hands=[], interaction="none",
                            activity="active", text=".")]))
    return p


def render(p: Project, **overrides) -> Tutorial:
    config = Config.load(overrides={"render": {**FAST, **overrides}})
    render_run(StageContext(project=p, config=config, llm=None, log=logging.getLogger("test")))
    return p.read("render/tutorial.json", Tutorial)


def decode(path) -> list[np.ndarray]:
    cap = cv2.VideoCapture(str(path))
    frames = []
    while True:
        ok, f = cap.read()
        if not ok:
            return frames
        frames.append(f)


def has_audio(path) -> bool:
    with av.open(str(path)) as c:
        return any(s.type == "audio" for s in c.streams)


def test_full_render(tmp_path):
    p = make_project()
    t = render(p)
    for rel in ("render/tutorial.mp4", "render/tutorial.md", "render/steps/s01.mp4", "render/steps/s02.mp4"):
        assert p.exists(rel), rel
    assert not [x for x in p.path("render").iterdir() if x.name.startswith(".tmp")]

    # 4 one-second cards + the 3 s of footage (22 + 23 frames).
    frames = decode(p.path("render/tutorial.mp4"))
    assert abs(len(frames) - (4 * FPS + 45)) <= 1
    assert frames[0].shape == (H, W, 3)
    assert has_audio(p.path("render/tutorial.mp4")) and has_audio(p.path("render/steps/s01.mp4"))
    assert abs(len(decode(p.path("render/steps/s02.mp4"))) - 23) <= 1

    # Overlay: the index fingertip of the synthetic hand is drawn in the Right-hand colour.
    clip_frame = frames[2 * FPS + 5]
    x, y = int(0.5 * W), int(0.2 * H)
    patch = clip_frame[y - 1:y + 2, x - 1:x + 2].reshape(-1, 3).astype(int)
    assert np.abs(patch - np.array(HAND_COLORS["Right"])).max(axis=1).min() < 40
    # Cards are uniform brand background in the corner; the footage is grey there.
    assert np.abs(frames[3][2, 2].astype(int) - np.array(cards.BG[::-1])).max() < 12

    assert t.title == "Wash your hands properly" and t.revision == 1 and t.llm == "openai:gpt-5.4-mini"
    s1, s2 = t.steps
    assert [n.id for n in s1.compliance] == ["n1"] and s2.compliance == []
    assert s1.gesture_keyframe_ids == ["g0001"] and s2.gesture_keyframe_ids == ["g0002"]
    assert s1.clip_path == "render/steps/s01.mp4"
    assert [q.id for q in t.open_questions] == ["q001"] and [n.id for n in t.global_notes] == ["n9"]
    assert t.artifacts["landmarks"] == "hands/frames.jsonl" and t.artifacts["clip:s02"] == "render/steps/s02.mp4"
    md = p.path("render/tutorial.md").read_text()
    assert "FDA Food Code 2022 p.61" in md and "q001" in md and "needs info" in md


def test_render_minimal_inputs():
    """No compliance, no questions, no hands, no audio: still renders."""
    p = make_project(audio=False, hands=False, compliance=False, questions=False)
    t = render(p)
    frames = decode(p.path("render/tutorial.mp4"))
    assert abs(len(frames) - (4 * FPS + 45)) <= 1
    assert not has_audio(p.path("render/tutorial.mp4"))
    assert t.open_questions == [] and all(s.compliance == [] and s.gesture_keyframe_ids == [] for s in t.steps)
    assert "landmarks" not in t.artifacts
    assert "needs info" in p.path("render/tutorial.md").read_text()  # falls back to blocking missing_info


def test_render_clips_only_and_rerender_is_deterministic():
    p = make_project(audio=False)
    render(p, include_cards=False, caption=False, step_clips=False)
    first = p.path("render/tutorial.mp4").read_bytes()
    assert abs(len(decode(p.path("render/tutorial.mp4"))) - 45) <= 1
    assert not p.exists("render/steps/s01.mp4")
    render(p, include_cards=False, caption=False, step_clips=False)
    assert p.path("render/tutorial.mp4").read_bytes() == first


def test_hand_track_interpolation_and_tolerance():
    a, b = hand_pose(0.3, 0.5), hand_pose(0.5, 0.5)
    track = HandTrack([HandFrame(frame=0, t=0.0, hands=[a]), HandFrame(frame=6, t=0.2, hands=[b]),
                       HandFrame(frame=60, t=2.0, hands=[b]),
                       HandFrame(frame=66, t=2.2, hands=[hand_pose(0.5, 0.5, "Left")])])
    mid = track.hands_at(0.1)
    assert len(mid) == 1 and np.isclose(mid[0].landmarks[0, 0], 0.4, atol=1e-5)
    assert track.hands_at(1.0) == []                         # far from any sample
    assert len(track.hands_at(2.05)) == 1 and track.hands_at(2.05)[0].handedness == "Right"  # nearest only
    assert [h.handedness for h in track.hands_at(2.15)] == ["Left"]  # handedness differs: no interpolation
    assert track.hands_at(5.0) == [] and HandTrack([]).hands_at(0.0) == []

    frame = np.zeros((400, 400, 3), np.uint8)
    draw_hands(frame, track.hands_at(0.2))
    assert np.abs(frame[120, 200].astype(int) - HAND_COLORS["Right"]).max() < 10  # landmark 8 at (0.5, 0.3)
    assert not frame[390, 10].any()


def test_cards_fit_long_text_and_citations():
    long = " ".join(["Thoroughly scrub every surface of both hands including the wrists"] * 12)
    step = Step(id="s01", index=0, start=3, end=75, title=long, instruction=long, confidence=0.5,
                tools=[f"tool {i}" for i in range(20)], cautions=[long] * 6)
    cite = Citation(chunk_id="d01:1", doc_name="fda-food-code-2022.pdf", page=61, quote="q")
    notes = [ComplianceNote(id=f"n{i}", step_id="s01", kind="caution", severity="critical", text=long,
                            citations=[cite, cite]) for i in range(5)]
    img = cards.step_card(640, 360, step, 3, 7, notes, True, [long])
    assert img.shape == (360, 640, 3) and img.dtype == np.uint8
    assert cards.intro_card(1280, 720, long, 7, 151, "https://x", "CC BY", "me", 2).shape == (720, 1280, 3)
    assert cards.outro_card(1280, 720, [Question(id="q001", step_id="s01", kind="other", text=long, why="", priority=1,
                                                 blocking=True)] * 9, {"s01": 1}).shape == (720, 1280, 3)
    y0, band = cards.caption_overlay(1280, 720, 3, 7, long, long, True)
    assert band.shape[2] == 4 and 0 < y0 < 720
    assert cards.citations_text([cite, cite]) == "FDA Food Code 2022 p.61"
    assert cards.doc_label("d01-cdc-lockout-tagout.pdf") == "CDC Lockout Tagout"
    assert cards.doc_label("WHO Hand Hygiene Guide.pdf") == "WHO Hand Hygiene Guide"
    assert output_size(1920, 1080, 720) == (1280, 720) and output_size(641, 361, 720) == (640, 360)


def test_font_fallback(monkeypatch, tmp_path):
    monkeypatch.setattr(cards, "FONT_DIR", tmp_path)
    cards.font.cache_clear()
    try:
        assert cards.intro_card(320, 240, "T", 1, 3).shape == (240, 320, 3)
    finally:
        cards.font.cache_clear()
