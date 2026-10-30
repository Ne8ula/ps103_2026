"""Text helpers shared by loaders, retrieval and citation checks."""

from __future__ import annotations

import re
import unicodedata

_PUNCT_MAP = str.maketrans({
    "‘": "'", "’": "'", "‚": "'", "‛": "'",
    "“": '"', "”": '"', "„": '"',
    "‐": "-", "‑": "-", "‒": "-", "–": "-", "—": "-", "−": "-",
    " ": " ", " ": " ", " ": " ", "­": "",
    "•": " ", "": " ",
})
_CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")
_SPACES = re.compile(r"[ \t]+")


def clean(text: str) -> str:
    """Unicode-normalize (ligatures, smart quotes, dashes) and collapse runs of spaces; keeps newlines."""
    text = unicodedata.normalize("NFKC", text).translate(_PUNCT_MAP)
    text = _CONTROL.sub(" ", text)
    return "\n".join(_SPACES.sub(" ", line).strip() for line in text.split("\n"))


def squash(text: str) -> str:
    """Whitespace- and case-insensitive canonical form used to match quotes against chunk text."""
    return re.sub(r"\s+", " ", clean(text)).strip().lower()


def quote_in_text(quote: str, text: str, min_chars: int = 12) -> bool:
    """True if ``quote`` occurs verbatim in ``text`` modulo whitespace, case and typographic punctuation.

    Leading/trailing ellipses, quote marks and terminal punctuation on the quote are ignored, since
    models often add or trim them.
    """
    q = squash(quote).strip(" .…'\"`;:,")
    q = q.removeprefix("...").removesuffix("...").strip()
    if len(q) < min_chars:
        return False
    return q in squash(text)


def word_count(text: str) -> int:
    return len(text.split())


_STOP = frozenset(
    "a an and are as at be been but by can do does for from has have he her his if in into is it its "
    "may must not of on or our shall should so such than that the their them then there these they this "
    "to under up was we were what when where which while who will with you your".split()
)
_TOKEN = re.compile(r"[a-z0-9]+")


def stem(word: str) -> str:
    """Very light suffix stripping so 'hands'/'hand', 'washing'/'wash', 'rinsed'/'rinse' meet."""
    for suf, min_len in (("ing", 6), ("ed", 5), ("es", 5), ("s", 4)):
        if word.endswith(suf) and len(word) >= min_len and not word.endswith("ss"):
            return word[: -len(suf)]
    return word


def tokenize(text: str) -> list[str]:
    """Lowercase content-word tokens for BM25 and overlap scoring."""
    return [stem(t) for t in _TOKEN.findall(clean(text).lower()) if t not in _STOP]


_NUMBER = re.compile(r"(?<![A-Za-z0-9])\d+(?:[.,]\d+)?")


def numbers(text: str) -> set[str]:
    """Standalone numbers in a text ('2-301.12' -> {'2', '301.12'}; 's03' is not a number)."""
    return {n.replace(",", "") for n in _NUMBER.findall(clean(text))}


_SENTENCE_BREAK = re.compile(r"(?<=[.;:!?])\s+|\n+")


def sentences(text: str) -> list[str]:
    """Rough sentence/clause split at punctuation followed by whitespace; items are verbatim substrings."""
    return [s.strip() for s in _SENTENCE_BREAK.split(text) if s and s.strip()]
