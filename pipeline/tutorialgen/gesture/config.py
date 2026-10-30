"""Settings for the ``gestures`` and ``candidates`` stages. Every threshold lives here.

Units: distances on a hand are in *palm sizes* (mean wrist-to-knuckle distance, see
``geometry.palm_size``), so they do not depend on how large the hand appears. Distances in the image
are fractions of the image diagonal ("diag"), measured in isotropic pixels, so a 16:9 video is not
squashed. Angles are degrees. Times are seconds.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class GestureConfig(BaseModel):
    """``gestures`` config section."""

    # --- visibility / noise filtering ------------------------------------------------------
    min_score: float = Field(0.5, description="hand score below this -> low_confidence")
    out_of_frame_margin: float = Field(0.02, description="landmark counts as outside the image beyond this margin (normalized)")
    max_out_of_frame_frac: float = Field(0.25, description="more landmarks than this outside the image -> low_confidence")
    min_palm_size: float = Field(0.012, description="palm smaller than this (diag) -> low_confidence")
    max_bone_ratio: float = Field(1.0, description="any finger bone longer than this many palm sizes -> implausible")
    max_jitter_rate: float = Field(15.0, description="hand-shape change faster than this (palm sizes/s) between samples -> low_confidence")
    max_jump_speed: float = Field(4.0, description="palm-centre jump faster than this (diag/s) between samples -> low_confidence")
    not_visible_memory_s: float = Field(5.0, description="report a missing hand as not_visible for this long after it was last seen; omit it afterwards")
    fill_gaps: bool = Field(True, description="treat time gaps in frames.jsonl as frames with no hands")

    # --- finger state ----------------------------------------------------------------------
    ext_max_bend: float = Field(60.0, description="finger extended if MCP+PIP+DIP bend below this ...")
    ext_min_ratio: float = Field(0.8, description="... and MCP-to-tip / finger length at least this")
    curl_min_bend: float = Field(150.0, description="finger curled if total bend above this ...")
    curl_max_ratio: float = Field(0.55, description="... or MCP-to-tip / finger length below this")
    thumb_ext_max_bend: float = Field(50.0, description="thumb extended if MCP+IP bend below this ...")
    thumb_out_dist: float = Field(0.5, description="... and thumb tip at least this far (palm sizes) from the index knuckle")
    thumb_curl_bend: float = Field(100.0, description="thumb curled if MCP+IP bend above this ...")
    thumb_in_lateral: float = Field(-0.1, description="... or thumb tip lies this far (palm sizes) across the palm past the index knuckle")
    foreshortened_ratio: float = Field(0.3, description="finger pointing at/away from the camera (image length / 3D length below this): no direction")

    # --- groups and grip -------------------------------------------------------------------
    group_tip_dist: float = Field(0.3, description="non-curled fingertips closer than this (palm sizes) form a group")
    pinch_tip_dist: float = Field(0.25, description="thumb tip to index/middle tip closer than this -> pinch")
    fist_tip_dist: float = Field(0.45, description="mean fingertip to palm-centre distance below this -> fist, above -> power grip")
    grip_min_bend: float = Field(100.0, description="mean finger bend at least this for a power grip")
    palm_facing_threshold: float = Field(0.5, description="|palm normal . camera axis| above this -> camera/away, else side")

    # --- motion ----------------------------------------------------------------------------
    speed_window_s: float = Field(0.3, description="window for palm speed and shape-change rate")
    max_gap_s: float = Field(0.5, description="samples further apart than this are not differenced")
    still_max: float = Field(0.03, description="speed buckets (diag/s): still < still_max <= slow ...")
    slow_max: float = Field(0.12, description="... < slow_max <= moderate ...")
    moderate_max: float = Field(0.40, description="... < moderate_max <= fast")
    min_move: float = Field(0.02, description="net displacement below this (diag) has no direction")
    idle_speed: float = Field(0.03, description="active if any hand moves faster than this (diag/s) ...")
    idle_shape_rate: float = Field(0.8, description="... or changes shape faster than this (palm sizes/s)")
    touch_dist: float = Field(0.2, description="closest landmarks of both hands within this (palm sizes) -> hands_touching")
    close_dist: float = Field(3.0, description="palm centres within this (palm sizes) -> hands_close, else hands_apart")

    # --- keyframes -------------------------------------------------------------------------
    debounce_frames: int = Field(3, description="a new hand state (visibility, grip, fingers, interaction) must persist this many sampled frames")
    motion_debounce_frames: int = Field(6, description="same for the noisier speed bucket and idle/active")
    min_gap_s: float = Field(1.0, description="minimum time between keyframes; later events are postponed")
    max_interval_s: float = Field(4.0, description="emit a keyframe at least this often while a hand is visible")
    default_aspect: float = Field(16 / 9, description="width/height used when ingest/meta.json is missing")


class CandidatesConfig(BaseModel):
    """``candidates`` config section."""

    activity_fps: float = Field(5.0, description="rate of the activity samples written to candidates.json")
    max_gap_s: float = Field(0.5, description="samples further apart than this are not differenced")
    energy_smooth_s: float = Field(0.5, description="moving-average window for motion energy")
    pause_abs: float = Field(0.02, description="energy below max(pause_abs, pause_rel * median active energy) is a pause")
    pause_rel: float = Field(0.3)
    min_pause_s: float = Field(0.4, description="pauses shorter than this are ignored")
    full_pause_s: float = Field(1.0, description="pauses this long get full strength")
    minima_window_s: float = Field(1.5, description="energy minimum must be lowest within +-this window ...")
    minima_ratio: float = Field(0.5, description="... and below this fraction of the peak on both sides")
    hand_debounce_frames: int = Field(3, description="hand count must persist this many samples for enter/exit")
    state_reasons: list[str] = Field(["grip_change", "interaction_change", "activity_change"],
                                     description="gesture keyframe reasons that count as a hand-state change")
    min_narration_gap_s: float = Field(0.6, description="gap between transcript segments counted as a pause")
    full_narration_gap_s: float = Field(2.0, description="gaps this long get full strength")
    merge_window_s: float = Field(1.0, description="candidates closer than this are merged")
    weights: dict[str, float] = Field(default_factory=lambda: {
        "scene_cut": 0.6, "hand_state_change": 0.35, "motion_pause": 0.35, "narration_pause": 0.3,
        "hands_enter": 0.3, "hands_exit": 0.3, "even_spacing": 0.3})
    min_score: float = Field(0.25, description="drop merged candidates scoring below this")
    edge_margin_s: float = Field(0.5, description="no candidates this close to the start or end")
    fallback_spacing_s: float = Field(10.0, description="spacing of even candidates when no hands are ever seen")
