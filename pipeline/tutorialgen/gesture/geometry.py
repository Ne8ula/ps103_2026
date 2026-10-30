"""Pure geometry over one hand: 21 x 3 MediaPipe landmarks -> finger states, directions, groups, grip.

Coordinates: MediaPipe image landmarks are x right, y down, normalized to width/height, z depth
(smaller = closer, roughly x scale). ``to_iso`` converts them to an isotropic right-handed frame in
units of the image diagonal: X right, Y up, Z toward the camera. All angles below use that frame,
so ``direction_deg`` 0 = right, 90 = up.
"""

from __future__ import annotations

import math

import numpy as np

from ..schemas.gestures import FingerState
from .config import GestureConfig

WRIST = 0
FINGERS: dict[str, tuple[int, int, int, int]] = {
    "thumb": (1, 2, 3, 4),
    "index": (5, 6, 7, 8),
    "middle": (9, 10, 11, 12),
    "ring": (13, 14, 15, 16),
    "pinky": (17, 18, 19, 20),
}
FINGER_NAMES = list(FINGERS)
LONG_FINGERS = FINGER_NAMES[1:]
PALM_IDS = (0, 5, 9, 13, 17)
BONES = [(a, b) for chain in FINGERS.values() for a, b in zip(chain, chain[1:])] + [(0, 1)]
DIRECTIONS = ["right", "up-right", "up", "up-left", "left", "down-left", "down", "down-right"]


def to_iso(landmarks, aspect: float) -> np.ndarray:
    """Normalized image landmarks -> isotropic (X right, Y up, Z toward camera), units of image diagonal."""
    a = np.asarray(landmarks, dtype=float).reshape(21, 3)
    diag = math.hypot(aspect, 1.0)
    sx, sy = aspect / diag, 1.0 / diag
    return np.stack([a[:, 0] * sx, -a[:, 1] * sy, -a[:, 2] * sx], axis=1)


def palm_size(p: np.ndarray) -> float:
    """Mean wrist-to-knuckle distance (3D): the unit for every hand-relative threshold."""
    return float(np.mean([np.linalg.norm(p[k] - p[WRIST]) for k in (5, 9, 13, 17)]))


def palm_centre(p: np.ndarray) -> np.ndarray:
    return p[list(PALM_IDS)].mean(axis=0)


def _angle(u: np.ndarray, v: np.ndarray) -> float:
    nu, nv = np.linalg.norm(u), np.linalg.norm(v)
    if nu < 1e-9 or nv < 1e-9:
        return 0.0
    return math.degrees(math.acos(float(np.clip(np.dot(u, v) / (nu * nv), -1.0, 1.0))))


def direction_deg(vec) -> float:
    """Image-plane angle of an iso vector in [0, 360): 0 = right, 90 = up."""
    return math.degrees(math.atan2(float(vec[1]), float(vec[0]))) % 360.0


