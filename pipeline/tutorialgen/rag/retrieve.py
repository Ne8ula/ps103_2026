"""Hybrid retrieval: BM25 (exact terms like "2-301.12", "fingernails") + dense cosine (paraphrase),
fused with reciprocal-rank fusion so neither score scale has to be calibrated."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from rank_bm25 import BM25Okapi

from ..schemas.compliance import DocChunk
from ..schemas.steps import Step
from .embeddings import Embedder
from .index import Index, embed_text
from .text import tokenize


@dataclass
class Hit:
    chunk: DocChunk
    score: float              # fused RRF score
    bm25_rank: int | None     # 1-based rank in each list (None = outside the candidate pool)
    dense_rank: int | None


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


class HybridRetriever:
    def __init__(self, index: Index, embedder: Embedder, rrf_k: int = 60, pool: int = 50):
        self.index = index
        self.embedder = embedder
        self.rrf_k = rrf_k
        self.pool = pool
        corpus = [tokenize(embed_text(c)) for c in index.chunks]
        self.bm25 = BM25Okapi(corpus) if corpus and any(corpus) else None

    def search(self, queries: list[str], top_k: int) -> list[list[Hit]]:
        chunks = self.index.chunks
        if not chunks or not queries:
            return [[] for _ in queries]
        qvecs = self.embedder.embed_queries(queries)
        return [self._fuse(q, qv, top_k) for q, qv in zip(queries, qvecs)]

    def _fuse(self, query: str, qvec: np.ndarray, top_k: int) -> list[Hit]:
        n = len(self.index.chunks)
        pool = min(self.pool, n)
        dense = self.index.vectors @ qvec
        dense_order = np.argsort(-dense, kind="stable")[:pool]
        bm25_order: np.ndarray = np.array([], dtype=int)
        qtoks = tokenize(query)
        if self.bm25 is not None and qtoks:
            scores = self.bm25.get_scores(qtoks)
            bm25_order = np.argsort(-scores, kind="stable")[:pool]
            bm25_order = bm25_order[scores[bm25_order] > 0]
        fused: dict[int, float] = {}
        ranks: dict[int, list[int | None]] = {}
        for which, order in ((0, bm25_order), (1, dense_order)):
            for rank, i in enumerate(order, start=1):
                i = int(i)
                fused[i] = fused.get(i, 0.0) + 1.0 / (self.rrf_k + rank)
                ranks.setdefault(i, [None, None])[which] = rank
        best = sorted(fused, key=lambda i: (-fused[i], i))[:top_k]
        return [Hit(self.index.chunks[i], fused[i], ranks[i][0], ranks[i][1]) for i in best]
