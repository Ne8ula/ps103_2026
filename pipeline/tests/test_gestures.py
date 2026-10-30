"""M2: GestLLM-style gesture text and boundary candidates, on synthetic landmark poses."""

from __future__ import annotations

import json
import logging
import math

import numpy as np
import pytest

from tutorialgen.gesture import CandidatesConfig, GestureConfig, build_keyframes, build_timeline
from tutorialgen.gesture import geometry as g
from tutorialgen.gesture import motion as m
from tutorialgen.gesture.keyframes import debounce
from tutorialgen.gesture.timeline import observe_hand
from tutorialgen.project import Project
from tutorialgen.schemas.gestures import Candidates, GestureTrack
from tutorialgen.schemas.media import Hand, HandFrame, SceneCut, Scenes, Transcript, TranscriptSegment, VideoMeta
from tutorialgen.stages import StageContext
from tutorialgen.stages import candidates as candidates_stage
from tutorialgen.stages import gestures as gestures_stage

CFG = GestureConfig()

# ---- synthetic hands -------------------------------------------------------------------------
# Hand-local frame in palm units: X toward the thumb side, Y along the fingers, Z out of the palm.
# A right hand with palm facing the camera has local X = image right, Y = image up, Z = toward camera.

MCP = {"index": (0.30, 1.0), "middle": (0.10, 1.05), "ring": (-0.10, 1.0), "pinky": (-0.28, 0.9)}
SCALE = {"index": 1.0, "middle": 1.05, "ring": 0.95, "pinky": 0.8}
BONES = (0.45, 0.28, 0.22)
CMC = np.array([0.25, 0.22, 0.05])
TUCKED_THUMB = [(0.40, 0.45, 0.25), (0.28, 0.68, 0.45), (0.05, 0.78, 0.50)]
CURLED = (90, 100, 60)


def _finger(name: str, bends=(0, 0, 0), splay: float = 0.0) -> list[np.ndarray]:
    base = np.array([*MCP[name], 0.0])
    d0 = np.array([math.sin(math.radians(splay)), math.cos(math.radians(splay)), 0.0])
    z = np.array([0.0, 0.0, 1.0])
    pts, phi, p = [base], 0.0, base
    for bone, bend in zip(BONES, bends):
        phi += math.radians(bend)
        p = p + bone * SCALE[name] * (math.cos(phi) * d0 + math.sin(phi) * z)
        pts.append(p)
    return pts


def _thumb_extended(angle: float = 40.0) -> list[np.ndarray]:
    d = np.array([math.sin(math.radians(angle)), math.cos(math.radians(angle)), 0.0])
    return [CMC + d * s for s in (0.4, 0.72, 0.98)]


def make_pose(fingers: dict | None = None, splay: dict | None = None, thumb=None) -> np.ndarray:
    """Local 21 x 3 pose. ``fingers``: name -> (mcp, pip, dip) bend degrees; ``thumb``: 3 points (MCP, IP, tip) or None."""
    fingers, splay = fingers or {}, splay or {}
    pts = [np.zeros(3), CMC] + [np.asarray(x, float) for x in (thumb if thumb is not None else _thumb_extended())]
    for name in ("index", "middle", "ring", "pinky"):
        pts += _finger(name, fingers.get(name, (0, 0, 0)), splay.get(name, 0.0))
    return np.array(pts)


def open_hand():
    return make_pose(splay={"index": 10, "middle": 0, "ring": -10, "pinky": -20})


def flat_hand():
    return make_pose(thumb=TUCKED_THUMB)


def fist():
    return make_pose({n: CURLED for n in MCP}, thumb=TUCKED_THUMB)


def point():
    return make_pose({n: CURLED for n in ("middle", "ring", "pinky")}, thumb=TUCKED_THUMB)


def pinch():
    pose = make_pose({"index": (35, 45, 20), **{n: CURLED for n in ("middle", "ring", "pinky")}})
    tip = pose[8] + np.array([0.04, 0.0, 0.03])
    mcp = CMC + np.array([0.25, 0.22, 0.12])
    ip = (mcp + tip) / 2 + np.array([0.08, 0.0, 0.02])
    pose[2:5] = [mcp, ip, tip]
    return pose


