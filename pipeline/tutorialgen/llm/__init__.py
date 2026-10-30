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


OPENAI_DEFAULT_MODEL = "gpt-5.4-mini"


class LLMSettings(BaseModel):
    provider: str = "auto"
    model: str | None = None            # None = the provider's default
    max_images_per_call: int = 6
    timeout_s: float = 120
    replay: bool = False                # answer only from llm_cache; a miss is an error
    base_url: str | None = None         # "chat" provider: any OpenAI-compatible endpoint
    api_key_env: str = "OPENAI_API_KEY"
    min_interval_s: float | None = None  # spacing between requests (free-tier RPM limits)


def _resolve(s: LLMSettings) -> str:
    if s.provider != "auto":
        return s.provider
    for env, name in (("OPENAI_API_KEY", "openai"), ("GEMINI_API_KEY", "gemini")):
        if os.environ.get(env):
            return name
    log.warning("no OPENAI_API_KEY or GEMINI_API_KEY: using the fake LLM provider (deterministic placeholder text)")
    return "fake"


def make_provider(config: Config) -> LLMProvider:
    from .chat_provider import PRESETS, ChatProvider, ReplayProvider

    s = config.section("llm", LLMSettings)
    provider = _resolve(s)
    if provider == "fake":
        return FakeProvider("fake")
    if provider == "openai":
        model = s.model or OPENAI_DEFAULT_MODEL
    elif provider in PRESETS:
        base_url, key_env, default_model = PRESETS[provider]
        model = s.model or default_model
    elif provider == "chat":
        if not (s.base_url and s.model):
            raise ValueError("llm.provider 'chat' needs llm.base_url and llm.model")
        base_url, key_env, model = s.base_url, s.api_key_env, s.model
    else:
        raise ValueError(f"unknown llm provider '{provider}'")

    if s.replay:
        return ReplayProvider(provider, model)
    if provider == "openai":
        from .openai_provider import OpenAIProvider

        return OpenAIProvider(model, s.timeout_s)
    interval = s.min_interval_s if s.min_interval_s is not None else (6.0 if provider == "gemini" else 0.0)
    return ChatProvider(provider, model, base_url, key_env, s.timeout_s, interval)


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
