"""OpenAI adapter (default: GPT-5.4 mini) using the Responses API with structured outputs."""

from __future__ import annotations

from .base import LLMError, LLMProvider, LLMRequest, T


class OpenAIProvider(LLMProvider):
    name = "openai"

    def __init__(self, model: str, timeout_s: float = 120):
        super().__init__(model)
        from openai import OpenAI

        self.client = OpenAI(timeout=timeout_s)

    def generate(self, request: LLMRequest[T]) -> T:
        content: list[dict] = [{"type": "input_text", "text": request.user}]
        content += [{"type": "input_image", "image_url": url} for url in request.image_data_urls()]
        try:
            response = self.client.responses.parse(
                model=self.model,
                input=[
                    {"role": "system", "content": request.system},
                    {"role": "user", "content": content},
                ],
                text_format=request.schema,
            )
        except Exception as exc:  # network, auth, schema rejection
            raise LLMError(f"{self.label} failed on {request.task}: {exc}") from exc
        parsed = response.output_parsed
        if parsed is None:
            raise LLMError(f"{self.label} returned no parsable output for {request.task}")
        return parsed
