"""Runs stages in dependency order, skipping any whose fingerprint has not changed.

fingerprint(stage) = hash(stage name, config sections it reads, output hashes of its requirements,
hashes of the project inputs it reads, LLM provider label if it uses one). A changed upstream output
therefore re-runs everything downstream, and an unchanged one is free.
"""

from __future__ import annotations

import hashlib
import logging
import traceback

from .llm import CachedLLM, LLMSettings, make_provider
from .project import Project, StageStatus, now_iso
from .stages import ORDER, STAGES, StageContext

log = logging.getLogger("tutorialgen")


class StageFailed(RuntimeError):
    pass


def _fingerprint(project: Project, name: str, config, llm_label: str) -> str:
    spec = STAGES[name]
    h = hashlib.sha256(name.encode())
    h.update(config.fingerprint(*spec.config_sections).encode())
    for req in spec.requires:
        h.update((project.manifest.stages.get(req, StageStatus()).output_hash or "").encode())
    h.update(project.hash_paths(list(spec.inputs)).encode())
    if spec.name == "ingest" and project.manifest.video:
        h.update(project.manifest.video.model_dump_json().encode())
    if spec.uses_llm:
        h.update(llm_label.encode())
    return h.hexdigest()[:16]


def closure(targets: list[str]) -> list[str]:
    """Targets plus everything they require, in registry order."""
    needed: set[str] = set()

    def visit(n: str):
        if n in needed:
            return
        needed.add(n)
        for r in STAGES[n].requires:
            visit(r)

    for t in targets:
        visit(t)
    return [n for n in ORDER if n in needed]


def plan(until: str | None = None, only: list[str] | None = None) -> list[str]:
    if only:
        return closure(only)
    if until:
        return ORDER[: ORDER.index(until) + 1]
    return list(ORDER)


def run(project: Project, stages: list[str] | None = None, until: str | None = None,
        force: bool | list[str] = False, config_overrides: dict | None = None) -> dict[str, str]:
    """Run the plan; returns {stage: 'ran' | 'skipped'}. Raises StageFailed on the first failure."""
    config = project.config(config_overrides)
    provider = make_provider(config)
    llm = CachedLLM(provider, project.path("llm_cache"), config.section("llm", LLMSettings).max_images_per_call)
    forced = set(ORDER) if force is True else set(force or [])
    results: dict[str, str] = {}

    for name in plan(until, stages):
        spec = STAGES[name]
        fp = _fingerprint(project, name, config, provider.label)
        status = project.manifest.stages.get(name, StageStatus())
        outputs_present = all(project.exists(o) for o in spec.outputs if not o.endswith(".mp4"))
        if status.status == "done" and status.fingerprint == fp and outputs_present and name not in forced:
            results[name] = "skipped"
            continue

        log.info("stage %s: running", name)
        project.manifest.stages[name] = StageStatus(status="running", fingerprint=fp, started_at=now_iso())
        project.save_manifest()
        ctx = StageContext(project=project, config=config, llm=llm, log=logging.getLogger(f"tutorialgen.{name}"))
        try:
            spec.load()(ctx)
        except Exception as exc:
            project.manifest.stages[name] = StageStatus(
                status="failed", fingerprint=fp, started_at=project.manifest.stages[name].started_at,
                finished_at=now_iso(), error=f"{type(exc).__name__}: {exc}\n{traceback.format_exc(limit=5)}",
            )
            project.save_manifest()
            raise StageFailed(f"stage {name} failed: {exc}") from exc

        project.manifest.stages[name] = StageStatus(
            status="done", fingerprint=fp, output_hash=project.hash_paths(list(spec.outputs)),
            started_at=project.manifest.stages[name].started_at, finished_at=now_iso(),
        )
        project.save_manifest()
        results[name] = "ran"
    return results
