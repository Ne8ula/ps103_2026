"""Stage 'render': the tutorial package.

Reads ingest/meta.json + video, refine/steps.json, and (when present) compliance, questions, hand
landmarks and gesture keyframes. Writes:

    render/tutorial.mp4     intro card, then per step a title card and the clip with hand overlay +
                            caption, then an outro card with open questions (H.264, yuv420p, faststart)
    render/steps/<id>.mp4   each step clip on its own (overlay + caption, original audio)
    render/tutorial.json    Tutorial: steps with compliance notes, gesture keyframes, clip paths, provenance
    render/tutorial.md      human-readable version

Video frames are decoded once and piped to ffmpeg (the main video and the step clip at the same
time). Audio is assembled sample-exactly in memory from the source track (silence under cards), so
cards and clips never drift.
"""

from __future__ import annotations

import json
import shutil
import tempfile
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import numpy as np
from pydantic import BaseModel

from ..focus import FocusConfig, content_box, load_cuts, load_timeline
from ..focus.crop import CropTrack, apply_crop, is_full, plan, to_crop
from ..project import Project, now_iso
from ..render import cards
from ..render.layout import callouts as build_callouts
from ..render.overlay import HandTrack, PoseHand, draw_hands
from ..render.video import Encoder, FrameReader, audio_slice, output_size, pick_encoder, read_audio, write_wav
from ..schemas.compliance import ComplianceNote, ComplianceReport
from ..schemas.gestures import GestureTrack
from ..schemas.media import HandFrame, VideoMeta
from ..schemas.steps import Question, QuestionSet, Step, StepList
from ..schemas.tutorial import Callout, CropSegment, Tutorial, TutorialStep
from . import StageContext


class RenderConfig(BaseModel):
    include_cards: bool = True           # intro, per-step title cards and outro
    intro_seconds: float = 3.5
    card_min_seconds: float = 3.0        # step card duration scales with its text within [min, max]
    card_max_seconds: float = 6.0
    outro_min_seconds: float = 3.0
    outro_max_seconds: float = 8.0
    overlay: bool = True                 # hand skeletons on clips
    overlay_labels: bool = False         # small L/R tag at the wrist
    hand_tolerance_s: float | None = None  # nearest-sample tolerance; None = 0.6 x sample spacing
    caption: bool = True                 # lower-third step caption on clips
    step_clips: bool = True              # also write render/steps/<id>.mp4
    max_height: int = 720
    crf: int = 20
    preset: str = "fast"                 # libx264 preset
    encoder: Literal["auto", "libx264", "h264_nvenc"] = "auto"  # auto = nvenc when device is cuda and it works
    audio: bool = True
    audio_rate: int = 48000
    # Structured layout (uses step.substeps when present; the focus crop is configured in the 'focus' section).
    substep_captions: bool = True        # caption per sub-step, timed to the clip (else the step caption)
    progress_bar: bool = True            # segmented step progress across the top of clips, sub-step ticks
    callouts: bool = True                # tools/materials chip, emphasis chips, safety callouts from compliance notes
    emphasis_seconds: float = 2.5
    items_seconds: float = 3.0
    max_safety_callouts: int = 2


@dataclass
class _Overlay:
    callout: Callout
    image: np.ndarray                 # BGRA
    slot: str                         # "left" | "right"


@dataclass
class _Piece:
    kind: str                 # "card" | "clip"
    frames: int
    image: np.ndarray | None = None   # card
    step: Step | None = None          # clip
    number: int = 0
    src_start: int = 0                # clip: first source frame
    caption: tuple[int, np.ndarray] | None = None
    sub_captions: list[tuple[float, float, int, np.ndarray]] = field(default_factory=list)  # (start, end, y0, band)
    overlays: list[_Overlay] = field(default_factory=list)
    crop: CropTrack | None = None


def _load_optional(project: Project, rel: str, model):
    return project.read(rel, model) if project.exists(rel) else None


