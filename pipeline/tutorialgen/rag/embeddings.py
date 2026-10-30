"""Embedding providers, selected by the ``embeddings`` config section.

- ``local``: fastembed (ONNX, CPU) with ``model`` (default BAAI/bge-small-en-v1.5); model files are
  cached under ``pipeline/models/`` (gitignored).
- ``openai``: ``openai_model`` (default text-embedding-3-small); requires OPENAI_API_KEY.
- ``hash``: deterministic hashed bag of words/bigrams; no download, used by tests.

All providers return L2-normalized float32 rows, so cosine similarity is a dot product.
"""

from __future__ import annotations

import hashlib
import logging
import os
from abc import ABC, abstractmethod
from pathlib import Path

import numpy as np
from pydantic import BaseModel

from .text import tokenize

log = logging.getLogger(__name__)

MODELS_DIR = Path(__file__).resolve().parents[2] / "models"


class EmbeddingSettings(BaseModel):
    provider: str = "local"            # local | openai | hash
    model: str = "BAAI/bge-small-en-v1.5"
    openai_model: str = "text-embedding-3-small"
    batch_size: int = 32
    threads: int | None = 4            # fastembed ONNX threads; None = all cores
    hash_dims: int = 512
    cache_dir: str | None = None       # default: pipeline/models/fastembed


def _normalize(m: np.ndarray) -> np.ndarray:
    m = np.asarray(m, dtype=np.float32)
    if m.ndim == 1:
        m = m[None, :]
    norms = np.linalg.norm(m, axis=1, keepdims=True)
    return m / np.maximum(norms, 1e-12)


class Embedder(ABC):
    name: str  # "<provider>:<model>", stored in the index manifest

    def __init__(self, batch_size: int = 32):
        self.batch_size = batch_size

    @abstractmethod
    def _embed(self, texts: list[str], query: bool) -> np.ndarray: ...

    def embed_documents(self, texts: list[str]) -> np.ndarray:
        return self._batched(texts, query=False)

    def embed_queries(self, texts: list[str]) -> np.ndarray:
        return self._batched(texts, query=True)

    def _batched(self, texts: list[str], query: bool) -> np.ndarray:
        if not texts:
            return np.zeros((0, 0), dtype=np.float32)
        parts = [self._embed(texts[i:i + self.batch_size], query) for i in range(0, len(texts), self.batch_size)]
        return _normalize(np.vstack(parts))


class HashEmbedder(Embedder):
    """Signed feature hashing of unigrams + bigrams. Lexical only, but deterministic and instant."""

    def __init__(self, dims: int = 512, batch_size: int = 256):
        super().__init__(batch_size)
        self.dims = dims
        self.name = f"hash:{dims}"

    def _embed(self, texts: list[str], query: bool) -> np.ndarray:
        out = np.zeros((len(texts), self.dims), dtype=np.float32)
        for row, text in enumerate(texts):
            toks = tokenize(text)
            for feat in toks + [f"{a}_{b}" for a, b in zip(toks, toks[1:])]:
                h = int.from_bytes(hashlib.blake2b(feat.encode(), digest_size=8).digest(), "little")
                out[row, h % self.dims] += 1.0 if (h >> 63) & 1 else -1.0
        return out


class FastEmbedder(Embedder):
    # bge v1.5 retrieves better when queries carry this instruction (passages do not).
    BGE_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "

    def __init__(self, model: str, batch_size: int = 32, threads: int | None = 4, cache_dir: str | None = None):
        super().__init__(batch_size)
        self.model_name = model
        self.name = f"local:{model}"
        self.threads = threads
        self.cache_dir = Path(cache_dir) if cache_dir else MODELS_DIR / "fastembed"
        self._model = None

    @property
    def model(self):
        if self._model is None:
            from fastembed import TextEmbedding

            self.cache_dir.mkdir(parents=True, exist_ok=True)
            log.info("loading embedding model %s (cache %s)", self.model_name, self.cache_dir)
            self._model = TextEmbedding(self.model_name, cache_dir=str(self.cache_dir), threads=self.threads)
        return self._model

    def _embed(self, texts: list[str], query: bool) -> np.ndarray:
        if query and "bge" in self.model_name.lower() and "-en" in self.model_name.lower():
            texts = [self.BGE_QUERY_PREFIX + t for t in texts]
        return np.vstack(list(self.model.embed(texts, batch_size=self.batch_size)))


class OpenAIEmbedder(Embedder):
    def __init__(self, model: str, batch_size: int = 128):
        super().__init__(batch_size)
        from openai import OpenAI

        self.model_name = model
        self.name = f"openai:{model}"
        self.client = OpenAI()

    def _embed(self, texts: list[str], query: bool) -> np.ndarray:
        resp = self.client.embeddings.create(model=self.model_name, input=texts)
        return np.array([d.embedding for d in sorted(resp.data, key=lambda d: d.index)], dtype=np.float32)


def make_embedder(settings: EmbeddingSettings) -> Embedder:
    if settings.provider == "hash":
        return HashEmbedder(settings.hash_dims)
    if settings.provider == "local":
        return FastEmbedder(settings.model, settings.batch_size, settings.threads, settings.cache_dir)
    if settings.provider == "openai":
        if not os.environ.get("OPENAI_API_KEY"):
            raise ValueError("embeddings.provider=openai needs OPENAI_API_KEY; use 'local' instead")
        return OpenAIEmbedder(settings.openai_model, max(settings.batch_size, 64))
    raise ValueError(f"unknown embeddings provider '{settings.provider}' (local | openai | hash)")
