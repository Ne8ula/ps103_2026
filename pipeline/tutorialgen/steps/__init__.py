"""Shared helpers for the LLM orchestration stages (segment, draft, refine, questions).

- ``upstream``: tolerant loaders for ingest/transcript/gesture/candidate artifacts and per-range text.
- ``frames``: representative JPEG extraction with OpenCV.
- ``windows``: candidate intervals, overlapping windows and the deterministic cross-window merge.
- ``guards``: deterministic guardrails (ungrounded numbers become missing-info, not assertions).
- ``llm_schemas``: structured-output schemas for every LLM task (all fields required, no dicts).
- ``fakes``: ``@fake_handler`` implementations; imported by the stage modules so they are registered.
"""
