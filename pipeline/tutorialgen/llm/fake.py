"""Deterministic stand-in provider.

Each LLM task registers a handler that builds a plausible answer from ``request.context`` alone,
so the full pipeline runs end to end without an API key and tests are reproducible. Handlers live
next to the stage that owns the task (``@fake_handler("segment_steps")``).
"""

from __future__ import annotations

import hashlib
import inspect
from typing import Callable

from pydantic import BaseModel

from .base import LLMError, LLMProvider, LLMRequest, T

_HANDLERS: dict[str, Callable[[LLMRequest], BaseModel]] = {}


def fake_handler(task: str):
    def register(fn: Callable[[LLMRequest], BaseModel]):
        _HANDLERS[task] = fn
        return fn

    return register


def handlers_version() -> str:
    """Hash of every registered handler's source, so editing a fake invalidates its cache entries and fingerprints."""
    from ..stages import STAGES  # handlers register on import; load them all so the hash is stable

    for spec in STAGES.values():
        if spec.uses_llm:
            spec.load()
    h = hashlib.sha256()
    for task in sorted(_HANDLERS):
        h.update(task.encode())
        try:
            h.update(inspect.getsource(inspect.getmodule(_HANDLERS[task])).encode())
        except (OSError, TypeError):
            pass
    return h.hexdigest()[:8]


class FakeProvider(LLMProvider):
    name = "fake"

    @property
    def model(self) -> str:
        return f"{self._model}-{handlers_version()}" if self._model == "fake" else self._model

    @model.setter
    def model(self, value: str) -> None:
        self._model = value

    def generate(self, request: LLMRequest[T]) -> T:
        handler = _HANDLERS.get(request.task)
        if handler is None:
            raise LLMError(f"no fake handler registered for task '{request.task}'")
        result = handler(request)
        return request.schema.model_validate(result.model_dump() if isinstance(result, BaseModel) else result)
