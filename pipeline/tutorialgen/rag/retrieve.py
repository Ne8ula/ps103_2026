"""Hybrid retrieval: BM25 (exact terms like "2-301.12", "fingernails") + dense cosine (paraphrase),
fused with reciprocal-rank fusion so neither score scale has to be calibrated.

Structured retrieval for a step: the step's fields become separate sub-queries ("facets": the action,
the objects handled, time/temperature/quantity clauses, cautions, and the whole procedure as
context), each retrieved with BM25 + dense, all fused with weighted RRF. Optionally a cross-encoder
re-ranks the fused candidates against the full step query, and the neighbours of the best hits are
added when they continue the same section (a numbered procedure split across two chunks).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import numpy as np
from rank_bm25 import BM25Okapi

from ..schemas.compliance import DocChunk
from ..schemas.steps import Step
from .embeddings import Embedder
from .index import Index, embed_text
from .text import clean, sentences, tokenize


@dataclass
class Hit:
    chunk: DocChunk
    score: float              # fused RRF score (or cross-encoder score after re-ranking)
    bm25_rank: int | None     # 1-based rank in each list (None = outside the candidate pool)
    dense_rank: int | None
    facets: list[str] = field(default_factory=list)  # facets whose lists contained the chunk
    neighbour_of: str | None = None                   # set for chunks added by neighbour expansion


@dataclass
class Facet:
    name: str     # action | objects | quantities | safety | procedure | query
    query: str
    weight: float = 1.0


def step_query(step: Step) -> str:
    """Query per step: title + instruction + tools/materials + cautions."""
    parts = [step.title, step.instruction]
    if step.tools or step.materials:
        parts.append("Using " + ", ".join(step.tools + step.materials) + ".")
    parts += step.cautions
    return " ".join(p.strip() for p in parts if p and p.strip())


def procedure_query(steps: list[Step]) -> str:
    """Whole-procedure query for the missing-step check."""
    return " ".join(f"{s.title}. {s.instruction}" for s in steps)


_QUANTITY = re.compile(
    r"\d|\b(seconds?|minutes?|hours?|degrees?|temperature|hot|warm|cold|times?|once|twice|amount|dose|"
    r"ml|litres?|liters?|grams?|ppm|percent)\b", re.I)


def step_facets(step: Step, procedure: str | None = None, weights: dict[str, float] | None = None) -> list[Facet]:
    """Sub-queries built from the step's structured fields. Weights are relative RRF weights."""
    w = {"action": 1.0, "objects": 0.5, "quantities": 0.5, "safety": 0.5, "procedure": 0.5} | (weights or {})
    action = " ".join([f"{step.title}.", step.instruction, *step.details]).strip()
    out = [Facet("action", action, w["action"])]
    things = list(dict.fromkeys(step.tools + step.materials))
    if things:
        out.append(Facet("objects", f"{step.title}: " + ", ".join(things), w["objects"]))
    text = " ".join([step.instruction, *step.details])
    quantities = [s for s in sentences(text) if _QUANTITY.search(s)]
    if quantities:
        out.append(Facet("quantities", f"{step.title}: " + " ".join(quantities), w["quantities"]))
    if step.cautions:
        out.append(Facet("safety", f"{step.title}: " + " ".join(step.cautions), w["safety"]))
    if procedure:
        out.append(Facet("procedure", procedure, w["procedure"]))
    return [f for f in out if w.get(f.name, 0) > 0 and f.query.strip()]


