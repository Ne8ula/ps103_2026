"""Background pipeline runs for the API: one active run per project, a small thread pool, a JSONL log.

The manager knows nothing about HTTP. ``dispatch`` is the single seam where a run is executed; today it
calls ``runner.run`` in-process, later it can hand GPU stages to a remote worker.

<project>/api/runs.jsonl    one line per state change of a run; the last line for an id wins
"""

from __future__ import annotations

import logging
import re
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable, Literal

from pydantic import BaseModel, Field

from .. import runner
from ..project import Project, now_iso

log = logging.getLogger("tutorialgen.api")

RUNS_LOG = "api/runs.jsonl"
RunStatus = Literal["queued", "running", "done", "failed"]


class RunRequest(BaseModel):
    stages: list[str] | None = Field(default=None, description="run these stages and their requirements")
    until: str | None = Field(default=None, description="run every stage up to and including this one")
    force: bool | list[str] = Field(default=False, description="true re-runs everything; a list re-runs those stages")


class RunRecord(BaseModel):
    id: str
    project_id: str
    status: RunStatus
    request: RunRequest
    created_at: str
    started_at: str | None = None
    finished_at: str | None = None
    results: dict[str, Literal["ran", "skipped"]] = Field(default={}, description="per-stage outcome, set when the run is done")
    current_stage: str | None = Field(default=None, description="stage running right now, read from the manifest")
    failed_stage: str | None = None
    error: str | None = None


class ProjectBusy(RuntimeError):
    def __init__(self, project_id: str, run_id: str):
        super().__init__(f"project {project_id} already has an active run {run_id}")
        self.run_id = run_id


Dispatch = Callable[[Project, RunRequest], dict[str, str]]


def local_dispatch(project: Project, request: RunRequest) -> dict[str, str]:
    return runner.run(project, stages=request.stages, until=request.until, force=request.force)


class JobManager:
    def __init__(self, max_workers: int = 2, dispatch: Dispatch = local_dispatch):
        self._pool = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="tutorialgen-run")
        self._dispatch = dispatch
        self._lock = threading.Lock()
        self._runs: dict[str, RunRecord] = {}
        self._active: dict[str, str] = {}  # project id -> run id

    # ---- queries ---------------------------------------------------------------------------

    def active_run(self, project_id: str) -> str | None:
        with self._lock:
            return self._active.get(project_id)

    def active_count(self) -> int:
        with self._lock:
            return len(self._active)

    def get(self, project: Project, run_id: str) -> RunRecord | None:
        with self._lock:
            record = self._runs.get(run_id)
        if record is not None and record.project_id == project.id:
            return self._with_progress(project, record)
        return next((r for r in self.history(project) if r.id == run_id), None)

    def history(self, project: Project) -> list[RunRecord]:
        """Every run of the project, oldest first: the persisted log, overlaid with live in-memory state."""
        records: dict[str, RunRecord] = {}
        path = project.path(RUNS_LOG)
        if path.exists():
            for line in path.read_text().splitlines():
                if line.strip():
                    try:
                        r = RunRecord.model_validate_json(line)
                    except ValueError:
                        continue
                    records[r.id] = r
        with self._lock:
            live = {k: v.model_copy() for k, v in self._runs.items() if v.project_id == project.id}
        records.update(live)
        for rid, r in records.items():
            if rid not in live and r.status in ("queued", "running"):
                # Logged as unfinished but unknown to this process: the server stopped mid-run.
                records[rid] = r.model_copy(update={"status": "failed", "error": "interrupted: the server stopped before the run finished"})
        return sorted((self._with_progress(project, r) for r in records.values()), key=lambda r: r.created_at)

    # ---- commands --------------------------------------------------------------------------

    def submit(self, project: Project, request: RunRequest) -> RunRecord:
        with self._lock:
            if busy := self._active.get(project.id):
                raise ProjectBusy(project.id, busy)
            record = RunRecord(id=f"r-{uuid.uuid4().hex[:10]}", project_id=project.id, status="queued",
                               request=request, created_at=now_iso())
            self._runs[record.id] = record
            self._active[project.id] = record.id
        self._persist(project.root, record)
        self._pool.submit(self._execute, project.root, record.id)
        return record.model_copy()

    def shutdown(self, wait: bool = False) -> None:
        self._pool.shutdown(wait=wait, cancel_futures=True)

    # ---- internals -------------------------------------------------------------------------

    def _execute(self, root: Path, run_id: str) -> None:
        record = self._update(root, run_id, status="running", started_at=now_iso())
        try:
            project = Project(root)  # fresh load: sees inputs changed after the run was queued
            results = self._dispatch(project, record.request)
            self._update(root, run_id, status="done", finished_at=now_iso(), results=results)
        except Exception as exc:
            failed = None
            if isinstance(exc, runner.StageFailed):
                if m := re.match(r"stage (\S+) failed", str(exc)):
                    failed = m.group(1)
            else:
                log.exception("run %s crashed", run_id)
            self._update(root, run_id, status="failed", finished_at=now_iso(), failed_stage=failed,
                         error=f"{type(exc).__name__}: {exc}")
        finally:
            with self._lock:
                if self._active.get(record.project_id) == run_id:
                    del self._active[record.project_id]

    def _update(self, root: Path, run_id: str, **changes) -> RunRecord:
        with self._lock:
            record = self._runs[run_id] = self._runs[run_id].model_copy(update=changes)
        self._persist(root, record)
        return record

    def _persist(self, root: Path, record: RunRecord) -> None:
        path = root / RUNS_LOG
        if not root.exists():
            return  # project deleted after the run finished
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock, open(path, "a") as f:
            f.write(record.model_dump_json(exclude={"current_stage"}) + "\n")

    @staticmethod
    def _with_progress(project: Project, record: RunRecord) -> RunRecord:
        if record.status != "running":
            return record
        try:
            stages = Project(project.root).manifest.stages
        except (OSError, ValueError):
            return record
        current = next((n for n, s in stages.items() if s.status == "running"), None)
        return record.model_copy(update={"current_stage": current})
