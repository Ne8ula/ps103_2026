"""Provider-neutral LLM interface.

Stages build an ``LLMRequest`` (prompt text + optional images + a pydantic output schema + the
structured ``context`` the prompt was built from) and get back a validated pydantic object. Nothing
in a stage knows which provider answered.
"""

from __future__ import annotations

import base64
import hashlib
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


@dataclass
class LLMRequest(Generic[T]):
    task: str                      # e.g. "segment_steps"; selects the fake handler and names cache entries
    system: str
    user: str
    schema: type[T]
    images: list[Path] = field(default_factory=list)
    context: dict[str, Any] = field(default_factory=dict)  # structured inputs; used by the fake provider, not sent
    prompt_version: str = ""

    def cache_key(self, provider: str, model: str) -> str:
        h = hashlib.sha256()
        for part in (provider, model, self.task, self.prompt_version, self.system, self.user):
            h.update(part.encode())
            h.update(b"\0")
        h.update(json.dumps(self.schema.model_json_schema(), sort_keys=True).encode())
        for img in self.images:
            h.update(hashlib.sha256(Path(img).read_bytes()).digest())
        return f"{self.task}-{h.hexdigest()[:20]}"

    def image_data_urls(self) -> list[str]:
        urls = []
        for img in self.images:
            mime = "image/png" if str(img).lower().endswith(".png") else "image/jpeg"
            urls.append(f"data:{mime};base64,{base64.b64encode(Path(img).read_bytes()).decode()}")
        return urls


class LLMError(RuntimeError):
    pass


class LLMProvider(ABC):
    name: str = "base"

    def __init__(self, model: str):
        self.model = model

    @property
    def label(self) -> str:
        return f"{self.name}:{self.model}"

    @abstractmethod
    def generate(self, request: LLMRequest[T]) -> T: ...
