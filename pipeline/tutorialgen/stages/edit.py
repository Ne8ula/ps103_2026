"""Stage 'edit': decide what each step's clip keeps, speeds up or cuts -> edit/edl.json.

See tutorialgen/edit/__init__.py for the protocol. Render plays the kept and sped-up units in order;
with the stage disabled every unit is kept and the tutorial shows each step's full range.
"""

from __future__ import annotations

import json

from ..edit import EditConfig, apply_rules, build_units, pixel_motion, step_output_seconds, subtitle_lines
from ..edit.llm import TASK, EditLabelsOutput
from ..llm import LLMRequest
from ..prompts import load_prompt
from ..schemas import EditDecisionList, EditUnit, HandFrame, StepEdit, StepList, Transcript, VideoMeta
from . import StageContext

VERSION = "edit/1.0"
MOTION = "edit/motion.json"


def _motion(ctx: StageContext, meta: VideoMeta, cfg: EditConfig):
    """Pixel motion, cached next to the EDL (it only depends on the video and the sample rate)."""
    import numpy as np

    p = ctx.project
    if p.exists(MOTION):
        cached = json.loads(p.path(MOTION).read_text())
        if cached.get("fps") == cfg.motion_fps and cached.get("video") == meta.video_path:
            return np.array(cached["t"]), np.array(cached["v"])
    t, v = pixel_motion(p.path(meta.video_path), cfg.motion_fps)
    p.write_json(MOTION, {"fps": cfg.motion_fps, "video": meta.video_path, "t": [round(x, 3) for x in t], "v": [round(x, 4) for x in v]})
    return t, v


def _label(ctx: StageContext, steps, units_by_step: dict, cfg: EditConfig) -> tuple[dict[str, tuple[str, str]], list[str]]:
    """LLM labels for spoken lines, in batches; returns {unit id: (label, reason)} and the cache keys."""
    prompt = load_prompt(TASK)
    speech = [(s, u) for s in steps for u in units_by_step[s.id] if u.kind == "speech"]
    labels, calls = {}, []
    for i in range(0, len(speech), cfg.units_per_call):
        batch = speech[i:i + cfg.units_per_call]
        lines, current = [], None
        for s, u in batch:
            if s.id != current:
                lines.append(f"\nStep \"{s.title}\": {s.instruction}")
                current = s.id
            lines.append(f"{u.id} | {u.start:.1f}-{u.end:.1f}s | hands {u.hands:.0%} | motion {u.motion:.2f} | {u.text}")
        request = LLMRequest(task=TASK, system=prompt.system, user=prompt.render(lines="\n".join(lines).strip()),
                             schema=EditLabelsOutput, prompt_version=prompt.version,
                             context={"units": [{"id": u.id, "hands": u.hands, "motion": u.motion, "text": u.text} for _, u in batch]})
        out, key = ctx.llm.call(request)
        calls.append(key)
        offered = {u.id for _, u in batch}
        for item in out.labels:
            if item.unit_id in offered and item.unit_id not in labels:  # ignore invented or repeated ids
                labels[item.unit_id] = (item.label, item.reason.strip()[:120])
    missing = len(speech) - len(labels)
    if missing:
        ctx.log.info("edit: %d spoken lines left unlabelled by the LLM are kept", missing)
    return labels, calls


def run(ctx: StageContext) -> None:
    p = ctx.project
    cfg = ctx.config.section("edit", EditConfig)
    meta = p.read("ingest/meta.json", VideoMeta)
    steps = sorted(p.read("refine/steps.json", StepList).steps, key=lambda s: (s.index, s.start))
    tr = p.read("transcript/transcript.json", Transcript) if p.exists("transcript/transcript.json") else None
    hand_frames = p.read_jsonl("hands/frames.jsonl", HandFrame) if p.exists("hands/frames.jsonl") else []

    if not cfg.enabled:
        step_edits = [StepEdit(step_id=s.id, source_s=s.end - s.start, output_s=s.end - s.start, units=[EditUnit(
            id=f"{s.id}-u01", start=s.start, end=s.end, kind="gap", hands=0, motion=0, label="task", label_source="default",
            action="keep", reason="editing disabled")]) for s in steps]
        p.write("edit/edl.json", _edl(step_edits, False, []))
        return

    lines = subtitle_lines(tr, cfg.line_max_s, cfg.line_max_words, cfg.line_gap_s) if tr and tr.available else []
    motion = _motion(ctx, meta, cfg)
    units_by_step = {s.id: build_units(s.id, s.start, s.end, lines, hand_frames, motion, cfg.absorb_gap_s) for s in steps}
    labels, calls = _label(ctx, steps, units_by_step, cfg) if cfg.use_llm and lines else ({}, [])

    step_edits = []
    for s in steps:
        units = apply_rules(s, units_by_step[s.id], labels, cfg)
        step_edits.append(StepEdit(step_id=s.id, source_s=round(s.end - s.start, 3),
                                   output_s=round(step_output_seconds(units), 3), units=units))
    edl = _edl(step_edits, True, calls)
    p.write("edit/edl.json", edl)
    counts = {a: sum(u.action == a for e in step_edits for u in e.units) for a in ("keep", "speed", "cut")}
    ctx.log.info("edit: %.0fs of steps -> %.0fs (%.0f%%); units kept %d, sped up %d, cut %d", edl.source_s, edl.output_s,
                 100 * edl.output_s / max(edl.source_s, 1e-6), counts["keep"], counts["speed"], counts["cut"])


def _edl(step_edits: list[StepEdit], enabled: bool, calls: list[str]) -> EditDecisionList:
    return EditDecisionList(version=VERSION, enabled=enabled, source_s=round(sum(e.source_s for e in step_edits), 3),
                            output_s=round(sum(e.output_s for e in step_edits), 3), steps=step_edits, llm_calls=calls)
