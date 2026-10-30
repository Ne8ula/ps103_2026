"""A project is one folder holding inputs, per-stage outputs, an LLM cache and a manifest.

<home>/<project_id>/
    project.json          manifest: inputs + per-stage status
    config.yaml           optional overrides
    inputs/               documents/, answers.json, local video copy
    <stage>/              outputs of each stage
    llm_cache/            one JSON per LLM call, keyed by request hash
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, TypeVar

from pydantic import BaseModel, Field

from .config import Config
from .schemas.common import SCHEMA_VERSION, Artifact

A = TypeVar("A", bound=BaseModel)

DEFAULT_HOME = Path(__file__).resolve().parents[1] / "projects"


def projects_home() -> Path:
    return Path(os.environ.get("TUTORIALGEN_HOME", DEFAULT_HOME))


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()[:16]


class VideoInput(Artifact):
    source: str
    kind: Literal["url", "file"]


class DocumentInput(Artifact):
    id: str
    name: str
    path: str = Field(description="relative to project root")
    sha: str


class StageStatus(Artifact):
    status: Literal["pending", "running", "done", "failed"] = "pending"
    fingerprint: str | None = None
    output_hash: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    error: str | None = None


class Manifest(Artifact):
    schema_version: int = SCHEMA_VERSION
    id: str
    name: str
    created_at: str
    video: VideoInput | None = None
    documents: list[DocumentInput] = []
    stages: dict[str, StageStatus] = {}


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40] or "project"


class Project:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.manifest = Manifest.model_validate_json((self.root / "project.json").read_text())

    # ---- lifecycle -------------------------------------------------------------------------

    @classmethod
    def create(cls, name: str, home: Path | None = None) -> "Project":
        home = Path(home or projects_home())
        pid = f"{_slug(name)}-{uuid.uuid4().hex[:6]}"
        root = home / pid
        (root / "inputs" / "documents").mkdir(parents=True)
        manifest = Manifest(id=pid, name=name, created_at=now_iso())
        (root / "project.json").write_text(manifest.model_dump_json(indent=2))
        return cls(root)

    @classmethod
    def load(cls, ref: str | Path, home: Path | None = None) -> "Project":
        path = Path(ref)
        if not (path / "project.json").exists():
            path = Path(home or projects_home()) / str(ref)
        if not (path / "project.json").exists():
            raise FileNotFoundError(f"no project at {ref}")
        return cls(path)

    @property
    def id(self) -> str:
        return self.manifest.id

    def save_manifest(self) -> None:
        tmp = self.root / "project.json.tmp"
        tmp.write_text(self.manifest.model_dump_json(indent=2))
        tmp.replace(self.root / "project.json")

    def config(self, overrides: dict | None = None) -> Config:
        return Config.load(self.root / "config.yaml", overrides)

    # ---- inputs ----------------------------------------------------------------------------

    def set_video(self, source: str) -> None:
        """Accept a URL or a local file. Local files are copied into inputs/ so the project is self-contained."""
        if re.match(r"^https?://", source):
            self.manifest.video = VideoInput(source=source, kind="url")
        else:
            src = Path(source).expanduser().resolve()
            if not src.exists():
                raise FileNotFoundError(source)
            dest = self.root / "inputs" / f"video{src.suffix.lower()}"
            shutil.copy2(src, dest)
            self.manifest.video = VideoInput(source=str(dest.relative_to(self.root)), kind="file")
        self.save_manifest()

    def add_document(self, path: str | Path, name: str | None = None) -> DocumentInput:
        src = Path(path).expanduser().resolve()
        sha = file_hash(src)
        for doc in self.manifest.documents:
            if doc.sha == sha:
                return doc
        doc_id = f"d{len(self.manifest.documents) + 1:02d}"
        dest = self.root / "inputs" / "documents" / f"{doc_id}-{_slug(src.stem)}{src.suffix.lower()}"
        shutil.copy2(src, dest)
        doc = DocumentInput(id=doc_id, name=name or src.name, path=str(dest.relative_to(self.root)), sha=sha)
        self.manifest.documents.append(doc)
        self.save_manifest()
        return doc

    # ---- artifact IO -----------------------------------------------------------------------

    def path(self, rel: str | Path) -> Path:
        return self.root / rel

    def rel(self, path: Path) -> str:
        return str(Path(path).resolve().relative_to(self.root.resolve()))

    def exists(self, rel: str | Path) -> bool:
        return (self.root / rel).exists()

    def write(self, rel: str | Path, obj: BaseModel) -> Path:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(obj.model_dump_json(indent=2))
        tmp.replace(path)
        return path

    def read(self, rel: str | Path, model: type[A]) -> A:
        return model.model_validate_json((self.root / rel).read_text())

    def write_jsonl(self, rel: str | Path, items: list[BaseModel]) -> Path:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            for item in items:
                f.write(item.model_dump_json() + "\n")
        return path

    def read_jsonl(self, rel: str | Path, model: type[A]) -> list[A]:
        with open(self.root / rel) as f:
            return [model.model_validate_json(line) for line in f if line.strip()]

    def write_json(self, rel: str | Path, data) -> Path:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, default=str))
        return path

    def stage_dir(self, name: str) -> Path:
        d = self.root / name
        d.mkdir(parents=True, exist_ok=True)
        return d

    def hash_paths(self, rels: list[str]) -> str:
        """Hash files (or every file under a directory) so downstream stages can detect changes."""
        h = hashlib.sha256()
        for rel in sorted(rels):
            p = self.root / rel
            files = sorted(x for x in p.rglob("*") if x.is_file()) if p.is_dir() else [p] if p.exists() else []
            for f in files:
                h.update(str(f.relative_to(self.root)).encode())
                h.update(file_hash(f).encode())
        return h.hexdigest()[:16]