class HybridRetriever:
    def __init__(self, index: Index, embedder: Embedder, rrf_k: int = 60, pool: int = 50):
        self.index = index
        self.embedder = embedder
        self.rrf_k = rrf_k
        self.pool = pool
        corpus = [tokenize(embed_text(c)) for c in index.chunks]
        self.bm25 = BM25Okapi(corpus) if corpus and any(corpus) else None
        self._qcache: dict[str, np.ndarray] = {}

    def search(self, queries: list[str], top_k: int) -> list[list[Hit]]:
        """One plain query per result list (BM25 + dense, RRF)."""
        return self.search_facets([[Facet("query", q)] for q in queries], top_k)

    def search_facets(self, facet_sets: list[list[Facet]], top_k: int) -> list[list[Hit]]:
        """One result list per facet set: every facet contributes a BM25 and a dense list, weighted."""
        if not self.index.chunks or not facet_sets:
            return [[] for _ in facet_sets]
        self._embed_queries([f.query for fs in facet_sets for f in fs])
        return [self._fuse(fs, top_k) for fs in facet_sets]

    def _embed_queries(self, queries: list[str]) -> None:
        todo = list(dict.fromkeys(q for q in queries if q not in self._qcache))
        if todo:
            for q, v in zip(todo, self.embedder.embed_queries(todo)):
                self._qcache[q] = v

    def _orders(self, query: str) -> tuple[np.ndarray, np.ndarray]:
        pool = min(self.pool, len(self.index.chunks))
        dense = self.index.vectors @ self._qcache[query]
        dense_order = np.argsort(-dense, kind="stable")[:pool]
        bm25_order: np.ndarray = np.array([], dtype=int)
        qtoks = tokenize(query)
        if self.bm25 is not None and qtoks:
            scores = self.bm25.get_scores(qtoks)
            bm25_order = np.argsort(-scores, kind="stable")[:pool]
            bm25_order = bm25_order[scores[bm25_order] > 0]
        return bm25_order, dense_order

    def _fuse(self, facets: list[Facet], top_k: int) -> list[Hit]:
        fused: dict[int, float] = {}
        ranks: dict[int, list[int | None]] = {}
        seen_in: dict[int, list[str]] = {}
        for facet in facets:
            for which, order in enumerate(self._orders(facet.query)):
                for rank, i in enumerate(order, start=1):
                    i = int(i)
                    fused[i] = fused.get(i, 0.0) + facet.weight / (self.rrf_k + rank)
                    r = ranks.setdefault(i, [None, None])
                    if facet is facets[0]:  # report ranks of the main facet
                        r[which] = rank
                    if facet.name not in seen_in.setdefault(i, []):
                        seen_in[i].append(facet.name)
        best = sorted(fused, key=lambda i: (-fused[i], i))[:top_k]
        return [Hit(self.index.chunks[i], fused[i], ranks[i][0], ranks[i][1], seen_in[i]) for i in best]


def expand_neighbours(hits: list[Hit], chunks: list[DocChunk], top: int = 2, limit: int = 2) -> list[Hit]:
    """Add the previous/next chunk of the ``top`` best hits when it is in the same document and section
    (a numbered list or long clause split across chunks). Added chunks go right after their source."""
    pos = {c.id: n for n, c in enumerate(chunks)}
    have = {h.chunk.id for h in hits}
    out: list[Hit] = []
    added = 0
    for rank, h in enumerate(hits):
        out.append(h)
        if rank >= top or h.chunk.id not in pos:
            continue
        n = pos[h.chunk.id]
        for m in (n - 1, n + 1):
            if added >= limit or not 0 <= m < len(chunks):
                continue
            nb = chunks[m]
            if nb.id in have or nb.doc_id != h.chunk.doc_id or not nb.section or nb.section != h.chunk.section:
                continue
            if not _continues(chunks[min(n, m)], chunks[max(n, m)]):
                continue
            have.add(nb.id)
            added += 1
            out.append(Hit(nb, h.score, None, None, ["neighbour"], neighbour_of=h.chunk.id))
    return out


_ENUM = re.compile(r"\((\d{1,2}|[a-z])\)")


def _continues(first: DocChunk, second: DocChunk) -> bool:
    """True if ``second`` continues ``first``: it does not open with a new heading, or the enumeration
    "(n)" running at the end of ``first`` goes on in ``second``."""
    head = clean(second.text).split("\n", 1)[0].strip()
    if not re.match(r"^\d{1,2}-\d{1,3}(?:\.\d{1,3})?\s+[A-Z]", head):
        return True
    tail_items = _ENUM.findall(first.text[-400:])
    return bool(tail_items) and bool(_ENUM.search(second.text[:400]))
