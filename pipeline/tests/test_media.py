"""M1: ingest, perception helpers, scene cuts, transcript. Fast tests use synthetic media; slow ones use samples."""

from __future__ import annotations

import wave

import cv2
import numpy as np
import pytest

from tutorialgen import runner
from tutorialgen.media import hands as H
from tutorialgen.media import video
from tutorialgen.media.scenes import SceneCutDetector
from tutorialgen.project import Project
from tutorialgen.schemas.media import HandFrame, HandsSummary, Scenes, Transcript, VideoMeta
from tutorialgen.stages import perception


def make_video(path, n=24, fps=12, size=(160, 120), cut_at: int | None = None):
    """MJPG avi: a white square moving over a blue background that turns red at ``cut_at``."""
    w, h = size
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), fps, (w, h))
    for i in range(n):
        bgr = (40, 20, 200) if cut_at is not None and i >= cut_at else (200, 60, 20)
        img = np.full((h, w, 3), bgr, np.uint8)
        x = 10 + 3 * i % (w - 30)
        img[40:60, x:x + 20] = 255
        writer.write(img)
    writer.release()
    return path


def project_with_video(path) -> Project:
    p = Project.create("synthetic")
    p.set_video(str(path))
    return p


# ---- ingest ------------------------------------------------------------------------------------


def test_ingest_cv2_video_without_audio(tmp_path):
    p = project_with_video(make_video(tmp_path / "clip.avi"))
    assert runner.run(p, stages=["ingest"]) == {"ingest": "ran"}
    meta = p.read("ingest/meta.json", VideoMeta)
    assert (meta.fps, meta.frame_count, meta.width, meta.height) == (12.0, 24, 160, 120)
    assert meta.duration == pytest.approx(2.0)
    assert meta.has_audio is False and meta.audio_path is None
    assert meta.source_kind == "file" and meta.video_path == "ingest/video.mp4"
    import av

    with av.open(str(p.path(meta.video_path))) as c:
        s = c.streams.video[0]
        assert s.codec_context.name == "h264" and s.codec_context.pix_fmt == "yuv420p"


def test_ingest_caps_fps_and_height_and_extracts_audio(tmp_path):
    src = tmp_path / "lavfi.mkv"
    video.run_ffmpeg(["-f", "lavfi", "-i", "testsrc=size=320x240:rate=50:duration=1",
                      "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=44100:duration=1",
                      "-c:v", "mjpeg", "-c:a", "pcm_s16le", "-shortest", str(src)])
    p = project_with_video(src)
    (p.root / "config.yaml").write_text("ingest:\n  max_fps: 25\n  max_height: 120\n")
    runner.run(p, stages=["ingest"])
    meta = p.read("ingest/meta.json", VideoMeta)
    assert (meta.fps, meta.width, meta.height) == (25.0, 160, 120)
    assert meta.frame_count == 25 and meta.duration == pytest.approx(1.0)
    assert meta.has_audio and meta.audio_path == "ingest/audio.wav"
    with wave.open(str(p.path(meta.audio_path))) as w:
        assert (w.getframerate(), w.getnchannels(), w.getsampwidth()) == (16000, 1, 2)
        assert w.getnframes() == pytest.approx(16000, rel=0.05)


def test_ingest_rejects_unknown_settings(tmp_path):
    p = project_with_video(make_video(tmp_path / "clip.avi"))
    (p.root / "config.yaml").write_text("ingest:\n  max_hieght: 480\n")
    with pytest.raises(runner.StageFailed):
        runner.run(p, stages=["ingest"])


def test_sample_indices():
    assert video.sample_indices(10, 30, 60) == list(range(10))
    assert video.sample_indices(10, 30, 15) == [0, 2, 4, 6, 8]
    idx = video.sample_indices(240, 23.976, 15)
    assert len(idx) == pytest.approx(240 * 15 / 23.976, abs=1) and idx == sorted(set(idx))


# ---- transcript ----------------------------------------------------------------------------------


