"""Document RAG for the compliance stage: load -> chunk -> embed -> index -> hybrid retrieve -> cite."""

from .chunker import chunk_blocks
from .embeddings import EmbeddingSettings, Embedder, make_embedder
from .index import DocSource, Index, IndexManifest, load_or_build_index
from .loaders import Block, LoadedDoc, load_document
from .notes import MissingStepDraft, MissingStepsOutput, QuoteRef, StepNoteDraft, StepNotesOutput, validate_notes
from .retrieve import Hit, HybridRetriever, procedure_query, step_query
from .text import quote_in_text

__all__ = [name for name in dir() if not name.startswith("_")]
