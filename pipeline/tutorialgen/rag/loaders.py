"""Document loaders: PDF (pypdf, page numbers kept), DOCX (headings become sections), TXT/MD.

Every loader returns a ``LoadedDoc``: an ordered list of ``Block``s, each one heading or one run
of body text on a single page, already cleaned (ligatures, smart quotes, hyphenation at line breaks,
running headers/footers). The chunker only sees blocks, so it is format-agnostic.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from .text import clean

SUPPORTED = (".pdf", ".docx", ".txt", ".md", ".markdown")


@dataclass
class Block:
    text: str
    page: int | None = None
    section: str | None = None   # nearest heading above (for headings: the heading itself)
    heading: bool = False


@dataclass
class LoadedDoc:
    blocks: list[Block] = field(default_factory=list)
    pages: int | None = None


def load_document(path: Path, strip_priority_markers: bool = True) -> LoadedDoc:
    suffix = Path(path).suffix.lower()
    if suffix == ".pdf":
        return load_pdf(path, strip_priority_markers)
    if suffix == ".docx":
        return load_docx(path)
    if suffix in (".txt", ".md", ".markdown"):
        return load_text(Path(path).read_text(errors="replace"))
    raise ValueError(f"unsupported document type '{suffix}' ({path}); supported: {', '.join(SUPPORTED)}")


# ---- headings ---------------------------------------------------------------------------------

# "2-301.12 Cleaning Procedure."  "2-3 Personal Cleanliness"  "3.1 Scope"  "4. Equipment"
_NUMBERED_HEADING = re.compile(
    r"^(?P<num>\d{1,2}-\d{1,3}(?:\.\d{1,3})?|\d{1,2}(?:\.\d{1,2}){0,3}\.?)\s+"
    r"(?P<title>[A-Z][A-Za-z0-9 ,'/&()\-]{1,80}?)\.?\s*(?:\(.{1,30}\))?\s*$"
)
_MD_HEADING = re.compile(r"^\s{0,3}#{1,6}\s+(?P<title>.+?)\s*#*\s*$")


def heading_of(line: str) -> str | None:
    """Return a normalized heading label if the line looks like a numbered section heading."""
    m = _NUMBERED_HEADING.match(line.strip())
    if not m:
        return None
    title = m.group("title").strip()
    words = title.split()
    if not 1 <= len(words) <= 12 or title.endswith((",", ";", "-")):
        return None
    # Body lines that begin with a number ("20 Seconds is the minimum ...") are rarely title-cased.
    lower_words = [w for w in words if w[0].islower() and w not in {"and", "or", "of", "for", "the", "to", "in", "on", "a", "with", "by"}]
    if len(lower_words) > max(1, len(words) // 3):
        return None
    return f"{m.group('num').rstrip('.')} {title}".strip()


# ---- PDF --------------------------------------------------------------------------------------

_ROMAN = re.compile(r"\b[ivxlc]+\b")


def _furniture_key(line: str) -> str:
    key = re.sub(r"\d+", "#", line.lower())
    key = _ROMAN.sub("#", key)
    return re.sub(r"\s+", " ", key).strip()


def _prefix(key: str) -> str:
    """First three words of a long line: running headers often vary only in their chapter title."""
    words = key.split()
    return " ".join(words[:3]) if len(words) >= 5 else ""


def _strip_page_furniture(pages: list[list[str]], edge: int = 3) -> list[list[str]]:
    """Drop running headers/footers: lines near the top/bottom of a page that recur on many pages."""
    n = len(pages)
    if n < 4:
        return pages
    full, prefix = Counter(), Counter()
    for lines in pages:
        edges = {_furniture_key(l) for l in lines[:edge] + lines[-edge:] if l.strip()}
        full.update(edges)
        prefix.update({_prefix(k) for k in edges if _prefix(k)})
    out = []
    for lines in pages:
        kept = []
        for i, line in enumerate(lines):
            at_edge = i < edge or i >= len(lines) - edge
            k = _furniture_key(line)
            if at_edge and k and (full[k] >= max(3, 0.15 * n) or (_prefix(k) and prefix[_prefix(k)] >= 0.3 * n)):
                continue
            kept.append(line)
        out.append(kept)
    return out


# FDA-style priority markers after a clause: "clean.P", "water; P", "procedure, Pf and"
_PRIORITY_MARK = re.compile(r"(?<=[.;,:])\s?P[f]?(?=\s|$)")


def _join_lines(lines: list[str]) -> str:
    """Join hard-wrapped lines, removing hyphenation at line ends ("com-\\npound" -> "compound")."""
    out = ""
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if out.endswith("-") and len(out) > 1 and out[-2].isalpha() and line[:1].islower():
            out = out[:-1] + line
        else:
            out = f"{out} {line}" if out else line
    return out


def pages_to_blocks(page_texts: list[str], strip_priority_markers: bool = True) -> list[Block]:
    """Turn raw per-page text into heading/body blocks. Separated from pypdf so it is unit-testable."""
    pages = [clean(t).split("\n") for t in page_texts]
    pages = _strip_page_furniture(pages)
    blocks: list[Block] = []
    section: str | None = None
    for page_no, lines in enumerate(pages, start=1):
        body: list[str] = []

        def flush():
            text = _join_lines(body)
            if strip_priority_markers:
                text = _PRIORITY_MARK.sub("", text)
            text = re.sub(r"\s+", " ", text).strip()
            if text:
                blocks.append(Block(text=text, page=page_no, section=section))
            body.clear()

        for line in lines:
            label = heading_of(line)
            if label:
                flush()
                section = label
                blocks.append(Block(text=line.strip(), page=page_no, section=section, heading=True))
            else:
                body.append(line)
        flush()
    return blocks


def load_pdf(path: Path, strip_priority_markers: bool = True) -> LoadedDoc:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    texts = [(page.extract_text() or "") for page in reader.pages]
    return LoadedDoc(blocks=pages_to_blocks(texts, strip_priority_markers), pages=len(texts))


# ---- DOCX -------------------------------------------------------------------------------------


def load_docx(path: Path) -> LoadedDoc:
    import docx
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    document = docx.Document(str(path))
    blocks: list[Block] = []
    section: str | None = None
    for child in document.element.body.iterchildren():
        tag = child.tag.rsplit("}", 1)[-1]
        if tag == "p":
            para = Paragraph(child, document)
            text = clean(para.text).replace("\n", " ").strip()
            if not text:
                continue
            style = (para.style.name if para.style is not None else "") or ""
            if style.startswith(("Heading", "Title")) or heading_of(text):
                section = text.rstrip(".")
                blocks.append(Block(text=text, section=section, heading=True))
            else:
                blocks.append(Block(text=text, section=section))
        elif tag == "tbl":
            for row in Table(child, document).rows:
                cells = []
                for cell in row.cells:
                    t = clean(cell.text).replace("\n", " ").strip()
                    if t and (not cells or cells[-1] != t):  # merged cells repeat their text
                        cells.append(t)
                if cells:
                    blocks.append(Block(text=" | ".join(cells), section=section))
    return LoadedDoc(blocks=blocks)


# ---- TXT / Markdown ---------------------------------------------------------------------------


def load_text(raw: str) -> LoadedDoc:
    blocks: list[Block] = []
    section: str | None = None
    para: list[str] = []

    def flush():
        text = re.sub(r"\s+", " ", _join_lines(para)).strip()
        if text:
            blocks.append(Block(text=text, section=section))
        para.clear()

    for line in clean(raw).split("\n"):
        md = _MD_HEADING.match(line)
        label = md.group("title").strip() if md else heading_of(line)
        if label:
            flush()
            section = label.rstrip(".")
            blocks.append(Block(text=(md.group("title").strip() if md else line.strip()), section=section, heading=True))
        elif not line.strip():
            flush()
        elif re.match(r"^\s*(?:[-*+]|\d+[.)]|\([0-9a-zA-Z]+\))\s+", line):
            flush()  # list items start their own block
            para.append(line)
        else:
            para.append(line)
    flush()
    return LoadedDoc(blocks=blocks)
