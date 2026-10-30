"""LLM access for stages: ``CachedLLM.call(request)`` -> (parsed result, cache key)."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from pydantic import BaseModel

from ..config import Config
from .base import LLMError, LLMProvider, LLMRequest, T
from .fake import FakeProvider, fake_handler

log = logging.getLogger(__name__)

__all__ = ["CachedLLM", "LLMError", "LLMProvider", "LLMRequest", "fake_handler", "make_provider"]


class LLMSettings(BaseModel):
    provider: str = "auto"
    model: str = "gpt-5.4-mini"
    max_images_per_call: int = 6
    timeout_s: float = 120


def make_provider(config: Config) -> LLMProvider:
    s = config.section("llm", LLMSettings)
    provider = s.provider
    if provider == "auto":
        provider = "openai" if os.environ.get("OPENAI_API_KEY") else "fake"
        if provider == "fake":
            log.warning("OPENAI_API_KEY not set: using the fake LLM provider (deterministic placeholder text)")
    if provider == "openai":
        from .openai_provider import OpenAIProvider

        return OpenAIProvider(s.model, s.timeout_s)
    if provider == "fake":
        return FakeProvider("fake")
    raise ValueError(f"unknown llm provider '{provider}'")


class CachedLLM:
    """Wraps a provider with an on-disk cache keyed by the full request, so re-runs are free and inspectable."""

    def __init__(self, provider: LLMProvider, cache_dir: Path, max_images: int = 6):
        self.provider = provider
        self.cache_dir = Path(cache_dir)
        self.max_images = max_images

    @property
    def label(self) -> str:
        return self.provider.label

    def call(self, request: LLMRequest[T]) -> tuple[T, str]:
        if len(request.images) > self.max_images:
            request.images = request.images[: self.max_images]
        key = request.cache_key(self.provider.name, self.provider.model)
        path = self.cache_dir / f"{key}.json"
        if path.exists():
            cached = json.loads(path.read_text())
            return request.schema.model_validate(cached["response"]), key
        result = self.provider.generate(request)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "task": request.task,
                    "provider": self.provider.label,
                    "prompt_version": request.prompt_version,
                    "system": request.system,
                    "user": request.user,
                    "images": [str(p) for p in request.images],
                    "response": result.model_dump(mode="json"),
                },
                indent=2,
            )
        )
        return result, key