def power_grip():
    return make_pose({n: (60, 70, 50) for n in MCP}, thumb=[(0.45, 0.5, 0.25), (0.45, 0.85, 0.5), (0.25, 1.25, 0.6)])


def relaxed():
    return make_pose({n: (30, 40, 20) for n in MCP}, thumb=[(0.5, 0.45, 0.1), (0.6, 0.7, 0.2), (0.6, 0.9, 0.3)])


def rot_z(deg):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


def rot_y(deg):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


def to_landmarks(local: np.ndarray, *, left: bool = False, rot=None, scale: float = 0.12,
                 centre=(0.5, 0.6), aspect: float = 16 / 9) -> list[list[float]]:
    """Place a local pose in the image and return MediaPipe-style normalized landmarks."""
    p = local.copy()
    if left:
        p[:, 0] *= -1
    if rot is not None:
        p = p @ np.asarray(rot).T
    iso = scale * p
    diag = math.hypot(aspect, 1)
    sx, sy = aspect / diag, 1 / diag
    raw = np.stack([iso[:, 0] / sx + centre[0], -iso[:, 1] / sy + centre[1], -iso[:, 2] / sx], axis=1)
    return raw.round(6).tolist()


def hand(local, label="Right", score=0.95, **kw) -> Hand:
    return Hand(handedness=label, score=score, landmarks=to_landmarks(local, left=label == "Left", **kw))


def obs(local, label="Right", aspect=16 / 9, **kw):
    return observe_hand(hand(local, label, aspect=aspect, **kw), aspect, CFG)


def states(o) -> dict[str, str]:
    return {f.name: f.state for f in o.fingers}


# ---- single-frame features -------------------------------------------------------------------

@pytest.mark.parametrize("pose,grip,expect", [
    (open_hand, "open", {"index": "extended", "middle": "extended", "ring": "extended", "pinky": "extended", "thumb": "extended"}),
    (fist, "fist", {"index": "curled", "middle": "curled", "ring": "curled", "pinky": "curled", "thumb": "curled"}),
    (point, "point", {"index": "extended", "middle": "curled", "ring": "curled", "pinky": "curled", "thumb": "curled"}),
    (pinch, "pinch", {"index": "partial", "middle": "curled"}),
    (power_grip, "power_grip", {"index": "curled", "middle": "curled", "ring": "curled", "pinky": "curled"}),
    (relaxed, "relaxed", {"index": "partial", "middle": "partial", "ring": "partial", "pinky": "partial"}),
])
def test_canonical_poses(pose, grip, expect):
    o = obs(pose())
    assert o.visibility == "visible"
    assert o.grip == grip
    assert {k: states(o)[k] for k in expect} == expect


def test_directions_rotate_with_the_hand():
    words = {0: "up", 45: "up-left", 90: "left", 180: "down", 270: "right", -45: "up-right"}
    for deg, word in words.items():
        o = obs(point(), rot=rot_z(deg))
        index = next(f for f in o.fingers if f.name == "index")
        assert index.direction == word, deg
        assert abs(((index.direction_deg - (90 + deg)) + 180) % 360 - 180) < 2
        assert o.grip == "point"
    # Curled fingers carry no direction.
    assert all(f.direction is None for f in obs(fist()).fingers)


@pytest.mark.parametrize("pose", [open_hand, fist, point, pinch, power_grip, relaxed, flat_hand])
def test_scale_and_aspect_invariance(pose):
    ref = obs(pose(), scale=0.12)
    for scale, aspect, centre in [(0.04, 16 / 9, (0.5, 0.6)), (0.2, 16 / 9, (0.5, 0.85)), (0.12, 1.0, (0.5, 0.6)), (0.12, 9 / 16, (0.5, 0.6))]:
        o = obs(pose(), scale=scale, aspect=aspect, centre=centre)
        assert states(o) == states(ref) and o.grip == ref.grip and o.groups == ref.groups
        assert [f.direction for f in o.fingers] == [f.direction for f in ref.fingers]


