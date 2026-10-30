"""Motion energy and heuristic step-boundary candidates (stage 'candidates')."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..schemas.gestures import ActivitySample, GestureTrack
from ..schemas.media import HandFrame, Scenes, Transcript
from .config import CandidatesConfig
from .geometry import to_iso
from .keyframes import debounce


@dataclass
class RawCandidate:
    t: float
    reason: str
    strength: float = 1.0


def motion_energy(frames: list[HandFrame], aspect: float, max_gap_s: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(t, energy, hand count) per frame. Energy = sum over hands of mean landmark speed in the image plane (diag/s)."""
    ts = np.array([f.t for f in frames], dtype=float)
    energy = np.zeros(len(frames))
    counts = np.array([len({h.handedness for h in f.hands}) for f in frames], dtype=int)
    prev: dict[str, tuple[float, np.ndarray]] = {}
    for i, f in enumerate(frames):
        cur: dict[str, tuple[float, np.ndarray]] = {}
        for h in sorted(f.hands, key=lambda h: h.score):  # duplicate labels: the higher score wins
            cur[h.handedness] = (f.t, to_iso(h.landmarks, aspect)[:, :2])
        for label, (t, pts) in cur.items():
            if label in prev and 0 < t - prev[label][0] <= max_gap_s:
                energy[i] += float(np.mean(np.linalg.norm(pts - prev[label][1], axis=1))) / (t - prev[label][0])
        prev = {**{k: v for k, v in prev.items() if f.t - v[0] <= max_gap_s}, **cur}
    return ts, energy, counts


def smooth(ts: np.ndarray, values: np.ndarray, window_s: float) -> np.ndarray:
    """Centred moving average over a time window."""
    if len(ts) == 0 or window_s <= 0:
        return values.copy()
    cs = np.concatenate([[0.0], np.cumsum(values)])
    lo = np.searchsorted(ts, ts - window_s / 2, side="left")
    hi = np.searchsorted(ts, ts + window_s / 2, side="right")
    return (cs[hi] - cs[lo]) / np.maximum(hi - lo, 1)


def pause_threshold(energy: np.ndarray, counts: np.ndarray, cfg: CandidatesConfig) -> float:
    active = energy[(counts > 0) & (energy > cfg.pause_abs)]
    return max(cfg.pause_abs, cfg.pause_rel * float(np.median(active))) if len(active) else cfg.pause_abs


def pause_candidates(ts: np.ndarray, energy: np.ndarray, counts: np.ndarray, cfg: CandidatesConfig) -> list[RawCandidate]:
    """Low-energy runs (hands visible) and pronounced local energy minima."""
    out: list[RawCandidate] = []
    thr = pause_threshold(energy, counts, cfg)
    low = (energy < thr) & (counts > 0)
    i = 0
    while i < len(ts):
        if not low[i]:
            i += 1
            continue
        j = i
        while j + 1 < len(ts) and low[j + 1]:
            j += 1
        dur = ts[j] - ts[i]
        if dur >= cfg.min_pause_s:
            out.append(RawCandidate(float((ts[i] + ts[j]) / 2), "motion_pause", min(1.0, dur / cfg.full_pause_s)))
        i = j + 1
    w = cfg.minima_window_s
    for i in range(len(ts)):
        if counts[i] == 0 or low[i]:
            continue
        left = energy[np.searchsorted(ts, ts[i] - w, side="left"):i]
        right = energy[i + 1:np.searchsorted(ts, ts[i] + w, side="right")]
        if len(left) == 0 or len(right) == 0 or energy[i] > min(left.min(), right.min()):
            continue
        if i > 0 and energy[i - 1] == energy[i]:
            continue  # plateau: keep the first sample only
        peak = min(left.max(), right.max())
        if peak > 0 and energy[i] < cfg.minima_ratio * peak:
            out.append(RawCandidate(float(ts[i]), "motion_pause", float(1 - energy[i] / peak)))
    return out


def hand_count_candidates(ts: np.ndarray, counts: np.ndarray, cfg: CandidatesConfig) -> list[RawCandidate]:
    stable = debounce(list(counts), cfg.hand_debounce_frames)
    out = []
    for i in range(1, len(stable)):
        if stable[i] > stable[i - 1]:
            out.append(RawCandidate(float(ts[i]), "hands_enter"))
        elif stable[i] < stable[i - 1]:
            out.append(RawCandidate(float(ts[i]), "hands_exit"))
    return out


def state_change_candidates(track: GestureTrack | None, cfg: CandidatesConfig) -> list[RawCandidate]:
    if track is None:
        return []
    wanted = set(cfg.state_reasons)
    return [RawCandidate(k.t, "hand_state_change") for k in track.keyframes if wanted & set(k.reasons)]


def scene_candidates(scenes: Scenes | None) -> list[RawCandidate]:
    return [RawCandidate(c.t, "scene_cut") for c in scenes.cuts] if scenes else []


def narration_candidates(transcript: Transcript | None, cfg: CandidatesConfig) -> list[RawCandidate]:
    if transcript is None or not transcript.available:
        return []
    segs = sorted(transcript.segments, key=lambda s: s.start)
    out = []
    for a, b in zip(segs, segs[1:]):
        gap = b.start - a.end
        if gap >= cfg.min_narration_gap_s:
            out.append(RawCandidate((a.end + b.start) / 2, "narration_pause", min(1.0, gap / cfg.full_narration_gap_s)))
    return out


def even_candidates(duration: float, cfg: CandidatesConfig) -> list[RawCandidate]:
    n = int(duration // cfg.fallback_spacing_s)
    return [RawCandidate(k * cfg.fallback_spacing_s, "even_spacing") for k in range(1, n + 1)
            if k * cfg.fallback_spacing_s < duration]


def merge_candidates(raws: list[RawCandidate], cfg: CandidatesConfig) -> list[tuple[float, float, list[str]]]:
    """Cluster candidates within merge_window_s of the cluster's first member; score = sum of weight x strongest
    strength per reason, clipped to 1. A scene cut pins the cluster time; otherwise the strongest member does."""
    raws = sorted(raws, key=lambda r: r.t)
    clusters: list[list[RawCandidate]] = []
    for r in raws:
        if clusters and r.t - clusters[-1][0].t <= cfg.merge_window_s:
            clusters[-1].append(r)
        else:
            clusters.append([r])
    out = []
    for cl in clusters:
        best: dict[str, float] = {}
        for r in cl:
            best[r.reason] = max(best.get(r.reason, 0.0), r.strength)
        score = min(1.0, sum(cfg.weights.get(k, 0.0) * v for k, v in best.items()))
        cuts = [r for r in cl if r.reason == "scene_cut"]
        anchor = cuts[0] if cuts else max(cl, key=lambda r: cfg.weights.get(r.reason, 0.0) * r.strength)
        out.append((anchor.t, round(score, 4), sorted(best)))
    return out


def activity_samples(ts: np.ndarray, energy: np.ndarray, counts: np.ndarray, cfg: CandidatesConfig) -> list[ActivitySample]:
    if len(ts) == 0:
        return []
    out = []
    step = 1.0 / cfg.activity_fps
    t = float(ts[0])
    while t <= ts[-1] + 1e-9:
        i = int(np.argmin(np.abs(ts - t)))
        out.append(ActivitySample(t=round(float(ts[i]), 3), motion_energy=round(float(energy[i]), 5),
                                  hands_visible=int(counts[i])))
        t += step
    return out
