"""Configuration: defaults.yaml < project config.yaml < environment.

Each stage owns its own section model and parses it with ``Config.section(name, Model)``, so stage
settings live next to the stage code and this module never needs editing when a stage grows a knob.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
from typing import Any, TypeVar

import yaml
from pydantic import BaseModel

DEFAULTS_PATH = Path(__file__).with_name("defaults.yaml")
M = TypeVar("M", bound=BaseModel)


def _deep_merge(base: dict, override: dict) -> dict:
    out = copy.deepcopy(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = copy.deepcopy(value)
    return out


def _env_overrides() -> dict:
    env: dict[str, Any] = {}
    if provider := os.environ.get("TUTORIALGEN_LLM_PROVIDER"):
        env.setdefault("llm", {})["provider"] = provider
    if model := os.environ.get("TUTORIALGEN_LLM_MODEL"):
        env.setdefault("llm", {})["model"] = model
    if embed := os.environ.get("TUTORIALGEN_EMBEDDINGS_PROVIDER"):
        env.setdefault("embeddings", {})["provider"] = embed
    if device := os.environ.get("TUTORIALGEN_DEVICE"):
        env["device"] = device
    return env


class Config:
    def __init__(self, data: dict):
        self.data = data

    @classmethod
    def load(cls, project_config: Path | None = None, overrides: dict | None = None) -> "Config":
        data = yaml.safe_load(DEFAULTS_PATH.read_text()) or {}
        if project_config and project_config.exists():
            data = _deep_merge(data, yaml.safe_load(project_config.read_text()) or {})
        data = _deep_merge(data, _env_overrides())
        data = _deep_merge(data, overrides or {})
        return cls(data)

    def raw(self, name: str) -> dict:
        return copy.deepcopy(self.data.get(name, {}))

    def section(self, name: str, model: type[M]) -> M:
        return model.model_validate(self.raw(name))

    def fingerprint(self, *names: str) -> str:
        """Stable hash of the named sections, used to decide whether a stage must re-run."""
        payload = json.dumps({n: self.data.get(n) for n in names}, sort_keys=True, default=str)
        return hashlib.sha256(payload.encode()).hexdigest()[:16]

    @property
    def device(self) -> str:
        return self.data.get("device", "cpu")