def test_groups():
    assert obs(flat_hand()).groups == [["index", "middle", "ring", "pinky"]]
    assert obs(open_hand()).groups == []
    assert obs(pinch()).groups == [["thumb", "index"]]
    together = make_pose({"ring": CURLED, "pinky": CURLED}, thumb=TUCKED_THUMB)  # two-finger "V" closed
    assert obs(together).groups == [["index", "middle"]]


def test_palm_facing_and_handedness():
    assert obs(open_hand()).palm_facing == "camera"
    assert obs(open_hand(), label="Left").palm_facing == "camera"
    assert obs(open_hand(), rot=rot_y(180)).palm_facing == "away"
    assert obs(open_hand(), label="Left", rot=rot_y(180)).palm_facing == "away"
    assert obs(open_hand(), rot=rot_y(90)).palm_facing == "side"
    # Mirroring flips which side the thumb is on, so the labelled handedness matters.
    assert obs(open_hand(), label="Left").fingers[0].direction == "up-left"
    assert obs(open_hand()).fingers[0].direction == "up-right"


def test_low_confidence_and_implausible():
    for o in (obs(fist(), score=0.2), obs(open_hand(), centre=(0.98, 0.5)), obs(open_hand(), scale=0.005)):
        assert o.visibility == "low_confidence" and o.reason
        assert {f.state for f in o.fingers} == {"unknown"} and o.grip == "unknown" and o.palm_facing == "unknown"
        assert o.position is not None
    broken = open_hand()
    broken[8] = broken[8] + np.array([0, 2.0, 0])  # index tip two palms away
    assert obs(broken).reason == "implausible_shape"


# ---- timelines and keyframes -----------------------------------------------------------------

def frames_from(spec, fps=10.0) -> list[HandFrame]:
    """spec: list of lists of Hand (one per sampled frame)."""
    return [HandFrame(frame=i * 3, t=round(i / fps, 4), hands=hs) for i, hs in enumerate(spec)]


def moving(pose, n, start=(0.3, 0.6), velocity=(0.0, 0.0), fps=10.0, label="Right", **kw):
    """n frames of one hand moving at velocity (normalized units per second)."""
    return [[hand(pose(), label, centre=(start[0] + velocity[0] * i / fps, start[1] + velocity[1] * i / fps), **kw)]
            for i in range(n)]


def test_speed_buckets_and_trajectory():
    cfg = GestureConfig(max_interval_s=1.0)
    diag = math.hypot(16 / 9, 1)
    for v_diag, bucket in [(0.0, "still"), (0.07, "slow"), (0.2, "moderate"), (0.8, "fast")]:
        vx = v_diag * diag / (16 / 9)  # normalized-x per second giving v_diag diag/s
        tl = build_timeline(frames_from(moving(open_hand, 25, start=(0.1, 0.6), velocity=(vx, 0))), 16 / 9, cfg)
        kfs = build_keyframes(tl, cfg)
        tr = kfs[-1].hands[0].trajectory
        assert tr.speed == bucket, (v_diag, tr)
        if bucket == "still":
            assert tr.direction is None and "holding position" in kfs[-1].text
        else:
            assert tr.direction == "right"
            assert tr.distance == pytest.approx(v_diag * (kfs[-1].t - tr.since_t), rel=0.05)
    # Moving down-left in the image (y grows downward).
    tl = build_timeline(frames_from(moving(open_hand, 15, start=(0.6, 0.3), velocity=(-0.1, 0.1))), 16 / 9, cfg)
    assert build_keyframes(tl, cfg)[-1].hands[0].trajectory.direction == "down-left"


def test_debounce():
    assert debounce(list("aaabaaa"), 3) == list("aaaaaaa")
    assert debounce(list("aaabbbcc"), 3) == list("aaabbbbb")
    assert debounce(list("abbbb"), 3) == list("bbbbb")  # short start-up run takes the first stable value
    assert debounce(list("ab"), 3) == list("aa")


def test_keyframe_debounce_ignores_flicker_and_marks_onset():
    cfg = GestureConfig(max_interval_s=100)
    spec = moving(open_hand, 10) + moving(fist, 2) + moving(open_hand, 10) + moving(fist, 10)
    tl = build_timeline(frames_from(spec), 16 / 9, cfg)
    kfs = build_keyframes(tl, cfg)
    grip_kfs = [k for k in kfs if "grip_change" in k.reasons]
    assert len(grip_kfs) == 1 and grip_kfs[0].t == pytest.approx(2.2)  # onset of the persistent fist
    assert kfs[0].reasons == ["start"] and kfs[0].id == "g0001"
    assert grip_kfs[0].hands[0].grip == "fist" and "fist" in grip_kfs[0].text