def test_transcribe_without_audio_is_unavailable(tmp_path):
    p = project_with_video(make_video(tmp_path / "clip.avi"))
    runner.run(p, stages=["transcribe"])
    t = p.read("transcript/transcript.json", Transcript)
    assert t.available is False and t.segments == []


# ---- hands helpers -------------------------------------------------------------------------------


def _hand(label: str, score: float = 0.9, x: float = 0.5) -> H.DetectedHand:
    lm = np.zeros((21, 3))
    lm[:, 0] = x + np.linspace(0, 0.1, 21)
    lm[:, 1] = 0.5 + np.linspace(0, 0.1, 21)
    return H.DetectedHand(label, score, lm, lm * 0.1)


def test_fix_handedness_mirror_and_dedupe():
    hands = H.fix_handedness([_hand("Left"), _hand("Right")], mirror=True)
    assert [h.handedness for h in hands] == ["Right", "Left"]
    hands = H.fix_handedness([_hand("Right", 0.95), _hand("Right", 0.6)], mirror=False)
    assert [h.handedness for h in hands] == ["Right", "Left"]
    hands = H.fix_handedness([_hand("Right", 0.95), _hand("Right", 0.6)], mirror=False, dedupe=False)
    assert [h.handedness for h in hands] == ["Right", "Right"]


def test_one_euro_reduces_jitter_and_tracks_motion():
    rng = np.random.default_rng(0)
    f = H.OneEuroFilter(min_cutoff=1.0, beta=1.0)
    ts = np.arange(0, 3, 1 / 15)
    still = [f(np.array([0.5 + rng.normal(0, 0.01)]), t, scale=0.1)[0] for t in ts]
    assert np.std(still[15:]) < 0.5 * 0.01

    f = H.OneEuroFilter(min_cutoff=1.0, beta=1.0)
    ramp = 0.1 + 0.3 * ts                       # 3 hand-sizes per second
    out = np.array([f(np.array([v]), t, scale=0.1)[0] for v, t in zip(ramp, ts)])
    lag = ramp[-15:] - out[-15:]
    assert np.all(lag >= 0) and lag.max() < 0.03

    slow = H.OneEuroFilter(min_cutoff=1.0, beta=0.0)
    out0 = np.array([slow(np.array([v]), t, scale=0.1)[0] for v, t in zip(ramp, ts)])
    assert (ramp[-1] - out0[-1]) > lag.max()     # beta is what removes lag on fast motion


def test_hand_smoother_tracks_by_label_and_resets_after_gap():
    sm = H.HandSmoother(min_cutoff=0.5, beta=0.0, reset_gap_s=0.5)
    sm([_hand("Right", x=0.2), _hand("Left", x=0.7)], 0.0)
    out = sm([_hand("Right", x=0.3)], 1 / 15)
    assert 0.2 < out[0].landmarks[0, 0] < 0.3          # smoothed toward the previous position
    out = sm([_hand("Left", x=0.2)], 1.0)               # Left unseen for 1 s: fresh track, no smoothing
    assert out[0].landmarks[0, 0] == pytest.approx(0.2)


# ---- scene cuts ----------------------------------------------------------------------------------


def test_scene_cut_detector_on_synthetic_frames():
    rng = np.random.default_rng(1)

    def frame(rgb):
        img = np.full((90, 120, 3), rgb, np.uint8).astype(np.int16)
        return np.clip(img + rng.integers(-8, 9, img.shape), 0, 255).astype(np.uint8)

    det = SceneCutDetector(threshold=0.4, min_gap_s=0.5)
    colors = [(20, 60, 200)] * 10 + [(200, 40, 30)] * 10 + [(30, 200, 40)] * 2 + [(240, 240, 240)] * 10 \
        + [(30, 200, 40)] * 5
    hits = [(i, det.update(frame(c), i / 10)) for i, c in enumerate(colors)]
    cuts = [i for i, s in hits if s is not None]
    assert cuts == [10, 20, 32]  # 22 is suppressed by min_gap_s (0.2 s after the cut at 20)
    assert all(0.4 <= s <= 1.0 for _, s in hits if s is not None)


