from __future__ import annotations

from pathlib import Path

import pytest

SAMPLES = Path(__file__).resolve().parents[1] / "samples" / "data"


@pytest.fixture(autouse=True)
def isolated_home(tmp_path, monkeypatch):
    """Every test gets its own projects folder and the fake LLM, never the network."""
    monkeypatch.setenv("TUTORIALGEN_NO_DOTENV", "1")
    monkeypatch.setenv("TUTORIALGEN_HOME", str(tmp_path / "projects"))
    monkeypatch.setenv("TUTORIALGEN_LLM_PROVIDER", "fake")
    monkeypatch.setenv("TUTORIALGEN_EMBEDDINGS_PROVIDER", "hash")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    return tmp_path / "projects"


@pytest.fixture
def sample(request):
    """Path to a downloaded sample (run samples/fetch.py); skips if missing."""

    def get(name: str) -> Path:
        p = SAMPLES / name
        if not p.exists():
            pytest.skip(f"sample {name} not downloaded; run python samples/fetch.py")
        return p

    return get