def test_max_interval_and_min_gap():
    cfg = GestureConfig(max_interval_s=4.0)
    tl = build_timeline(frames_from(moving(open_hand, 101)), 16 / 9, cfg)  # 10 s, nothing changes
    kfs = build_keyframes(tl, cfg)
    assert [k.t for k in kfs] == [0.0, 4.0, 8.0]
    assert [k.reasons for k in kfs[1:]] == [["interval"], ["interval"]]
    # Two changes 0.3 s apart: the second is postponed to min_gap after the first, not dropped.
    cfg = GestureConfig(max_interval_s=100, min_gap_s=0.5, debounce_frames=2)
    spec = moving(open_hand, 10) + moving(fist, 3) + moving(point, 10)
    kfs = build_keyframes(build_timeline(frames_from(spec), 16 / 9, cfg), cfg)
    assert [(k.t, "grip_change" in k.reasons) for k in kfs] == [(0.0, False), (1.0, True), (1.5, True)]
    assert kfs[-1].hands[0].grip == "point"


def test_not_visible_handling():
    cfg = GestureConfig(max_interval_s=2.0, not_visible_memory_s=3.0)
    spec = moving(open_hand, 20) + [[] for _ in range(60)] + moving(open_hand, 10)
    kfs = build_keyframes(build_timeline(frames_from(spec), 16 / 9, cfg), cfg)
    gone = [k for k in kfs if k.hands and k.hands[0].visibility == "not_visible"]
    assert gone and gone[0].t == pytest.approx(2.0) and "Right hand: not visible." in gone[0].text
    assert "visibility_change" in gone[0].reasons
    assert all(k.t < 2.0 or k.t >= 8.0 for k in kfs if k is not gone[0])  # no interval keyframes while absent
    back = kfs[-1]
    assert back.t == pytest.approx(8.0) and back.hands[0].visibility == "visible"
    # The never-seen left hand is never mentioned.
    assert all(h.handedness == "Right" for k in kfs for h in k.hands)


def test_gaps_in_frames_file_mean_absence():
    cfg = GestureConfig(max_interval_s=100)
    fr = frames_from(moving(open_hand, 10))
    later = [HandFrame(frame=300 + i * 3, t=10.0 + i / 10, hands=h) for i, h in enumerate(moving(open_hand, 10))]
    kfs = build_keyframes(build_timeline(fr + later, 16 / 9, cfg), cfg)
    assert any(h.visibility == "not_visible" for k in kfs for h in k.hands)


def test_two_hands_interaction_and_text():
    cfg = GestureConfig(min_gap_s=0.5)
    apart = [[hand(power_grip(), "Right", centre=(0.75, 0.6)), hand(open_hand(), "Left", centre=(0.2, 0.6))]] * 5
    close = [[hand(power_grip(), "Right", centre=(0.62, 0.6)), hand(open_hand(), "Left", centre=(0.38, 0.6))]] * 5
    touch = [[hand(pinch(), "Right", centre=(0.52, 0.6)), hand(pinch(), "Left", centre=(0.48, 0.6))]] * 5
    tl = build_timeline(frames_from(apart + close + touch), 16 / 9, cfg)
    assert [tl[i].interaction for i in (0, 5, 10)] == ["hands_apart", "hands_close", "hands_touching"]
    kfs = build_keyframes(tl, cfg)
    assert [k.interaction for k in kfs] == ["hands_apart", "hands_close", "hands_touching"]
    assert all("interaction_change" in k.reasons for k in kfs[1:])
    text = kfs[0].text
    assert text.startswith("t=0.0s | Right hand: power grip, palm facing camera")
    assert "Left hand: open hand, palm facing camera, fingers spread pointing up, thumb out pointing up-left" in text
    assert text.endswith("Hands apart. Idle.")