# ---- perception stage with a fake landmarker -------------------------------------------------


class FakeLandmarker:
    device = "cpu"

    def __init__(self, *a, **k):
        self.calls = 0

    def detect(self, rgb, t):
        self.calls += 1
        return [_hand("Left", 0.8, x=0.3)] if self.calls % 2 else []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        pass


def test_perception_stage_with_fake_landmarker(tmp_path, monkeypatch):
    monkeypatch.setattr(perception.H, "HandLandmarker", FakeLandmarker)
    monkeypatch.setattr(perception.H, "ensure_model", lambda path=None: tmp_path / "fake.task")
    p = project_with_video(make_video(tmp_path / "clip.avi", n=48, fps=24, cut_at=24))
    (p.root / "config.yaml").write_text("perception:\n  sample_fps: 12\n  mirror_handedness: true\n")
    runner.run(p, stages=["perception"])

    frames = p.read_jsonl("hands/frames.jsonl", HandFrame)
    assert [f.frame for f in frames] == list(range(0, 48, 2))
    assert [len(f.hands) for f in frames] == [1, 0] * 12           # empty frames are kept
    assert frames[1].t == pytest.approx(2 / 24, abs=1e-3)
    assert all(h.handedness == "Right" for f in frames for h in f.hands)  # mirrored
    assert len(frames[0].hands[0].landmarks) == 21 and frames[0].hands[0].world_landmarks
    summary = p.read("hands/summary.json", HandsSummary)
    assert (summary.frames_processed, summary.frames_with_hands, summary.sample_fps) == (24, 12, 12.0)
    assert summary.smoothing.startswith("one_euro") and summary.device == "cpu"
    cuts = p.read("hands/scenes.json", Scenes).cuts
    assert [c.frame for c in cuts] == [24] and cuts[0].t == pytest.approx(1.0)


# ---- real media (slow) ---------------------------------------------------------------------------


@pytest.mark.slow
def test_sample_video_end_to_end(sample):
    p = project_with_video(sample("sfdph-wash-hands-en.webm"))
    runner.run(p, stages=["perception", "transcribe"])
    meta = p.read("ingest/meta.json", VideoMeta)
    assert meta.height == 720 and meta.fps == 25.0 and meta.has_audio
    assert meta.duration == pytest.approx(58.3, abs=0.5)

    summary = p.read("hands/summary.json", HandsSummary)
    assert summary.frames_processed == pytest.approx(meta.duration * 15, abs=2)
    assert summary.frames_with_hands / summary.frames_processed > 0.4
    frames = p.read_jsonl("hands/frames.jsonl", HandFrame)
    assert len(frames) == summary.frames_processed
    assert len(p.read("hands/scenes.json", Scenes).cuts) >= 8

    t = p.read("transcript/transcript.json", Transcript)
    assert t.available and t.language == "en"
    assert [s.id for s in t.segments] == list(range(len(t.segments)))
    text = " ".join(s.text for s in t.segments).lower()
    assert "20 seconds" in text and "soap" in text
    assert all(s.words for s in t.segments)


@pytest.mark.slow
def test_hand_landmarker_on_sample_frame(sample, tmp_path):
    """The real model finds the demonstrator's right hand in a known frame (no mirroring needed)."""
    src = sample("sfdph-wash-hands-en.webm")
    info = video.probe(src)
    with H.HandLandmarker(H.ensure_model(), 2) as lm:
        found = []
        for i, t, rgb in video.iter_frames(src, info.fps, 5):
            if 21.5 <= t <= 23.0:
                found += H.fix_handedness(lm.detect(rgb, t), mirror=False)
            if t > 23.0:
                break
    labels = [h.handedness for h in found]
    assert labels and labels.count("Right") > labels.count("Left")
