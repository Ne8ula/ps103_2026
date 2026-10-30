"""Section-aware chunking. Sizes are in words (~1.3 tokens each), so 300 words is ~400 tokens.

Rules: a chunk never crosses a document; a new section heading closes the current chunk once it
holds at least ``min_words`` (tiny sections are merged forward instead of becoming crumbs); a chunk
closes before it would exceed ``max_words``, and the next one in the same section starts with the
last ~``overlap_words`` of it. Units are sentences/clauses, so chunks never cut mid-sentence unless a
single sentence is longer than ``max_words``.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from ..schemas.compliance import DocChunk
from .loaders import Block
from .text import sentences, word_count


@dataclass
class _Unit:
    text: str
    page: int | None
    section: str | None
    heading: bool
    words: int


def _units(blocks: list[Block], max_words: int) -> list[_Unit]:
    out = []
    for b in blocks:
        if b.heading:
            out.append(_Unit(b.text, b.page, b.section, True, word_count(b.text)))
            continue
        for s in sentences(b.text):
            words = s.split()
            # A run-on "sentence" longer than a chunk (tables, lists without punctuation) is hard-split.
            for i in range(0, len(words), max_words):
                piece = " ".join(words[i:i + max_words])
                out.append(_Unit(piece, b.page, b.section, False, min(max_words, len(words) - i)))
    return out


def chunk_blocks(doc_id: str, doc_name: str, blocks: list[Block], max_words: int = 300,
                 overlap_words: int = 40, min_words: int = 60) -> list[DocChunk]:
    units = _units(blocks, max_words)
    chunks: list[DocChunk] = []
    buf: list[_Unit] = []

    def size() -> int:
        return sum(u.words for u in buf)

    def emit():
        if not buf or all(u.heading for u in buf):
            return
        text = ""
        for u in buf:
            if u.heading:
                text += ("\n" if text else "") + u.text + "\n"
            else:
                text += ("" if not text or text.endswith("\n") else " ") + u.text
        by_section = Counter()
        for u in buf:
            if u.section:
                by_section[u.section] += u.words
        pages = [u.page for u in buf if u.page is not None]
        chunks.append(DocChunk(
            id=f"{doc_id}:{len(chunks)}", doc_id=doc_id, doc_name=doc_name,
            page=pages[0] if pages else None,
            page_end=pages[-1] if pages and pages[-1] != pages[0] else None,
            section=by_section.most_common(1)[0][0] if by_section else None,
            text=text.strip(),
        ))

    for u in units:
        if u.heading and size() >= min_words:
            emit()
            buf = []
        elif buf and size() + u.words > max_words:
            emit()
            # Overlap: carry trailing sentences of the same section into the next chunk.
            carry: list[_Unit] = []
            for prev in reversed(buf):
                if prev.heading or prev.section != u.section or sum(c.words for c in carry) + prev.words > overlap_words:
                    break
                carry.insert(0, prev)
            buf = carry
        buf.append(u)
    emit()
    return chunks
