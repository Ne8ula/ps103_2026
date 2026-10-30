"""Pillow-rendered text cards (intro, per-step, outro) and the lower-third caption for clips.

Everything is laid out in units of the frame height (designed at 720 p) so any resolution looks the
same. Long content shrinks to fit, then truncates with an ellipsis. Brand fonts come from
docs/brand-guide/assets; Pillow's built-in font is the fallback when they are missing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from ..schemas.compliance import Citation, ComplianceNote
from ..schemas.steps import Question, Step

FONT_DIR = Path(__file__).resolve().parents[3] / "docs" / "brand-guide" / "assets"
SANS = "SpaceGrotesk.ttf"
MONO = "SpaceMono-Regular.ttf"
MONO_BOLD = "SpaceMono-Bold.ttf"

# RGB, from the brand guide: dark ink background, off-white text, lime accent.
BG = (41, 39, 51)
PANEL = (52, 50, 64)
TEXT = (243, 244, 248)
SOFT = (205, 207, 218)
MUTED = (150, 153, 170)
RULE = (81, 77, 99)
ACCENT = (214, 232, 121)
ON_ACCENT = (41, 39, 51)

MIN_SCALE = 0.6          # plain shrink-to-fit floor
MIN_SCALE_VARIANTS = 0.72  # floor before falling back to a less detailed variant


# ---- fonts ---------------------------------------------------------------------------------

@lru_cache(maxsize=256)
def font(name: str, size: int, weight: str | None = None) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    size = max(int(size), 6)
    path = FONT_DIR / name
    try:
        f = ImageFont.truetype(str(path), size)
    except OSError:
        return ImageFont.load_default(size)
    if weight:
        try:
            f.set_variation_by_name(weight)
        except (OSError, ValueError):
            pass
    return f


def sans(size: float, weight: str = "Regular"):
    return font(SANS, int(size), weight)


def mono(size: float, bold: bool = False):
    return font(MONO_BOLD if bold else MONO, int(size))


def _text_w(f, text: str) -> float:
    return f.getlength(text)


def _line_h(f) -> int:
    ascent, descent = f.getmetrics() if hasattr(f, "getmetrics") else (f.size, 0)
    return int(ascent + descent)


def wrap(text: str, f, width: float) -> list[str]:
    """Greedy word wrap; words longer than the width are broken by character."""
    lines: list[str] = []
    for para in str(text).split("\n"):
        cur = ""
        for word in para.split():
            cand = f"{cur} {word}" if cur else word
            if _text_w(f, cand) <= width:
                cur = cand
                continue
            if cur:
                lines.append(cur)
            while _text_w(f, word) > width and len(word) > 1:
                k = len(word)
                while k > 1 and _text_w(f, word[:k]) > width:
                    k -= 1
                lines.append(word[:k])
                word = word[k:]
            cur = word
        lines.append(cur)
    return lines


def ellipsize(line: str, f, width: float) -> str:
    if _text_w(f, line) <= width:
        return line
    while line and _text_w(f, line + "…") > width:
        line = line[:-1]
    return line.rstrip() + "…"


def _clip_lines(lines: list[str], max_lines: int | None, f, width: float) -> list[str]:
    if max_lines is None or len(lines) <= max_lines:
        return lines
    kept = lines[:max_lines]
    kept[-1] = ellipsize(kept[-1] + " …", f, width) if _text_w(f, kept[-1] + "…") > width else kept[-1] + "…"
    return kept


# ---- citations -----------------------------------------------------------------------------

_SMALL_WORDS = {"of", "the", "and", "for", "to", "in", "on", "a", "an", "at", "by", "or", "with"}


def doc_label(doc_name: str) -> str:
    """'fda-food-code-2022.pdf' -> 'FDA Food Code 2022'; names that already have spaces/case are kept."""
    name = re.sub(r"\.(pdf|docx?|txt|md|html?)$", "", doc_name.strip(), flags=re.I)
    name = re.sub(r"^d\d{2}-", "", name)  # project document prefix
    if " " in name or name != name.lower():
        return re.sub(r"[_]+", " ", name)[:48]
    words = [w for w in re.split(r"[-_\s]+", name) if w]
    out = []
    for w in words:
        if w.isdigit():
            out.append(w)
        elif len(w) <= 3 and w not in _SMALL_WORDS:
            out.append(w.upper())
        else:
            out.append(w if w in _SMALL_WORDS and out else w.capitalize())
    return " ".join(out)[:48]


def short_citation(c: Citation) -> str:
    return f"{doc_label(c.doc_name)} p.{c.page}" if c.page is not None else doc_label(c.doc_name)


def citations_text(citations: list[Citation]) -> str:
    seen: list[str] = []
    for c in citations:
        s = short_citation(c)
        if s not in seen:
            seen.append(s)
    return "; ".join(seen)


# ---- layout engine -------------------------------------------------------------------------

@dataclass
class Block:
    text: str
    size: float                      # px at 720 p, before shrink-to-fit
    kind: str = "sans"               # sans | mono
    weight: str = "Regular"
    color: tuple = TEXT
    space_before: float = 0          # px at 720 p
    max_lines: int | None = None
    bullet: str | None = None
    bullet_color: tuple = ACCENT
    indent: float = 0
    line_gap: float = 1.18

    def font(self, px: float):
        return mono(px, bold=self.weight == "Bold") if self.kind == "mono" else sans(px, self.weight)


@dataclass
class _Op:
    x: float
    y: float
    text: str
    font: object
    color: tuple


SHAPES = ("@dot", "@tri")  # bullets drawn as shapes (the brand fonts lack these glyphs)


def _bullet_w(f, bullet: str) -> float:
    if bullet in SHAPES:
        return _text_w(f, "§  ")
    return _text_w(f, bullet + "  ")


def _shape(draw: ImageDraw.ImageDraw, kind: str, x: float, y: float, f, color) -> None:
    """Draw a bullet shape vertically centred on the x-height of a text line starting at (x, y)."""
    asc = f.getmetrics()[0] if hasattr(f, "getmetrics") else f.size
    r = asc * 0.2
    cy = y + asc * 0.66
    if kind == "@dot":
        draw.ellipse((x, cy - r, x + 2 * r, cy + r), fill=color)
    else:
        r = asc * 0.3
        draw.polygon([(x, cy + r * 0.8), (x + r, cy - r * 0.95), (x + 2 * r, cy + r * 0.8)], fill=color)


@dataclass
class Layout:
    ops: list[_Op] = field(default_factory=list)
    height: float = 0
    scale: float = 1.0


def _layout(blocks: list[Block], width: float, u: float, scale: float, final: bool) -> Layout:
    lay = Layout(scale=scale)
    y = 0.0
    for b in blocks:
        px = b.size * u * scale
        f = b.font(px)
        lh = _line_h(f) * b.line_gap
        y += b.space_before * u * scale
        indent = b.indent * u * scale
        bullet_w = _bullet_w(f, b.bullet) if b.bullet else 0.0
        avail = width - indent - bullet_w
        lines = wrap(b.text, f, avail)
        if final:
            lines = _clip_lines(lines, b.max_lines, f, avail)
        elif b.max_lines is not None:
            lines = lines[: b.max_lines]
        for k, line in enumerate(lines):
            if k == 0 and b.bullet:
                lay.ops.append(_Op(indent, y, b.bullet, f, b.bullet_color))
            lay.ops.append(_Op(indent + bullet_w, y, line, f, b.color))
            y += lh
    lay.height = y
    return lay


def _scales(floor: float) -> list[float]:
    out, s = [], 1.0
    while s >= floor:
        out.append(s)
        s *= 0.94
    return out


def _try_fit(blocks: list[Block], width: float, height: float, u: float, floor: float) -> Layout | None:
    """Largest scale >= floor where everything fits untruncated; else the largest where it fits truncated."""
    for scale in _scales(floor):
        if not _overflowing(blocks, width, u, scale) and _layout(blocks, width, u, scale, final=False).height <= height:
            return _layout(blocks, width, u, scale, final=True)
    for scale in _scales(floor):
        lay = _layout(blocks, width, u, scale, final=True)
        if lay.height <= height:
            return lay
    return None


def fit_variants(variants: list[list[Block]], width: float, height: float, u: float) -> Layout:
    """First variant (most detailed first) that fits at a legible scale; else the last one, force-fitted."""
    for blocks in variants:
        if lay := _try_fit(blocks, width, height, u, MIN_SCALE_VARIANTS):
            return lay
    return fit(variants[-1], width, height, u)


def fit(blocks: list[Block], width: float, height: float, u: float) -> Layout:
    """Largest scale (<= 1) at which the blocks fit; at the minimum scale, extra lines are cut."""
    if lay := _try_fit(blocks, width, height, u, MIN_SCALE):
        return lay
    lay = _layout(blocks, width, u, MIN_SCALE, final=True)
    # Still too tall: drop trailing blocks until it fits.
    while lay.height > height and len(blocks) > 1:
        blocks = blocks[:-1]
        lay = _layout(blocks, width, u, MIN_SCALE, final=True)
    return lay


def _overflowing(blocks: list[Block], width: float, u: float, scale: float) -> bool:
    """True if any block would exceed its max_lines at this scale (so we shrink before truncating)."""
    for b in blocks:
        if b.max_lines is None:
            continue
        f = b.font(b.size * u * scale)
        avail = width - b.indent * u * scale - (_bullet_w(f, b.bullet) if b.bullet else 0)
        if len(wrap(b.text, f, avail)) > b.max_lines:
            return True
    return False


def _draw_ops(draw: ImageDraw.ImageDraw, lay: Layout, x0: float, y0: float) -> None:
    for op in lay.ops:
        if op.text in SHAPES:
            _shape(draw, op.text, x0 + op.x, y0 + op.y, op.font, op.color)
        else:
            draw.text((x0 + op.x, y0 + op.y), op.text, font=op.font, fill=op.color)


def _pill(draw: ImageDraw.ImageDraw, x: float, y: float, text: str, f, fill, ink, pad: float, anchor_right=False) -> tuple[float, float]:
    tw = _text_w(f, text)
    h = _line_h(f) + pad
    w = tw + 2 * pad
    if anchor_right:
        x -= w
    draw.rounded_rectangle((x, y, x + w, y + h), radius=h / 2, fill=fill)
    draw.text((x + pad, y + pad / 2), text, font=f, fill=ink)
    return w, h


def _canvas(width: int, height: int) -> tuple[Image.Image, ImageDraw.ImageDraw, float]:
    img = Image.new("RGB", (width, height), BG)
    return img, ImageDraw.Draw(img), height / 720.0


def _to_bgr(img: Image.Image) -> np.ndarray:
    return np.ascontiguousarray(np.asarray(img.convert("RGB"))[:, :, ::-1])


def fmt_time(t: float) -> str:
    t = max(int(round(t)), 0)
    return f"{t // 60}:{t % 60:02d}"


def fmt_duration(t: float) -> str:
    t = max(int(round(t)), 0)
    return f"{t // 60} min {t % 60:02d} s" if t >= 60 else f"{t} s"


def _frame_margins(width: int, height: int, u: float) -> tuple[float, float]:
    return max(width * 0.075, 48 * u), 56 * u


def _progress(draw, x0, y, width, u, n, current) -> None:
    if n <= 0:
        return
    gap = 6 * u
    seg = (width - gap * (n - 1)) / n
    for k in range(n):
        x = x0 + k * (seg + gap)
        color = ACCENT if k == current else (MUTED if k < current else RULE)
        draw.rectangle((x, y, x + seg, y + 4 * u), fill=color)


# ---- cards ---------------------------------------------------------------------------------

def intro_card(width: int, height: int, title: str, n_steps: int, duration: float, source: str | None = None,
               license: str | None = None, uploader: str | None = None, open_questions: int = 0) -> np.ndarray:
    img, d, u = _canvas(width, height)
    mx, my = _frame_margins(width, height, u)
    inner = width - 2 * mx

    # Attribution at the bottom, fixed size.
    meta_lines = []
    if source:
        meta_lines.append(("SOURCE", source))
    if uploader:
        meta_lines.append(("BY", uploader))
    if license:
        meta_lines.append(("LICENSE", license))
    mf = mono(15 * u)
    lab_w = max((_text_w(mf, k) for k, _ in meta_lines), default=0) + 14 * u
    y = height - my
    for key, val in reversed(meta_lines):
        y -= _line_h(mf) * 1.35
        d.text((mx, y), key, font=mf, fill=MUTED)
        d.text((mx + lab_w, y), ellipsize(val, mf, inner - lab_w), font=mf, fill=SOFT)
    bottom = y - 24 * u
    if meta_lines:
        d.line((mx, bottom + 8 * u, mx + inner, bottom + 8 * u), fill=RULE, width=max(int(u), 1))

    sub = f"{n_steps} step{'s' if n_steps != 1 else ''}  ·  {fmt_duration(duration)}"
    blocks = [
        Block("TUTORIAL", 18, kind="mono", weight="Bold", color=ACCENT),
        Block(title or "Untitled tutorial", 64, weight="Bold", space_before=14, max_lines=3, line_gap=1.08),
        Block(sub, 28, color=SOFT, space_before=22),
    ]
    if open_questions:
        blocks.append(Block(f"{open_questions} open question{'s' if open_questions != 1 else ''} for the uploader "
                            "— see the end", 20, color=MUTED, space_before=10, bullet="@dot"))
    top = my + 40 * u
    lay = fit(blocks, inner * 0.9, bottom - top, u)
    _draw_ops(d, lay, mx, top + max((bottom - top - lay.height) * 0.42, 0))
    return _to_bgr(img)


def step_card(width: int, height: int, step: Step, number: int, total: int,
              notes: list[ComplianceNote] = (), needs_info: bool = False, needs_info_text: list[str] = (),
              max_notes: int = 3, max_cautions: int = 3) -> np.ndarray:
    img, d, u = _canvas(width, height)
    mx, my = _frame_margins(width, height, u)
    inner = width - 2 * mx

    # Header: step counter + time range, progress bar, optional needs-info badge.
    hf = mono(18 * u, bold=True)
    d.text((mx, my), f"STEP {number} OF {total}", font=hf, fill=ACCENT)
    tf = mono(16 * u)
    d.text((mx + _text_w(hf, f"STEP {number} OF {total}") + 18 * u, my + 2 * u),
           f"{fmt_time(step.start)} – {fmt_time(step.end)}", font=tf, fill=MUTED)
    if needs_info:
        bf = mono(15 * u, bold=True)
        w, h = _pill(d, mx + inner, my - 6 * u, "    NEEDS INFO FROM UPLOADER", bf, ACCENT, ON_ACCENT, 10 * u,
                     anchor_right=True)
        _shape(d, "@dot", mx + inner - w + 12 * u, my - 6 * u + 5 * u, bf, ON_ACCENT)
    _progress(d, mx, my + _line_h(hf) + 14 * u, inner, u, total, number - 1)
    top = my + _line_h(hf) + 46 * u

    things = [*step.tools, *[m for m in step.materials if m not in step.tools]]
    detail = [(max_cautions, max_notes, 2, True, 4), (2, 2, 1, True, 4), (1, 1, 1, True, 3), (1, 1, 1, False, 3),
              (0, 1, 1, False, 3), (0, 0, 1, False, 2)]
    variants = [_step_blocks(step, number, things if tools else [], notes, needs_info_text if needs_info else [],
                             min(nc, max_cautions), min(nn, max_notes), nw, il)
                for nc, nn, nw, tools, il in detail]
    avail = height - my - top
    lay = fit_variants(variants, inner, avail, u)
    _draw_ops(d, lay, mx, top + max((avail - lay.height) * 0.3, 0))
    return _to_bgr(img)


def _step_blocks(step: Step, number: int, things: list[str], notes: list[ComplianceNote], waiting: list[str],
                 max_cautions: int, max_notes: int, max_waiting: int, instruction_lines: int) -> list[Block]:
    blocks = [
        Block(step.title or f"Step {number}", 52, weight="Bold", max_lines=2, line_gap=1.08),
        Block(step.instruction, 28, color=SOFT, space_before=14, max_lines=instruction_lines),
    ]
    if things:
        blocks += [Block("TOOLS & MATERIALS", 14, kind="mono", color=MUTED, space_before=26),
                   Block("  ·  ".join(things), 22, space_before=6, max_lines=2)]
    if step.cautions:
        blocks.append(Block("CAUTION", 14, kind="mono", color=MUTED, space_before=22))
        for k, c in enumerate(step.cautions[:max_cautions]):
            blocks.append(Block(c, 22, bullet="!", space_before=6 if k == 0 else 4, max_lines=2))
        if len(step.cautions) > max_cautions:
            blocks.append(Block(f"+{len(step.cautions) - max_cautions} more in tutorial.json", 15, kind="mono",
                                color=MUTED, space_before=4))
    if notes:
        blocks.append(Block("COMPLIANCE", 14, kind="mono", color=MUTED, space_before=22))
        for k, n in enumerate(notes[:max_notes]):
            marker = "@tri" if n.kind == "conflict" or n.severity == "critical" else "§"
            blocks.append(Block(n.text, 22, bullet=marker, space_before=6 if k == 0 else 8, max_lines=2))
            blocks.append(Block(citations_text(n.citations), 15, kind="mono", color=MUTED, indent=16, max_lines=1,
                                space_before=2))
        if len(notes) > max_notes:
            blocks.append(Block(f"+{len(notes) - max_notes} more notes in tutorial.json", 15, kind="mono",
                                color=MUTED, space_before=4))
    if waiting and max_waiting:
        blocks.append(Block("WAITING ON", 14, kind="mono", color=ACCENT, space_before=22))
        for k, q in enumerate(waiting[:max_waiting]):
            blocks.append(Block(q, 20, color=SOFT, bullet="?", space_before=6 if k == 0 else 4, max_lines=2))
    return blocks


def outro_card(width: int, height: int, questions: list[Question], step_numbers: dict[str, int] | None = None,
               footer: str = "", max_items: int = 6, notes: list[ComplianceNote] = ()) -> np.ndarray:
    """Open questions (blocking first) and whole-procedure compliance notes; a 'done' card when both are empty."""
    img, d, u = _canvas(width, height)
    mx, my = _frame_margins(width, height, u)
    inner = width - 2 * mx
    step_numbers = step_numbers or {}
    ff = mono(14 * u)
    bottom = height - my
    if footer:
        bottom -= _line_h(ff)
        d.text((mx, bottom), ellipsize(footer, ff, inner), font=ff, fill=MUTED)
        bottom -= 20 * u

    if not questions and not notes:
        blocks = [Block("DONE", 18, kind="mono", weight="Bold", color=ACCENT),
                  Block("That's the whole procedure.", 56, weight="Bold", space_before=14, max_lines=2),
                  Block("No open questions remain for the uploader.", 26, color=SOFT, space_before=18)]
        top = my + 40 * u
        lay = fit(blocks, inner, bottom - top, u)
        _draw_ops(d, lay, mx, top + max((bottom - top - lay.height) * 0.42, 0))
        return _to_bgr(img)

    ordered = sorted(questions, key=lambda q: (not q.blocking, q.priority, q.id))

    def build(n_q: int, n_notes: int) -> list[Block]:
        if ordered:
            blocks = [Block("OPEN QUESTIONS", 18, kind="mono", weight="Bold", color=ACCENT),
                      Block("Still needed from the uploader", 44, weight="Bold", space_before=10, max_lines=1)]
        else:
            blocks = [Block("DONE", 18, kind="mono", weight="Bold", color=ACCENT),
                      Block("No open questions remain", 44, weight="Bold", space_before=10, max_lines=1)]
        for k, q in enumerate(ordered[:n_q]):
            where = f"STEP {step_numbers[q.step_id]}" if q.step_id in step_numbers else "WHOLE PROCEDURE"
            tag = f"{q.id.upper()}  ·  {where}" + ("  ·  BLOCKING" if q.blocking else "")
            blocks.append(Block(tag, 14, kind="mono", color=ACCENT if q.blocking else MUTED,
                                space_before=26 if k == 0 else 16))
            blocks.append(Block(q.text, 24, space_before=4, max_lines=2))
        if len(ordered) > n_q:
            blocks.append(Block(f"+{len(ordered) - n_q} more in questions.json", 15, kind="mono", color=MUTED,
                                space_before=14))
        if notes:
            blocks.append(Block("WHOLE-PROCEDURE NOTES", 14, kind="mono", color=MUTED, space_before=30))
            for k, n in enumerate(notes[:n_notes]):
                marker = "@tri" if n.kind in ("conflict", "missing_step") or n.severity == "critical" else "§"
                blocks.append(Block(n.text, 22, bullet=marker, space_before=8 if k == 0 else 10, max_lines=2))
                blocks.append(Block(citations_text(n.citations), 15, kind="mono", color=MUTED, indent=16,
                                    max_lines=1, space_before=2))
            if len(notes) > n_notes:
                blocks.append(Block(f"+{len(notes) - n_notes} more in tutorial.json", 15, kind="mono", color=MUTED,
                                    space_before=6))
        return blocks

    variants = [build(min(nq, max_items), nn) for nq, nn in ((6, 3), (4, 2), (3, 1), (2, 1), (2, 0))]
    lay = fit_variants(variants, inner, bottom - my, u)
    _draw_ops(d, lay, mx, my)
    return _to_bgr(img)


# ---- caption -------------------------------------------------------------------------------

def first_sentence(text: str) -> str:
    m = re.match(r"(.+?[.!?])(\s|$)", text.strip())
    return (m.group(1) if m else text).strip()


def caption_overlay(width: int, height: int, number: int, total: int, title: str, instruction: str = "",
                    needs_info: bool = False) -> tuple[int, np.ndarray]:
    """Lower-third caption as (y0, BGRA band). Blend it onto clip frames with ``blend_band``."""
    u = height / 720.0
    mx = max(width * 0.04, 20 * u)
    pad = 16 * u
    tf = sans(26 * u, "Bold")
    sf = sans(19 * u, "Regular")
    pf = mono(17 * u, bold=True)
    pill_text = f"{number}/{total}"
    pill_w = _text_w(pf, pill_text) + 2 * 12 * u
    text_x = pad + pill_w + 14 * u
    max_text_w = width - 2 * mx - text_x - pad
    line1 = ellipsize(title, tf, max_text_w)
    sub = first_sentence(instruction) if instruction else ""
    if sub and sub.rstrip(".").strip().lower() == title.strip().lower():
        sub = ""
    prefix = "Needs info from uploader" + ("  ·  " if sub else "") if needs_info else ""
    line2 = ellipsize(prefix + sub, sf, max_text_w) if (prefix or sub) else ""
    content_h = _line_h(tf) + (_line_h(sf) + 4 * u if line2 else 0)
    panel_w = text_x + max(_text_w(tf, line1), _text_w(sf, line2) if line2 else 0) + pad
    panel_h = content_h + 2 * pad
    band_h = int(np.ceil(panel_h + 28 * u))
    y0 = height - band_h

    img = Image.new("RGBA", (width, band_h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    px0, py0 = mx, 0
    d.rounded_rectangle((px0, py0, px0 + panel_w, py0 + panel_h), radius=10 * u, fill=(*BG, 224))
    ph = _line_h(pf) + 8 * u
    d.rounded_rectangle((px0 + pad, py0 + pad + (_line_h(tf) - ph) / 2, px0 + pad + pill_w,
                         py0 + pad + (_line_h(tf) - ph) / 2 + ph), radius=ph / 2, fill=(*ACCENT, 255))
    d.text((px0 + pad + 12 * u, py0 + pad + (_line_h(tf) - ph) / 2 + 4 * u), pill_text, font=pf, fill=(*ON_ACCENT, 255))
    d.text((px0 + text_x, py0 + pad), line1, font=tf, fill=(*TEXT, 255))
    if line2:
        y2 = py0 + pad + _line_h(tf) + 4 * u
        head = line2[: len(prefix)] if prefix else ""
        if head:
            d.text((px0 + text_x, y2), head, font=sf, fill=(*ACCENT, 255))
        if line2[len(head):]:
            d.text((px0 + text_x + _text_w(sf, head), y2), line2[len(head):], font=sf, fill=(*SOFT, 255))
    arr = np.asarray(img)
    bgra = np.ascontiguousarray(arr[:, :, [2, 1, 0, 3]])
    return y0, bgra


def blend_band(frame: np.ndarray, y0: int, band: np.ndarray) -> np.ndarray:
    """Alpha-blend a BGRA band onto a BGR frame starting at row y0 (in place)."""
    h = min(band.shape[0], frame.shape[0] - y0)
    w = min(band.shape[1], frame.shape[1])
    if h <= 0:
        return frame
    region = frame[y0:y0 + h, :w].astype(np.float32)
    alpha = band[:h, :w, 3:4].astype(np.float32) / 255.0
    region = region * (1 - alpha) + band[:h, :w, :3].astype(np.float32) * alpha
    frame[y0:y0 + h, :w] = region.astype(np.uint8)
    return frame


def reading_seconds(texts: list[str], minimum: float, maximum: float, wps: float = 3.5, base: float = 1.5) -> float:
    """Card duration that scales with the amount of text, clamped to [minimum, maximum]."""
    words = sum(len(str(t).split()) for t in texts)
    return float(min(max(base + words / wps, minimum), maximum))