def _llm_label(project: Project, steps: StepList) -> str:
    cache = project.path("llm_cache")
    if not cache.is_dir():
        return "unknown"
    used = [k for s in steps.steps for k in s.provenance.llm_calls]
    files = [cache / f"{k}.json" for k in used if (cache / f"{k}.json").exists()] or sorted(cache.glob("*.json"))
    labels: Counter = Counter()
    for f in files:
        try:
            if label := json.loads(f.read_text()).get("provider"):
                labels[label] += 1
        except (OSError, ValueError):
            continue
    return labels.most_common(1)[0][0] if labels else "unknown"


def _open_questions(questions: QuestionSet | None) -> list[Question]:
    return [q for q in questions.questions if q.status == "open"] if questions else []


def _needs_info(step: Step, open_qs: list[Question], have_questions: bool) -> list[str]:
    """Texts of blocking gaps still open for this step (questions, or the step's own flags if no questions yet)."""
    if have_questions:
        return [q.text for q in open_qs if q.blocking and q.step_id == step.id]
    return [m.description for m in step.missing_info if m.blocking]


def run(ctx: StageContext) -> None:
    p, log = ctx.project, ctx.log
    cfg = ctx.config.section("render", RenderConfig)
    meta = p.read("ingest/meta.json", VideoMeta)
    steps = p.read("refine/steps.json", StepList)
    compliance = _load_optional(p, "compliance/compliance.json", ComplianceReport)
    questions = _load_optional(p, "questions/questions.json", QuestionSet)
    gestures = _load_optional(p, "gestures/gestures.json", GestureTrack)
    hand_frames = p.read_jsonl("hands/frames.jsonl", HandFrame) if p.exists("hands/frames.jsonl") else []
    if compliance is None:
        log.warning("no compliance/compliance.json: rendering without compliance notes")
    if questions is None:
        log.warning("no questions/questions.json: open questions taken from steps' blocking missing_info")

    ordered = sorted(steps.steps, key=lambda s: (s.index, s.start))
    total = len(ordered)
    notes_by_step: dict[str, list[ComplianceNote]] = {}
    if compliance:
        for sc in compliance.steps:
            notes_by_step.setdefault(sc.step_id, []).extend(sc.notes)
    open_qs = _open_questions(questions)
    numbers = {s.id: k + 1 for k, s in enumerate(ordered)}
    title = meta.title or p.manifest.name

    # ---- geometry, timing ------------------------------------------------------------------
    video_path = p.path(meta.video_path)
    reader = FrameReader(video_path)
    src_w, src_h = reader.size
    src_w, src_h = (src_w or meta.width), (src_h or meta.height)
    fps = meta.fps or reader.fps or 30.0
    n_src = meta.frame_count or int(round(meta.duration * fps))
    W, H = output_size(src_w, src_h, cfg.max_height)
    focus = ctx.config.section("focus", FocusConfig)
    zoom = focus.enabled and any(s.substeps for s in ordered) and bool(hand_frames)
    # Hands are needed for the overlay and, with the crop on, to keep every hand inside the crop.
    track = HandTrack(hand_frames, tolerance=cfg.hand_tolerance_s) if (cfg.overlay or zoom) and hand_frames else None
    timeline = load_timeline(p, ctx.config, hand_frames) if zoom else None
    cuts = load_cuts(p)
    content = content_box(p.path(meta.video_path)) if zoom and focus.avoid_letterbox else None
    codec = pick_encoder(ctx.config.device, cfg.encoder)
    log.info("render %d steps at %dx%d %.3g fps with %s%s%s", total, W, H, fps, codec,
             f", {len(hand_frames)} hand samples" if track else "", ", focus crop" if zoom else "")

    def secs(n: int) -> int:
        return max(int(round(n * fps)), 1)

    pieces: list[_Piece] = []
    if cfg.include_cards:
        pieces.append(_Piece("card", secs(cfg.intro_seconds), cards.intro_card(
            W, H, title, total, meta.duration, source=meta.source, license=meta.license, uploader=meta.uploader,
            open_questions=len(open_qs))))
    clip_ranges: dict[str, tuple[int, int]] = {}
    step_callouts: dict[str, list[Callout]] = {}
    crop_plans: dict[str, list[CropSegment]] = {}
    for k, step in enumerate(ordered, 1):
        notes = notes_by_step.get(step.id, [])
        waiting = _needs_info(step, open_qs, questions is not None)
        if cfg.include_cards:
            texts = [step.title, step.instruction, *step.tools, *step.materials, *step.cautions,
                     *[n.text for n in notes[:3]], *waiting[:2]]
            dur = cards.reading_seconds(texts, cfg.card_min_seconds, cfg.card_max_seconds)
            pieces.append(_Piece("card", secs(dur), cards.step_card(W, H, step, k, total, notes, bool(waiting), waiting)))
        f0 = max(int(round(step.start * fps)), 0)
        f1 = min(int(round(step.end * fps)), n_src)
        if f1 <= f0:
            log.warning("step %s has an empty time range [%.2f, %.2f]: no clip", step.id, step.start, step.end)
            continue
        clip_ranges[step.id] = (f0, f1)
        piece = _Piece("clip", f1 - f0, step=step, number=k, src_start=f0)
        if cfg.caption and cfg.substep_captions and step.substeps:
            n_sub = len(step.substeps)
            piece.sub_captions = [(s.start, s.end, *cards.substep_caption(W, H, k, total, step.title, s.caption, bool(waiting),
                                                                         (j, n_sub)))
                                  for j, s in enumerate(step.substeps)]
        elif cfg.caption:
            piece.caption = cards.caption_overlay(W, H, k, total, step.title, step.instruction, bool(waiting))
        if cfg.callouts:
            step_callouts[step.id] = build_callouts(step, notes, emphasis_s=cfg.emphasis_seconds, items_s=cfg.items_seconds,
                                                    max_safety=cfg.max_safety_callouts)
            piece.overlays = [_overlay(c, notes, W, H) for c in step_callouts[step.id]]
        if zoom:
            crop_plans[step.id] = plan(step, timeline, cuts, focus, content)
            piece.crop = CropTrack(crop_plans[step.id], focus)
        pieces.append(piece)
    if cfg.include_cards:
        footer = f"tutorialgen  ·  revision {steps.revision}  ·  {meta.source}"
        outro_texts = [q.text for q in open_qs[:6]] + [n.text for n in (compliance.global_notes[:3] if compliance else [])]
        dur = cards.reading_seconds(outro_texts, cfg.outro_min_seconds, cfg.outro_max_seconds,
                                    base=2.0)
        global_notes = compliance.global_notes if compliance else []
        pieces.append(_Piece("card", secs(dur), cards.outro_card(W, H, open_qs, numbers, footer, notes=global_notes)))
    if not pieces:
        raise RuntimeError("nothing to render: no steps with a valid time range and cards disabled")

    # ---- audio -----------------------------------------------------------------------------
    rate = cfg.audio_rate
    src_audio = None
    if cfg.audio and meta.has_audio:
        src_audio = read_audio(video_path, rate)
        if src_audio is None and meta.audio_path and p.exists(meta.audio_path):
            src_audio = read_audio(p.path(meta.audio_path), rate)
        if src_audio is None:
            log.warning("meta.has_audio is true but no audio could be decoded: rendering silent")

    out_dir = p.stage_dir("render")
    steps_dir = out_dir / "steps"
    shutil.rmtree(steps_dir, ignore_errors=True)
    if cfg.step_clips and clip_ranges:
        steps_dir.mkdir(parents=True)

    def samples_at(frame: int) -> int:
        return int(round(frame / fps * rate))

    tmp = Path(tempfile.mkdtemp(prefix=".tmp-", dir=out_dir))
    final = out_dir / "tutorial.mp4"
    clip_paths: dict[str, str] = {}
    try:
        main_wav = None
        if src_audio is not None:
            chunks, cum = [], 0
            for piece in pieces:
                n = samples_at(cum + piece.frames) - samples_at(cum)
                chunks.append(audio_slice(src_audio, samples_at(piece.src_start), n) if piece.kind == "clip"
                              else np.zeros(n, np.int16))
                cum += piece.frames
            main_wav = write_wav(tmp / "tutorial.wav", np.concatenate(chunks), rate)
            del chunks

        enc_args = dict(codec=codec, crf=cfg.crf, preset=cfg.preset)
        with Encoder(tmp / "tutorial.mp4", W, H, fps, main_wav, **enc_args) as main:
            for piece in pieces:
                if piece.kind == "card":
                    main.write_repeat(piece.image, piece.frames)
                    continue
                step = piece.step
                clip_enc = None
                if cfg.step_clips:
                    clip_wav = None
                    if src_audio is not None:
                        clip_wav = write_wav(tmp / f"{step.id}.wav", audio_slice(
                            src_audio, samples_at(piece.src_start), samples_at(piece.frames)), rate)
                    clip_enc = Encoder(tmp / f"{step.id}.mp4", W, H, fps, clip_wav, **enc_args)
                rects = _crop_rects(piece, track, fps, focus.contain_ramp_s)
                try:
                    for i in range(piece.frames):
                        src_index = piece.src_start + i
                        frame = _clip_frame(reader.read(src_index), src_index / fps, piece, track, cfg, total, W, H,
                                            rects[i] if rects else None)
                        main.write(frame)
                        if clip_enc is not None:
                            clip_enc.write(frame)
                except BaseException:
                    if clip_enc is not None:
                        clip_enc.abort()
                    raise
                if clip_enc is not None:
                    clip_enc.close()
                    dest = steps_dir / f"{step.id}.mp4"
                    (tmp / f"{step.id}.mp4").replace(dest)
                    clip_paths[step.id] = p.rel(dest)
        (tmp / "tutorial.mp4").replace(final)
    finally:
        reader.close()
        shutil.rmtree(tmp, ignore_errors=True)

    # ---- tutorial.json / .md ---------------------------------------------------------------
    keyframes = gestures.keyframes if gestures else []
    t_steps = [
        TutorialStep(
            step=s,
            compliance=notes_by_step.get(s.id, []),
            gesture_keyframe_ids=[g.id for g in keyframes if s.start <= g.t < s.end or (g.t == s.end == ordered[-1].end)],
            clip_path=clip_paths.get(s.id),
            callouts=step_callouts.get(s.id, []),
            crop_plan=crop_plans.get(s.id, []),
        )
        for s in ordered
    ]
    artifacts = {"video": meta.video_path, "tutorial_video": p.rel(final),
                 "tutorial_json": "render/tutorial.json", "tutorial_md": "render/tutorial.md"}
    for name, rel in [("landmarks", "hands/frames.jsonl"), ("hands_summary", "hands/summary.json"),
                      ("scenes", "hands/scenes.json"), ("gestures", "gestures/gestures.json"),
                      ("transcript", "transcript/transcript.json"), ("steps", "refine/steps.json"),
                      ("compliance", "compliance/compliance.json"), ("questions", "questions/questions.json")]:
        if p.exists(rel):
            artifacts[name] = rel
    if meta.audio_path and p.exists(meta.audio_path):
        artifacts["audio"] = meta.audio_path
    for sid, rel in clip_paths.items():
        artifacts[f"clip:{sid}"] = rel

    tutorial = Tutorial(
        project_id=p.id, title=title, source=meta.source, revision=steps.revision, generated_at=now_iso(),
        llm=_llm_label(p, steps), steps=t_steps, global_notes=compliance.global_notes if compliance else [],
        open_questions=open_qs, procedure_notes=list(getattr(steps, "notes", [])), artifacts=artifacts,
    )
    p.write("render/tutorial.json", tutorial)
    (out_dir / "tutorial.md").write_text(to_markdown(tutorial, meta, questions is not None))
    log.info("wrote %s (%d steps, %d clips)", p.rel(final), total, len(clip_paths))


