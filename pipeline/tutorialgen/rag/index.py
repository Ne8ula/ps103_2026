"""Document index on disk: ``chunks.json`` (DocIndex) + ``embeddings.npy`` + ``manifest.json``.

Embedding a large manual on CPU takes minutes, so the index is rebuilt only when the manifest
changes: document ids/shas, embedding model, or chunking parameters.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from ..schemas.common import Artifact
from ..schemas.compliance import DocChunk, DocIndex, DocumentInfo
from .chunker import chunk_blocks
from .embeddings import Embedder
from .loaders import load_document

log = logging.getLogger(__name__)

INDEX_VERSION = 2  # bump when loader/chunker output changes, to force a rebuild


class IndexedDocument(Artifact):
    id: str
    sha: str


class IndexManifest(Artifact):
    """compliance/index/manifest.json — the inputs the index was built from."""

    version: int = INDEX_VERSION
    embedding_model: str
    documents: list[IndexedDocument]
    chunking: dict[str, int | bool]
    build_seconds: float | None = None

    def same_inputs(self, other: "IndexManifest") -> bool:
        keys = ("version", "embedding_model", "documents", "chunking")
        return all(getattr(self, k) == getattr(other, k) for k in keys)


@dataclass
class DocSource:
    id: str
    name: str
    path: Path          # absolute
    rel_path: str       # relative to project root
    sha: str


@dataclass
class Index:
    doc_index: DocIndex
    vectors: np.ndarray       # (n_chunks, dims), L2-normalized
    manifest: IndexManifest
    rebuilt: bool

    @property
    def chunks(self) -> list[DocChunk]:
        return self.doc_index.chunks


def build_index(docs: list[DocSource], embedder: Embedder, max_words: int = 300, overlap_words: int = 40,
                min_words: int = 60, strip_priority_markers: bool = True) -> tuple[DocIndex, np.ndarray]:
    infos, chunks = [], []
    for doc in docs:
        t0 = time.perf_counter()
        loaded = load_document(doc.path, strip_priority_markers)
        doc_chunks = chunk_blocks(doc.id, doc.name, loaded.blocks, max_words, overlap_words, min_words)
        log.info("%s: %s pages, %d chunks (%.1fs to parse)", doc.name, loaded.pages, len(doc_chunks), time.perf_counter() - t0)
        infos.append(DocumentInfo(id=doc.id, name=doc.name, path=doc.rel_path, pages=loaded.pages, chunks=len(doc_chunks)))
        chunks += doc_chunks
    t0 = time.perf_counter()
    vectors = embedder.embed_documents([embed_text(c) for c in chunks])
    log.info("embedded %d chunks with %s in %.1fs", len(chunks), embedder.name, time.perf_counter() - t0)
    return DocIndex(embedding_model=embedder.name, documents=infos, chunks=chunks), vectors


def embed_text(chunk: DocChunk) -> str:
    """What gets embedded: the section label adds context to chunks that start mid-section."""
    if chunk.section and not chunk.text.startswith(chunk.section.split(" ", 1)[0]):
        return f"{chunk.section}\n{chunk.text}"
    return chunk.text


def load_or_build_index(index_dir: Path, docs: list[DocSource], embedder: Embedder, max_words: int = 300,
                        overlap_words: int = 40, min_words: int = 60, strip_priority_markers: bool = True) -> Index:
    index_dir = Path(index_dir)
    wanted = IndexManifest(
        embedding_model=embedder.name,
        documents=[IndexedDocument(id=d.id, sha=d.sha) for d in docs],
        chunking={"max_words": max_words, "overlap_words": overlap_words, "min_words": min_words,
                  "strip_priority_markers": strip_priority_markers},
    )
    paths = {k: index_dir / f for k, f in (("manifest", "manifest.json"), ("chunks", "chunks.json"), ("vectors", "embeddings.npy"))}
    if all(p.exists() for p in paths.values()):
        try:
            have = IndexManifest.model_validate_json(paths["manifest"].read_text())
            if have.same_inputs(wanted):
                doc_index = DocIndex.model_validate_json(paths["chunks"].read_text())
                vectors = np.load(paths["vectors"])
                if len(vectors) == len(doc_index.chunks):
                    log.info("reusing index (%d chunks, %s)", len(doc_index.chunks), have.embedding_model)
                    return Index(doc_index, vectors, have, rebuilt=False)
        except Exception as exc:  # corrupt or old-format index: rebuild
            log.warning("index unreadable (%s); rebuilding", exc)

    t0 = time.perf_counter()
    doc_index, vectors = build_index(docs, embedder, max_words, overlap_words, min_words, strip_priority_markers)
    wanted.build_seconds = round(time.perf_counter() - t0, 2)
    index_dir.mkdir(parents=True, exist_ok=True)
    paths["manifest"].unlink(missing_ok=True)
    paths["chunks"].write_text(doc_index.model_dump_json(indent=1))
    np.save(paths["vectors"], vectors.astype(np.float32))
    paths["manifest"].write_text(wanted.model_dump_json(indent=2))  # last: marks the index complete
    return Index(doc_index, vectors, wanted, rebuilt=True)