def direction8(deg: float) -> str:
    return DIRECTIONS[int(((deg % 360.0) + 22.5) // 45.0) % 8]


def finger_bend(p: np.ndarray, name: str) -> float:
    """Sum of joint flexion angles: long fingers MCP+PIP+DIP (0 = straight), thumb MCP+IP."""
    a, b, c, d = FINGERS[name]
    if name == "thumb":
        return _angle(p[b] - p[a], p[c] - p[b]) + _angle(p[c] - p[b], p[d] - p[c])
    return (_angle(p[a] - p[WRIST], p[b] - p[a]) + _angle(p[b] - p[a], p[c] - p[b])
            + _angle(p[c] - p[b], p[d] - p[c]))


def fold_ratio(p: np.ndarray, name: str) -> float:
    """Base-to-tip distance / summed bone length: 1 = straight, small = folded."""
    chain = FINGERS[name]
    length = sum(np.linalg.norm(p[j] - p[i]) for i, j in zip(chain, chain[1:]))
    return float(np.linalg.norm(p[chain[-1]] - p[chain[0]]) / max(length, 1e-9))


def palm_frame(p: np.ndarray, handedness: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(lateral axis toward the thumb side, finger axis, palm normal pointing out of the palm)."""
    u = p[5] - p[17]
    u = u / max(np.linalg.norm(u), 1e-9)
    v = p[9] - p[WRIST]
    v = v - np.dot(v, u) * u
    v = v / max(np.linalg.norm(v), 1e-9)
    n = np.cross(p[5] - p[WRIST], p[17] - p[WRIST])
    if handedness == "Left":
        n = -n
    n = n / max(np.linalg.norm(n), 1e-9)
    return u, v, n


def finger_state(p: np.ndarray, name: str, cfg: GestureConfig, palm: float, handedness: str) -> str:
    bend = finger_bend(p, name)
    if name == "thumb":
        tip = p[4]
        u, _, _ = palm_frame(p, handedness)
        lateral = float(np.dot(tip - p[5], u)) / palm
        out = float(np.linalg.norm(tip - p[5])) / palm
        if bend > cfg.thumb_curl_bend or lateral < cfg.thumb_in_lateral:
            return "curled"
        if bend < cfg.thumb_ext_max_bend and out >= cfg.thumb_out_dist:
            return "extended"
        return "partial"
    ratio = fold_ratio(p, name)
    if bend > cfg.curl_min_bend or ratio < cfg.curl_max_ratio:
        return "curled"
    if bend < cfg.ext_max_bend and ratio >= cfg.ext_min_ratio:
        return "extended"
    return "partial"


def finger_direction(p: np.ndarray, name: str, cfg: GestureConfig) -> float | None:
    """Image-plane angle from the finger base (thumb: MCP) to its tip; None when foreshortened."""
    chain = FINGERS[name]
    base = p[chain[1]] if name == "thumb" else p[chain[0]]
    vec = p[chain[-1]] - base
    full = float(np.linalg.norm(vec))
    if full < 1e-9 or float(np.linalg.norm(vec[:2])) / full < cfg.foreshortened_ratio:
        return None
    return direction_deg(vec)


def describe_fingers(p: np.ndarray, cfg: GestureConfig, handedness: str) -> list[FingerState]:
    palm = palm_size(p)
    out = []
    for name in FINGER_NAMES:
        state = finger_state(p, name, cfg, palm, handedness)
        deg = finger_direction(p, name, cfg) if state != "curled" else None
        out.append(FingerState(name=name, state=state, direction_deg=None if deg is None else round(deg, 1),
                               direction=None if deg is None else direction8(deg)))
    return out


def tip_groups(p: np.ndarray, fingers: list[FingerState], cfg: GestureConfig) -> list[list[str]]:
    """Connected components of non-curled fingers whose tips are within ``group_tip_dist`` palm sizes."""
    palm = palm_size(p)
    names = [f.name for f in fingers if f.state in ("extended", "partial")]
    parent = {n: n for n in names}

    def find(n: str) -> str:
        while parent[n] != n:
            n = parent[n]
        return n

    for i, a in enumerate(names):
        for b in names[i + 1:]:
            if np.linalg.norm(p[FINGERS[a][-1]] - p[FINGERS[b][-1]]) / palm < cfg.group_tip_dist:
                parent[find(b)] = find(a)
    comps: dict[str, list[str]] = {}
    for n in names:
        comps.setdefault(find(n), []).append(n)
    return [sorted(c, key=FINGER_NAMES.index) for c in comps.values() if len(c) >= 2]


def classify_grip(p: np.ndarray, fingers: list[FingerState], cfg: GestureConfig) -> str:
    """open | pinch | power_grip | point | fist | relaxed (rules are checked in this order: pinch first)."""
    palm = palm_size(p)
    st = {f.name: f.state for f in fingers}
    centre = palm_centre(p)
    tip_to_palm = {n: float(np.linalg.norm(p[FINGERS[n][-1]] - centre)) / palm for n in LONG_FINGERS}
    thumb_tip = p[4]
    pinch = min(np.linalg.norm(thumb_tip - p[8]), np.linalg.norm(thumb_tip - p[12])) / palm
    longs = [st[n] for n in LONG_FINGERS]
    n_ext, n_curl = longs.count("extended"), longs.count("curled")
    mean_bend = float(np.mean([finger_bend(p, n) for n in LONG_FINGERS]))
    mean_tip = float(np.mean(list(tip_to_palm.values())))

    if pinch < cfg.pinch_tip_dist and tip_to_palm["index"] >= cfg.fist_tip_dist and st["thumb"] != "curled":
        return "pinch"
    if st["index"] == "extended" and st["middle"] != "extended" and [st["ring"], st["pinky"], st["middle"]].count("curled") >= 2:
        return "point"
    if n_ext == 4 or (n_ext >= 3 and n_curl == 0 and st["thumb"] == "extended"):
        return "open"
    if n_ext == 0 and mean_bend >= cfg.grip_min_bend:
        if n_curl >= 3 and mean_tip < cfg.fist_tip_dist:
            return "fist"
        if mean_tip >= cfg.fist_tip_dist:
            return "power_grip"
    return "relaxed"


def palm_facing(p: np.ndarray, handedness: str, cfg: GestureConfig) -> str:
    """camera | away | side, from the palm normal's component along the camera axis (+Z)."""
    _, _, n = palm_frame(p, handedness)
    if n[2] > cfg.palm_facing_threshold:
        return "camera"
    if n[2] < -cfg.palm_facing_threshold:
        return "away"
    return "side"


def implausibility(raw: np.ndarray, p: np.ndarray, cfg: GestureConfig) -> str | None:
    """Reason a single-frame hand is not trustworthy, or None. ``raw`` is normalized, ``p`` iso."""
    m = cfg.out_of_frame_margin
    outside = np.mean((raw[:, 0] < -m) | (raw[:, 0] > 1 + m) | (raw[:, 1] < -m) | (raw[:, 1] > 1 + m))
    if outside > cfg.max_out_of_frame_frac:
        return "out_of_frame"
    palm = palm_size(p)
    if palm < cfg.min_palm_size:
        return "too_small"
    if any(np.linalg.norm(p[b] - p[a]) / palm > cfg.max_bone_ratio for a, b in BONES):
        return "implausible_shape"
    return None