KIND_HEADERS = {"conflict": "SOP conflict", "requirement": "Requirement", "caution": "Caution"}


def _overlay(c: Callout, notes: list[ComplianceNote], W: int, H: int) -> _Overlay:
    if c.kind == "safety":
        note = next((n for n in notes if n.id == c.note_id), None)
        header = KIND_HEADERS.get(note.kind, note.kind) if note else "Safety"
        if note and note.citations:
            header += "  ·  " + cards.short_citation(note.citations[0])
        return _Overlay(c, cards.callout_card(H, header, c.text, c.severity, max_width=W * 0.42), "right")
    return _Overlay(c, cards.chip(H, c.text, c.kind, max_width=W * 0.5), "left")


def _crop_rects(piece: _Piece, track: HandTrack | None, fps: float, ramp_s: float) -> list[list[float]] | None:
    """Per-frame crop rects of a clip (containment eased over ``ramp_s``), or None without a crop."""
    if piece.crop is None:
        return None
    times = [(piece.src_start + i) / fps for i in range(piece.frames)]
    points = []
    for t in times:
        hands = track.hands_at(t) if track is not None else []
        points.append(np.vstack([h.landmarks[:, :2] for h in hands]) if hands else None)
    return piece.crop.rects(times, points, int(round(ramp_s * fps)))


