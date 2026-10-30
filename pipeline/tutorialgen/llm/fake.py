"""Deterministic stand-in provider.

Each LLM task registers a handler that builds a plausible answer from ``request.context`` alone,
so the full pipeline runs end to end without an API key and tests are reproducible. Handlers live
next to the stage that owns the task (``@fake_handler("segment_steps")``).
"""

from __future__ import annotations

from typing import Callable

from pydantic import BaseModel

from .base import LLMError, LLMProvider, LLMRequest, T

_HANDLERS: dict[str, Callable[[LLMRequest], BaseModel]] = {}


def fake_handler(task: str):
    def register(fn: Callable[[LLMRequest], BaseModel]):
        _HANDLERS[task] = fn
        return fn

    return register


class FakeProvider(LLMProvider):
    name = "fake"

    def generate(self, request: LLMRequest[T]) -> T:
        handler = _HANDLERS.get(request.task)
        if handler is None:
            raise LLMError(f"no fake handler registered for task '{request.task}'")
        result = handler(request)
        return request.schema.model_validate(result.model_dump() if isinstance(result, BaseModel) else result)