def test_occluded_hand_text():
    cfg = GestureConfig()
    tl = build_timeline(frames_from(moving(power_grip, 5, score=0.3)), 16 / 9, cfg)
    k = build_keyframes(tl, cfg)[0]
    assert k.hands[0].visibility == "low_confidence" and k.hands[0].visibility_reason == "low_score"
    assert k.text == "t=0.0s | Right hand: unclear (partly hidden or unclear), at left side. Idle."


def test_activity_from_motion_and_shape_change():
    cfg = GestureConfig()
    tl = build_timeline(frames_from(moving(open_hand, 5, velocity=(0.3, 0))), 16 / 9, cfg)
    assert tl[-1].activity == "active"
    tl = build_timeline(frames_from(moving(open_hand, 5)), 16 / 9, cfg)
    assert tl[-1].activity == "idle"
    # Closing the hand in place is activity even without palm motion.
    poses = [make_pose({n: (k * 18, k * 20, k * 12) for n in MCP}) for k in range(6)]
    tl = build_timeline(frames_from([[hand(p)] for p in poses]), 16 / 9, cfg)
    assert tl[-1].activity == "active"


def test_jitter_rejected():
    cfg = GestureConfig()
    spec = moving(open_hand, 3) + [[hand(fist(), centre=(0.3, 0.6))]] + moving(open_hand, 3)
    tl = build_timeline(frames_from(spec, fps=30), 16 / 9, cfg)
    assert tl[3].hands["Right"].reason == "jitter"


# ---- candidates ------------------------------------------------------------------------------

def test_merge_and_score():
    cfg = CandidatesConfig()
    raws = [m.RawCandidate(5.0, "motion_pause", 0.8), m.RawCandidate(5.4, "scene_cut"),
            m.RawCandidate(5.6, "narration_pause", 0.5), m.RawCandidate(12.0, "hands_exit"),
            m.RawCandidate(20.0, "motion_pause", 0.2), m.RawCandidate(20.3, "motion_pause", 0.9)]
    merged = m.merge_candidates(raws, cfg)
    assert [t for t, _, _ in merged] == [5.4, 12.0, 20.3]  # scene cut pins time; else the strongest member
    assert merged[0][1] == pytest.approx(min(1.0, 0.6 + 0.35 * 0.8 + 0.3 * 0.5))
    assert merged[0][2] == ["motion_pause", "narration_pause", "scene_cut"]
    assert merged[1][1] == pytest.approx(0.3)
    assert merged[2][1] == pytest.approx(0.35 * 0.9)


def test_narration_pauses_and_even_spacing():
    cfg = CandidatesConfig()
    tr = Transcript(available=True, segments=[TranscriptSegment(id=0, start=0, end=3, text="a"),
                                              TranscriptSegment(id=1, start=3.2, end=6, text="b"),
                                              TranscriptSegment(id=2, start=8, end=9, text="c")])
    c = m.narration_candidates(tr, cfg)
    assert len(c) == 1 and c[0].t == 7.0 and c[0].strength == 1.0
    assert m.narration_candidates(Transcript(available=False), cfg) == []
    assert [r.t for r in m.even_candidates(35, cfg)] == [10, 20, 30]


def test_pause_detection():
    cfg = CandidatesConfig()
    ts = np.arange(0, 10, 0.1)
    energy = np.where((ts > 4) & (ts < 5.5), 0.0, 0.3)
    counts = np.ones_like(ts, dtype=int)
    pauses = m.pause_candidates(ts, energy, counts, cfg)
    assert any(r.reason == "motion_pause" and 4.5 < r.t < 5.0 and r.strength == 1.0 for r in pauses)
    assert m.pause_candidates(ts, energy, np.zeros_like(counts), cfg) == []


# ---- full stage runs -------------------------------------------------------------------------

def make_ctx(project: Project) -> StageContext:
    return StageContext(project=project, config=project.config(), llm=None, log=logging.getLogger("test"))