def _clip_frame(src: np.ndarray | None, t: float, piece: _Piece, track: HandTrack | None, cfg: RenderConfig, total: int,
                W: int, H: int, rect: list[float] | None = None) -> np.ndarray:
    """One output frame of a step clip: focus crop, hand overlay, progress bar, callouts, caption."""
    hands = track.hands_at(t) if track is not None else []
    rect = rect or [0.0, 0.0, 1.0, 1.0]
    if src is None:
        frame = np.zeros((H, W, 3), np.uint8)
        rect = [0.0, 0.0, 1.0, 1.0]
    else:
        frame = apply_crop(src, rect, W, H)
        if frame is src:
            frame = frame.copy()
    if cfg.overlay and hands:
        if not is_full(rect):
            hands = [PoseHand(h.handedness, to_crop(h.landmarks, rect), h.score) for h in hands]
        draw_hands(frame, hands, label=cfg.overlay_labels)
    step = piece.step
    u = H / 720.0
    top = 0
    if cfg.progress_bar and step is not None:
        dur = max(step.end - step.start, 1e-6)
        ticks = [(s.start - step.start) / dur for s in step.substeps[1:]]
        cards.draw_progress(frame, piece.number, total, (t - step.start) / dur, ticks)
        top = int(round(10 * u))
    y_left, y_right = top + int(14 * u), top + int(14 * u)
    margin = int(max(W * 0.04, 20 * u))
    for ov in piece.overlays:
        if not (ov.callout.start <= t < ov.callout.end):
            continue
        oh, ow = ov.image.shape[:2]
        if ov.slot == "left":
            cards.blend_at(frame, margin, y_left, ov.image)
            y_left += oh + int(8 * u)
        else:
            cards.blend_at(frame, W - margin - ow, y_right, ov.image)
            y_right += oh + int(8 * u)
    if piece.sub_captions:
        band = next((b for b in piece.sub_captions if b[0] <= t < b[1]), piece.sub_captions[-1])
        cards.blend_band(frame, band[2], band[3])
    elif piece.caption is not None:
        cards.blend_band(frame, *piece.caption)
    return frame


