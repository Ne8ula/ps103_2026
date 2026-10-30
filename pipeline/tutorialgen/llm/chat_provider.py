"""Adapter for any OpenAI-compatible Chat Completions endpoint (Gemini, Ollama, OpenRouter, vLLM, ...).

Structured output first tries ``response_format`` with the strict JSON schema; if the endpoint rejects
the schema, it falls back to JSON mode with the schema in the prompt and validates the reply locally.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time

from pydantic import ValidationError

from .base import LLMError, LLMProvider, LLMRequest, T

log = logging.getLogger(__name__)

# Tried in order when the primary model stays overloaded (503/timeout) or out of quota (429) after retries.
FALLBACKS: dict[str, tuple[str, ...]] = {
    "gemini": ("gemini-3.5-flash", "gemini-3-flash-preview", "gemini-3.1-flash-lite"),
}

# name -> (base_url, api key env var, default model)
PRESETS: dict[str, tuple[str, str, str]] = {
    "gemini": ("https://generativelanguage.googleapis.com/v1beta/openai/", "GEMINI_API_KEY", "gemini-3.6-flash"),
    "ollama": ("http://localhost:11434/v1/", "OLLAMA_API_KEY", "qwen2.5vl:3b"),
}


class ChatProvider(LLMProvider):
    def __init__(self, name: str, model: str, base_url: str, api_key_env: str,
                 timeout_s: float = 120, min_interval_s: float = 0.0, max_retries: int = 3,
                 fallback_models: tuple[str, ...] = ()):
        super().__init__(model)
        self.name = name
        self.fallback_models = tuple(m for m in fallback_models if m != model)
        self.served_by: str | None = None  # model that answered the last request (cache provenance)
        from openai import OpenAI

        key = os.environ.get(api_key_env) or ("ollama" if name == "ollama" else None)
        if not key:
            raise LLMError(f"{name}: set {api_key_env} to use this provider")
        # The SDK retries 429/5xx with backoff and honours Retry-After.
        self.client = OpenAI(api_key=key, base_url=base_url, timeout=timeout_s, max_retries=max_retries)
        self.min_interval_s = min_interval_s
        self._last = 0.0
        self._lock = threading.Lock()
        self._json_mode_only = False

    def _throttle(self) -> None:
        """Space requests out to stay under free-tier requests-per-minute limits."""
        with self._lock:
            wait = self._last + self.min_interval_s - time.monotonic()
            if wait > 0:
                time.sleep(wait)
            self._last = time.monotonic()

    def _messages(self, request: LLMRequest, system_extra: str = "") -> list[dict]:
        content: list[dict] = [{"type": "text", "text": request.user}]
        content += [{"type": "image_url", "image_url": {"url": url}} for url in request.image_data_urls()]
        return [{"role": "system", "content": request.system + system_extra}, {"role": "user", "content": content}]

    def generate(self, request: LLMRequest[T]) -> T:
        from openai import APIConnectionError, APITimeoutError, InternalServerError, OpenAIError, RateLimitError

        models = (self.model, *self.fallback_models)
        for i, model in enumerate(models):
            try:
                result = self._generate_with(request, model)
                self.served_by = model
                return result
            # Free-tier quotas are per model, so a 429 that outlasts the SDK's retries also moves on.
            except (InternalServerError, APITimeoutError, APIConnectionError, RateLimitError) as exc:
                if i + 1 < len(models):
                    log.warning("%s:%s unavailable for %s (%s); falling back to %s",
                                self.name, model, request.task, type(exc).__name__, models[i + 1])
                    continue
                raise LLMError(f"{self.label} failed on {request.task} (all models unavailable): {exc}") from exc
            except OpenAIError as exc:
                raise LLMError(f"{self.name}:{model} failed on {request.task}: {exc}") from exc
        raise AssertionError("unreachable")

    def _generate_with(self, request: LLMRequest[T], model: str) -> T:
        from openai import BadRequestError

        if not self._json_mode_only:
            self._throttle()
            try:
                completion = self.client.chat.completions.parse(
                    model=model, messages=self._messages(request), response_format=request.schema)
                parsed = completion.choices[0].message.parsed
                if parsed is not None:
                    return parsed
                log.warning("%s:%s returned no parsed output for %s; retrying in JSON mode", self.name, model, request.task)
            except BadRequestError as exc:
                log.warning("%s:%s rejected the JSON schema for %s (%s); switching to JSON mode", self.name, model, request.task, exc)
                self._json_mode_only = True
        return self._generate_json_mode(request, model)

    def _generate_json_mode(self, request: LLMRequest[T], model: str) -> T:
        schema = json.dumps(request.schema.model_json_schema())
        extra = ("\n\nReply with a single JSON object only, no prose or code fences, matching this JSON schema:\n" + schema)
        messages = self._messages(request, extra)
        for attempt in range(2):
            self._throttle()
            completion = self.client.chat.completions.create(
                model=model, messages=messages, response_format={"type": "json_object"})
            text = (completion.choices[0].message.content or "").strip().removeprefix("```json").removesuffix("```")
            try:
                return request.schema.model_validate_json(text)
            except ValidationError as exc:
                if attempt:
                    raise LLMError(f"{self.name}:{model} returned invalid JSON for {request.task}: {exc}") from exc
                messages = messages + [{"role": "assistant", "content": text},
                                       {"role": "user", "content": f"That JSON did not match the schema: {exc}. Reply with corrected JSON only."}]
        raise AssertionError("unreachable")


class ReplayProvider(LLMProvider):
    """Answers only from the LLM cache. Same label as the provider that filled it, so stages and cache
    keys line up; any cache miss is an error, so a demo can never call (or pay for) a live model."""

    def __init__(self, name: str, model: str):
        super().__init__(model)
        self.name = name

    def generate(self, request: LLMRequest[T]) -> T:
        raise LLMError(f"replay mode: no cached {self.label} answer for task '{request.task}'. "
                       "Run once without llm.replay to record it.")
