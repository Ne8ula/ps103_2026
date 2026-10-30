"""Cross-encoder re-ranking of fused retrieval candidates (fastembed ONNX, CPU).

The bi-encoder (bge-small) ranks dense legal text poorly for short step queries; a small MS MARCO
cross-encoder reading (query, chunk) pairs moves the relevant procedure chunk up and pushes it out
for unrelated steps. See eval/rag_compliance_bench.py for the measured effect.
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np

from .embeddings import MODELS_DIR
from .index import embed_text
from .retrieve import Hit

log = logging.getLogger(__name__)

DEFAULT_RERANK_MODEL = "Xenova/ms-marco-MiniLM-L-6-v2"


class CrossEncoderReranker:
    def __init__(self, model: str = DEFAULT_RERANK_MODEL, threads: int | None = 4, cache_dir: str | None = None):
        self.model_name = model
        self.threads = threads
        self.cache_dir = Path(cache_dir) if cache_dir else MODELS_DIR / "fastembed"
        self._model = None

    @property
    def model(self):
        if self._model is None:
            from fastembed.rerank.cross_encoder import TextCrossEncoder

            self.cache_dir.mkdir(parents=True, exist_ok=True)
            log.info("loading re-ranker %s (cache %s)", self.model_name, self.cache_dir)
            self._model = TextCrossEncoder(self.model_name, cache_dir=str(self.cache_dir), threads=self.threads)
        return self._model

    def scores(self, query: str, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros(0, dtype=np.float32)
        return np.asarray(list(self.model.rerank(query, texts)), dtype=np.float32)

    def rerank(self, query: str, hits: list[Hit]) -> list[Hit]:
        """Hits re-ordered by cross-encoder score (stable for ties); ``score`` becomes that score."""
        s = self.scores(query, [embed_text(h.chunk) for h in hits])
        order = np.argsort(-s, kind="stable")
        out = []
        for i in order:
            h = hits[int(i)]
            h.score = float(s[int(i)])
            out.append(h)
        return out