def _resize(frame: np.ndarray, w: int, h: int) -> np.ndarray:
    import cv2

    return cv2.resize(frame, (w, h), interpolation=cv2.INTER_AREA)


def _note_md(n: ComplianceNote) -> str:
    cites = "; ".join(f"{cards.short_citation(c)} — “{c.quote.strip()}”" if c.quote.strip() else cards.short_citation(c)
                      for c in n.citations)
    tag = n.kind.replace("_", " ") + (f", {n.severity}" if n.severity != "info" else "")
    return f"- **[{tag}]** {n.text}  \n  _Source: {cites}_ (`{', '.join(c.chunk_id for c in n.citations)}`)"


def to_markdown(t: Tutorial, meta: VideoMeta, have_questions: bool = True) -> str:
    out = [f"# {t.title}", ""]
    src = f"Source: {t.source}"
    if meta.uploader:
        src += f" · by {meta.uploader}"
    if meta.license:
        src += f" · license: {meta.license}"
    out += [src + "  ", f"Revision {t.revision} · generated {t.generated_at} · text by `{t.llm}`", ""]
    if t.artifacts.get("tutorial_video"):
        out += [f"Video: [`{t.artifacts['tutorial_video']}`](tutorial.mp4)", ""]
    blocking = {q.step_id for q in t.open_questions if q.blocking}
    for k, ts in enumerate(t.steps, 1):
        s = ts.step
        flag = " ⚠ needs info from uploader" if s.id in blocking or (
            not have_questions and any(m.blocking for m in s.missing_info)) else ""
        out += [f"## Step {k}. {s.title}{flag}", "",
                f"`{cards.fmt_time(s.start)}–{cards.fmt_time(s.end)}` · `{s.id}` · confidence {s.confidence:.2f}", "",
                s.instruction, ""]
        for d in s.details:
            out.append(f"- {d}")
        if s.details:
            out.append("")
        if len(s.substeps) > 1 or any(x.emphasis for x in s.substeps):
            labels = {b.id: b.label for b in s.focus_boxes}
            out.append("**Phases:**")
            for x in s.substeps:
                where = labels.get(x.focus, "full frame" if x.focus == "full" else x.focus)
                out.append(f"- `{cards.fmt_time(x.start)}` {x.caption} _(focus: {where})_"
                           + (f" · watch: **{x.emphasis}**" if x.emphasis else ""))
            out.append("")
        if s.tools or s.materials:
            if s.tools:
                out.append(f"**Tools:** {', '.join(s.tools)}  ")
            if s.materials:
                out.append(f"**Materials:** {', '.join(s.materials)}  ")
            out.append("")
        if s.expected_result:
            out += [f"**Expected result:** {s.expected_result}", ""]
        if s.cautions:
            out += ["**Cautions:**", *[f"- {c}" for c in s.cautions], ""]
        if ts.compliance:
            out += ["**Compliance:**", *[_note_md(n) for n in ts.compliance], ""]
        if s.user_supplied:
            out += ["**From the uploader:**", *[f"- {u}" for u in s.user_supplied], ""]
        if ts.clip_path:
            out += [f"Clip: [`{ts.clip_path}`]({Path(ts.clip_path).relative_to('render')})", ""]
    if t.global_notes:
        out += ["## Whole-procedure notes", "", *[_note_md(n) for n in t.global_notes], ""]
    if t.procedure_notes:
        out += ["## From the uploader (whole procedure)", "",
                *[f"- {n.text}" + (f" _({n.question_id})_" if n.question_id else "") for n in t.procedure_notes], ""]
    out += ["## Open questions", ""]
    if t.open_questions:
        step_no = {ts.step.id: k for k, ts in enumerate(t.steps, 1)}
        for q in sorted(t.open_questions, key=lambda q: (not q.blocking, q.priority, q.id)):
            where = f"step {step_no[q.step_id]}" if q.step_id in step_no else "whole procedure"
            out.append(f"- **{q.id}** ({where}, priority {q.priority}{', blocking' if q.blocking else ''}): {q.text}  \n"
                       f"  _Why:_ {q.why}")
    else:
        out.append("None." if have_questions else "Questions have not been generated yet.")
    out.append("")
    return "\n".join(out)