def write_project(with_hands=True, with_transcript=True) -> Project:
    p = Project.create("synthetic gestures")
    fps, sample = 30.0, 10.0
    p.write("ingest/meta.json", VideoMeta(source="x.mp4", source_kind="file", duration=20.0, fps=fps, width=1280,
                                          height=720, frame_count=600, has_audio=with_transcript,
                                          video_path="ingest/video.mp4"))
    spec: list[list[Hand]] = []
    if with_hands:
        # 0-4 s reach right with an open hand, 4-6 s still power grip, 6-10 s carry left, 10-13 s gone, 13-20 s pinch.
        spec += moving(open_hand, 40, start=(0.2, 0.6), velocity=(0.08, 0))
        spec += moving(power_grip, 20, start=(0.52, 0.6))
        spec += moving(power_grip, 40, start=(0.52, 0.6), velocity=(-0.06, -0.02))
        spec += [[] for _ in range(30)]
        spec += [[hand(pinch(), centre=(0.5, 0.5)), hand(open_hand(), "Left", centre=(0.4, 0.55))] for _ in range(70)]
    else:
        spec += [[] for _ in range(200)]
    frames = [HandFrame(frame=int(i * fps / sample), t=round(i / sample, 3), hands=h) for i, h in enumerate(spec)]
    p.write_jsonl("hands/frames.jsonl", frames)
    p.write("hands/scenes.json", Scenes(cuts=[SceneCut(t=13.0, frame=390, score=0.9)]))
    p.write("transcript/transcript.json", Transcript(available=with_transcript, segments=[
        TranscriptSegment(id=0, start=0.5, end=4.0, text="Reach for the bottle."),
        TranscriptSegment(id=1, start=5.5, end=9.5, text="Lift it over."),
    ] if with_transcript else []))
    return p


def test_full_stage_run():
    p = write_project()
    ctx = make_ctx(p)
    gestures_stage.run(ctx)
    track = p.read("gestures/gestures.json", GestureTrack)
    assert track.version.startswith("gesture_text/") and len(track.config_hash) == 16
    ids = [k.id for k in track.keyframes]
    assert ids == [f"g{i:04d}" for i in range(1, len(ids) + 1)]
    assert [k.t for k in track.keyframes] == sorted(k.t for k in track.keyframes)
    grips = [h.grip for k in track.keyframes for h in k.hands if h.visibility == "visible"]
    assert {"open", "power_grip", "pinch"} <= set(grips)
    assert any(h.visibility == "not_visible" for k in track.keyframes for h in k.hands)
    assert (p.root / "gestures" / "gestures.txt").exists()

    candidates_stage.run(ctx)
    cands = p.read("candidates/candidates.json", Candidates)
    ts = [b.t for b in cands.boundaries]
    assert ts == sorted(ts) and all(0 <= b.score <= 1 for b in cands.boundaries)
    assert any(abs(t - 4.0) < 1.0 for t in ts)          # grip change + pause + narration gap
    cut = next(b for b in cands.boundaries if "scene_cut" in b.reasons)
    assert cut.t == 13.0 and cut.frame == 390
    assert any("hands_exit" in b.reasons and abs(b.t - 10.0) < 0.5 for b in cands.boundaries)
    assert len(cands.activity) == pytest.approx(200 / 2, abs=2)  # 5 Hz over 20 s
    assert max(a.hands_visible for a in cands.activity) == 2


def test_candidates_without_hands_or_transcript():
    p = write_project(with_hands=False, with_transcript=False)
    ctx = make_ctx(p)
    gestures_stage.run(ctx)
    assert p.read("gestures/gestures.json", GestureTrack).keyframes == []
    candidates_stage.run(ctx)
    cands = p.read("candidates/candidates.json", Candidates)
    assert [(b.t, b.reasons) for b in cands.boundaries] == [(10.0, ["even_spacing"]), (13.0, ["scene_cut"])]


def test_stage_config_overrides(tmp_path):
    p = write_project()
    (p.root / "config.yaml").write_text("gestures:\n  max_interval_s: 1.0\n")
    gestures_stage.run(make_ctx(p))
    dense = p.read("gestures/gestures.json", GestureTrack)
    (p.root / "config.yaml").write_text("")
    gestures_stage.run(make_ctx(p))
    sparse = p.read("gestures/gestures.json", GestureTrack)
    assert len(dense.keyframes) > len(sparse.keyframes) and dense.config_hash != sparse.config_hash
    json.loads((p.root / "gestures" / "gestures.json").read_text())
