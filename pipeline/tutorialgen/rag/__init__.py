"""Document RAG for the compliance stage: load -> chunk -> embed -> index -> hybrid retrieve -> cite."""

from .chunker import chunk_blocks
from .embeddings import EmbeddingSettings, Embedder, make_embedder
from .index import DocSource, Index, IndexManifest, load_or_build_index
from .loaders import Block, LoadedDoc, load_document
from .notes import (
    ProcedureCoverageOutput, SentenceRef, Shown, SopProcedureOutput, SopStepCoverage, SopStepDraft, StepFinding,
    StepFindingsOutput, chunk_sentences, format_chunk, resolve_citations, validate_findings,
)
from .rerank import CrossEncoderReranker
from .retrieve import Facet, Hit, HybridRetriever, expand_neighbours, procedure_query, step_facets, step_query
from .text import quote_in_text

__all__ = [name for name in dir() if not name.startswith("_")]
