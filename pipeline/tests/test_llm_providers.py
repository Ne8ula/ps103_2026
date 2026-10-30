"""Chat-completions adapter (Gemini preset), JSON-mode fallback, replay mode, provider selection."""

from __future__ import annotations

import json

import httpx
import pytest
from openai import OpenAI
from pydantic import BaseModel

from tutorialgen.config import Config
from tutorialgen.llm import CachedLLM, LLMRequest, make_provider
from tutorialgen.llm.base import LLMError
from tutorialgen.llm.chat_provider import ChatProvider, ReplayProvider


class Answer(BaseModel):
    title: str
    seconds: int | None


def completion(content: str) -> dict:
    return {"id": "c1", "object": "chat.completion", "created": 0, "model": "m",
            "choices": [{"index": 0, "finish_reason": "stop",
                         "message": {"role": "assistant", "content": content}}]}


def provider_with(monkeypatch, responses: list[httpx.Response], bodies: list[dict]) -> ChatProvider:
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    p = make_provider(Config.load(overrides={"llm": {"provider": "gemini", "min_interval_s": 0}}))
    assert isinstance(p, ChatProvider) and p.label == "gemini:gemini-3.6-flash"
    queue = list(responses)

    def handler(request: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(request.content))
        assert request.headers["authorization"] == "Bearer test-key"
        assert str(request.url).startswith("https://generativelanguage.googleapis.com/v1beta/openai/chat/completions")
        return queue.pop(0)

    p.client = OpenAI(api_key="test-key", base_url=str(p.client.base_url), max_retries=0,
                      http_client=httpx.Client(transport=httpx.MockTransport(handler)))
    p.queue = queue  # tests may append more responses
    return p


def request(tmp_path) -> LLMRequest:
    import cv2
    import numpy as np

    img = tmp_path / "k.jpg"
    cv2.imwrite(str(img), np.zeros((8, 8, 3), np.uint8))
    return LLMRequest(task="t", system="SYS", user="USER", schema=Answer, images=[img])


def test_structured_output_request_and_parse(monkeypatch, tmp_path):
    bodies: list[dict] = []
    p = provider_with(monkeypatch, [httpx.Response(200, json=completion('{"title": "Rinse", "seconds": null}'))], bodies)
    out = p.generate(request(tmp_path))
    assert out == Answer(title="Rinse", seconds=None)
    body = bodies[0]
    assert body["model"] == "gemini-3.6-flash"
    assert body["response_format"]["type"] == "json_schema" and body["response_format"]["json_schema"]["strict"] is True
    user = body["messages"][1]["content"]
    assert user[0] == {"type": "text", "text": "USER"} and user[1]["image_url"]["url"].startswith("data:image/jpeg;base64,")


def test_schema_rejected_falls_back_to_json_mode_and_repairs(monkeypatch, tmp_path):
    bodies: list[dict] = []
    p = provider_with(monkeypatch, [
        httpx.Response(400, json={"error": {"message": "Invalid JSON schema"}}),
        httpx.Response(200, json=completion('{"title": "Rinse"}')),                      # missing field
        httpx.Response(200, json=completion('```json\n{"title": "Rinse", "seconds": 20}\n```')),
    ], bodies)
    assert p.generate(request(tmp_path)) == Answer(title="Rinse", seconds=20)
    assert bodies[1]["response_format"] == {"type": "json_object"}
    assert "JSON schema" in bodies[1]["messages"][0]["content"]
    assert bodies[2]["messages"][-1]["content"].startswith("That JSON did not match")
    # Once rejected, later calls skip straight to JSON mode: one request, no schema attempt.
    bodies.clear()
    p.queue.append(httpx.Response(200, json=completion('{"title": "Dry", "seconds": null}')))
    assert p.generate(request(tmp_path)).title == "Dry"
    assert len(bodies) == 1 and bodies[0]["response_format"] == {"type": "json_object"}


def test_missing_key_is_a_clear_error(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(LLMError, match="GEMINI_API_KEY"):
        make_provider(Config.load(overrides={"llm": {"provider": "gemini"}}))


def test_auto_picks_gemini_when_only_its_key_is_set(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    p = make_provider(Config.load(overrides={"llm": {"provider": "auto"}}))
    assert p.label == "gemini:gemini-3.6-flash"


def test_replay_serves_cache_and_refuses_misses(monkeypatch, tmp_path):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)  # replay never needs a key
    replay = make_provider(Config.load(overrides={"llm": {"provider": "gemini", "replay": True}}))
    assert isinstance(replay, ReplayProvider) and replay.label == "gemini:gemini-3.6-flash"
    req = LLMRequest(task="t", system="S", user="U", schema=Answer)
    with pytest.raises(LLMError, match="replay mode"):
        CachedLLM(replay, tmp_path).call(req)

    class Live(ReplayProvider):
        def generate(self, request):
            return Answer(title="live", seconds=1)

    recorded, key = CachedLLM(Live("gemini", "gemini-3.6-flash"), tmp_path).call(req)
    replayed, key2 = CachedLLM(replay, tmp_path).call(req)
    assert key2 == key and replayed == recorded


def test_overloaded_model_falls_back_to_next(monkeypatch, tmp_path):
    bodies: list[dict] = []
    p = provider_with(monkeypatch, [
        httpx.Response(503, json={"error": {"message": "overloaded"}}),
        httpx.Response(200, json=completion('{"title": "Rinse", "seconds": null}')),
    ], bodies)
    assert p.generate(request(tmp_path)).title == "Rinse"
    assert [b["model"] for b in bodies] == ["gemini-3.6-flash", "gemini-3.5-flash"]
    assert p.served_by == "gemini-3.5-flash" and p.label == "gemini:gemini-3.6-flash"

    bodies.clear()
    p.queue.extend([httpx.Response(503, json={})] * 4)
    with pytest.raises(LLMError, match="all models unavailable"):
        p.generate(request(tmp_path))
    assert len(bodies) == 4
