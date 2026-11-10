"""FastAPI data endpoints: projects, inputs, runs, typed artifacts, questions/answers and files. No UI.

Projects are the same folders the CLI uses (``projects_home()``). Runs execute in a background
``JobManager``; stage-level progress is the manifest (``GET /projects/{id}``).
"""

from __future__ import annotations

import mimetypes
import os
import re
import shutil
import uuid
from contextlib import asynccontextmanager
from pathlib import Path, PurePosixPath

from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, Request, Response, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse
from pydantic import BaseModel, ValidationError
from starlette.datastructures import UploadFile as StarletteUploadFile

from ..config import load_env_files
from .. import __version__, runner
from ..answers import QUESTIONS, add_answer, load_answers
from ..project import DocumentInput, Project, projects_home
from ..schemas import (Answer, AnswerSet, Candidates, ComplianceReport, EditDecisionList, GestureTrack, QuestionSet, Segmentation, StepList,
                       Transcript, Tutorial, VideoMeta)
from .jobs import JobManager, ProjectBusy, RunRecord, RunRequest
from .models import AnswerRequest, CreateProject, Health, ProjectDetail, ProjectSummary, StageInfo, VideoUrl

VIDEO_EXTS = {".mp4", ".mov", ".m4v", ".webm", ".mkv", ".avi", ".mpg", ".mpeg", ".3gp"}
DOC_EXTS = {".pdf", ".docx", ".txt", ".md"}
PROJECT_ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,80}$")
CHUNK = 1 << 20

# name -> (project-relative path, schema); each becomes GET /projects/{id}/<name>
ARTIFACTS: dict[str, tuple[str, type[BaseModel]]] = {
    "meta": ("ingest/meta.json", VideoMeta),
    "transcript": ("transcript/transcript.json", Transcript),
    "gestures": ("gestures/gestures.json", GestureTrack),
    "candidates": ("candidates/candidates.json", Candidates),
    "segments": ("segment/segments.json", Segmentation),
    "compliance": ("compliance/compliance.json", ComplianceReport),
    "tutorial": ("render/tutorial.json", Tutorial),
    "edl": ("edit/edl.json", EditDecisionList),
}
STEPS = ("refine/steps.json", "draft/steps.json")  # preferred first

mimetypes.add_type("application/x-ndjson", ".jsonl")
mimetypes.add_type("text/markdown", ".md")


class ApiSettings(BaseModel):
    max_video_mb: int = 2048
    max_document_mb: int = 100
    workers: int = 2

    @classmethod
    def from_env(cls) -> "ApiSettings":
        env = {"max_video_mb": "TUTORIALGEN_API_MAX_VIDEO_MB", "max_document_mb": "TUTORIALGEN_API_MAX_DOCUMENT_MB",
               "workers": "TUTORIALGEN_API_WORKERS"}
        return cls(**{k: int(os.environ[v]) for k, v in env.items() if v in os.environ})


# ---- helpers -------------------------------------------------------------------------------


def get_project(project_id: str) -> Project:
    root = projects_home() / project_id
    if not PROJECT_ID.match(project_id) or not (root / "project.json").is_file():
        raise HTTPException(404, f"no project {project_id}")
    return Project(root)


def _jobs(request: Request) -> JobManager:
    return request.app.state.jobs


def _settings(request: Request) -> ApiSettings:
    return request.app.state.settings


def _ensure_idle(jobs: JobManager, project: Project) -> None:
    if run_id := jobs.active_run(project.id):
        raise HTTPException(409, f"project {project.id} has an active run {run_id}; wait for it to finish")


def _detail(project: Project, jobs: JobManager) -> ProjectDetail:
    return ProjectDetail(**project.manifest.model_dump(), active_run_id=jobs.active_run(project.id))


def _read(project: Project, rel: str, model: type[BaseModel]):
    if not project.path(rel).is_file():
        raise HTTPException(404, f"{rel} does not exist yet; run the stage that produces it")
    try:
        return project.read(rel, model)
    except ValidationError as exc:
        raise HTTPException(500, f"{rel} does not match the {model.__name__} schema: {exc.error_count()} errors")


def _check_size(request: Request, limit_mb: int) -> None:
    length = request.headers.get("content-length")
    if length and length.isdigit() and int(length) > limit_mb * CHUNK + 64 * 1024:
        raise HTTPException(413, f"upload larger than {limit_mb} MB")


def _safe_name(filename: str | None, allowed: set[str]) -> str:
    name = PurePosixPath((filename or "").replace("\\", "/")).name
    suffix = Path(name).suffix.lower()
    if suffix not in allowed:
        raise HTTPException(415, f"unsupported file type {suffix or '(none)'}; allowed: {', '.join(sorted(allowed))}")
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(name).stem).strip("._") or "upload"
    return f"{stem[:80]}{suffix}"


async def _receive(project: Project, upload: StarletteUploadFile, name: str, limit_mb: int) -> Path:
    """Stream an upload into a private temp folder inside the project; the caller removes it."""
    tmp = project.root / "api" / "uploads" / uuid.uuid4().hex
    tmp.mkdir(parents=True)
    dest, total = tmp / name, 0
    try:
        with open(dest, "wb") as f:
            while block := await upload.read(CHUNK):
                total += len(block)
                if total > limit_mb * CHUNK:
                    raise HTTPException(413, f"upload larger than {limit_mb} MB")
                f.write(block)
    except BaseException:
        shutil.rmtree(tmp, ignore_errors=True)
        raise
    if total == 0:
        shutil.rmtree(tmp, ignore_errors=True)
        raise HTTPException(400, "empty upload")
    return dest


def _safe_file(project: Project, rel: str) -> Path:
    """Resolve a client path inside the project root; refuses traversal, absolute paths and escaping symlinks."""
    norm = rel.replace("\\", "/")
    parts = PurePosixPath(norm).parts
    if not norm or "\x00" in norm or norm.startswith("/") or re.match(r"^[A-Za-z]:", norm) or ".." in parts:
        raise HTTPException(400, "invalid path")
    root = project.root.resolve()
    target = (root / norm).resolve()
    if not target.is_relative_to(root) or not target.is_file():
        raise HTTPException(404, f"no file {rel}")
    return target


def _serve(project: Project, rel: str) -> FileResponse:
    path = _safe_file(project, rel)
    return FileResponse(path, media_type=mimetypes.guess_type(path.name)[0] or "application/octet-stream")


def _validate_run(req: RunRequest) -> None:
    known = runner.STAGES
    names = list(req.stages or []) + ([req.until] if req.until else []) + (req.force if isinstance(req.force, list) else [])
    if unknown := sorted({n for n in names if n not in known}):
        raise HTTPException(422, f"unknown stage(s): {', '.join(unknown)}; known: {', '.join(runner.ORDER)}")


def _start_run(jobs: JobManager, project: Project, req: RunRequest) -> RunRecord:
    try:
        return jobs.submit(project, req)
    except ProjectBusy as exc:
        raise HTTPException(409, str(exc))


VIDEO_BODY = {"requestBody": {"required": True, "content": {
    "application/json": {"schema": VideoUrl.model_json_schema()},
    "multipart/form-data": {"schema": {"type": "object", "required": ["file"],
                                       "properties": {"file": {"type": "string", "format": "binary"}}}},
}}}


# ---- app -----------------------------------------------------------------------------------


def create_app(settings: ApiSettings | None = None, jobs: JobManager | None = None) -> FastAPI:
    load_env_files()
    settings = settings or ApiSettings.from_env()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        yield
        app.state.jobs.shutdown(wait=False)

    app = FastAPI(title="tutorialgen", version=__version__, lifespan=lifespan,
                  description="Data endpoints for the demo-video -> stepwise-tutorial pipeline. No UI.")
    app.state.settings = settings
    app.state.jobs = jobs or JobManager(max_workers=settings.workers)

    # ---- service ---------------------------------------------------------------------------

    @app.get("/health", response_model=Health, tags=["service"])
    def health(request: Request):
        return Health(version=__version__, active_runs=_jobs(request).active_count())

    @app.get("/stages", response_model=list[StageInfo], tags=["service"])
    def stages():
        return [StageInfo(name=s.name, requires=list(s.requires), outputs=list(s.outputs), inputs=list(s.inputs),
                          uses_llm=s.uses_llm, gpu=s.gpu, description=s.description)
                for s in (runner.STAGES[n] for n in runner.ORDER)]

    # ---- projects --------------------------------------------------------------------------

    @app.post("/projects", response_model=ProjectDetail, status_code=201, tags=["projects"])
    def create_project(body: CreateProject, request: Request):
        if body.video_url and not re.match(r"^https?://", body.video_url):
            raise HTTPException(422, "video_url must be an http(s) URL; upload local files with PUT /projects/{id}/video")
        project = Project.create(body.name)
        if body.video_url:
            project.set_video(body.video_url)
        return _detail(project, _jobs(request))

    @app.get("/projects", response_model=list[ProjectSummary], tags=["projects"])
    def list_projects(request: Request):
        home, jobs, out = projects_home(), _jobs(request), []
        for d in sorted(home.iterdir()) if home.is_dir() else []:
            if not PROJECT_ID.match(d.name) or not (d / "project.json").is_file():
                continue
            try:
                m = Project(d).manifest
            except (OSError, ValueError):
                continue
            out.append(ProjectSummary(id=m.id, name=m.name, created_at=m.created_at, video=m.video, documents=len(m.documents),
                                      stages={n: s.status for n, s in m.stages.items()}, active_run_id=jobs.active_run(m.id)))
        return sorted(out, key=lambda s: s.created_at, reverse=True)

    @app.get("/projects/{project_id}", response_model=ProjectDetail, tags=["projects"])
    def get_project_detail(request: Request, project: Project = Depends(get_project)):
        return _detail(project, _jobs(request))

    @app.delete("/projects/{project_id}", status_code=204, tags=["projects"])
    async def delete_project(request: Request, project: Project = Depends(get_project)):
        _ensure_idle(_jobs(request), project)
        await run_in_threadpool(shutil.rmtree, project.root)
        return Response(status_code=204)

    # ---- inputs ----------------------------------------------------------------------------

    @app.put("/projects/{project_id}/video", response_model=ProjectDetail, tags=["inputs"], openapi_extra=VIDEO_BODY,
             summary="Set the video: JSON {url} or multipart file upload")
    async def put_video(request: Request, project: Project = Depends(get_project)):
        jobs = _jobs(request)
        _ensure_idle(jobs, project)
        if request.headers.get("content-type", "").startswith("multipart/form-data"):
            limit = _settings(request).max_video_mb
            _check_size(request, limit)
            async with request.form(max_files=1) as form:
                upload = form.get("file")
                if not isinstance(upload, StarletteUploadFile):
                    raise HTTPException(422, "multipart body needs a 'file' part")
                path = await _receive(project, upload, _safe_name(upload.filename, VIDEO_EXTS), limit)
            try:
                await run_in_threadpool(project.set_video, str(path))
            finally:
                shutil.rmtree(path.parent, ignore_errors=True)
        else:
            try:
                body = VideoUrl.model_validate_json(await request.body())
            except ValidationError as exc:
                raise RequestValidationError(exc.errors())
            if not re.match(r"^https?://", body.url):
                raise HTTPException(422, "url must be http(s); upload local files as multipart 'file'")
            project.set_video(body.url)
        return _detail(project, jobs)

    @app.post("/projects/{project_id}/documents", response_model=DocumentInput, status_code=201, tags=["inputs"],
              summary="Upload an SOP / manual (pdf, docx, txt, md)")
    async def upload_document(request: Request, response: Response, file: UploadFile = File(...),
                              name: str | None = Form(None), project: Project = Depends(get_project)):
        _ensure_idle(_jobs(request), project)
        limit = _settings(request).max_document_mb
        _check_size(request, limit)
        filename = _safe_name(file.filename, DOC_EXTS)
        path = await _receive(project, file, filename, limit)
        before = len(project.manifest.documents)
        try:
            doc = await run_in_threadpool(project.add_document, path, name or PurePosixPath((file.filename or filename).replace("\\", "/")).name)
        finally:
            shutil.rmtree(path.parent, ignore_errors=True)
        if len(project.manifest.documents) == before:
            response.status_code = 200  # identical content was already attached
        return doc

    @app.get("/projects/{project_id}/documents", response_model=list[DocumentInput], tags=["inputs"])
    def list_documents(project: Project = Depends(get_project)):
        return project.manifest.documents

    # ---- runs ------------------------------------------------------------------------------

    @app.post("/projects/{project_id}/runs", response_model=RunRecord, status_code=202, tags=["runs"],
              summary="Start a background run; 409 if one is already active")
    def start_run(request: Request, response: Response, body: RunRequest | None = None,
                  project: Project = Depends(get_project)):
        body = body or RunRequest()
        _validate_run(body)
        record = _start_run(_jobs(request), project, body)
        response.headers["Location"] = f"/projects/{project.id}/runs/{record.id}"
        return record

    @app.get("/projects/{project_id}/runs", response_model=list[RunRecord], tags=["runs"])
    def list_runs(request: Request, project: Project = Depends(get_project)):
        return _jobs(request).history(project)

    @app.get("/projects/{project_id}/runs/{run_id}", response_model=RunRecord, tags=["runs"])
    def get_run(run_id: str, request: Request, project: Project = Depends(get_project)):
        if (record := _jobs(request).get(project, run_id)) is None:
            raise HTTPException(404, f"no run {run_id}")
        return record

    # ---- artifacts -------------------------------------------------------------------------

    def artifact_endpoint(rel: str, model: type[BaseModel]):
        def endpoint(project: Project = Depends(get_project)):
            return _read(project, rel, model)
        return endpoint

    for name, (rel, model) in ARTIFACTS.items():
        app.add_api_route(f"/projects/{{project_id}}/{name}", artifact_endpoint(rel, model), methods=["GET"],
                          response_model=model, tags=["artifacts"], name=f"get_{name}", summary=f"{model.__name__} ({rel})")

    @app.get("/projects/{project_id}/steps", response_model=StepList, tags=["artifacts"],
             summary="refine/steps.json, else draft/steps.json; X-Steps-Source names which")
    def get_steps(response: Response, project: Project = Depends(get_project)):
        for rel in STEPS:
            if project.path(rel).is_file():
                response.headers["X-Steps-Source"] = rel.split("/")[0]
                return _read(project, rel, StepList)
        raise HTTPException(404, "no steps yet; run through 'draft'")

    @app.get("/projects/{project_id}/questions", response_model=QuestionSet, tags=["questions"])
    def get_questions(status: str | None = Query(None, pattern="^(open|answered|dismissed)$"),
                      project: Project = Depends(get_project)):
        qs = _read(project, QUESTIONS, QuestionSet)
        if status:
            qs.questions = [q for q in qs.questions if q.status == status]
        return qs

    @app.post("/projects/{project_id}/answers", response_model=Answer, status_code=201, tags=["questions"],
              summary="Answer a question; ?rerun=true also starts a run (X-Run-Id header)")
    def post_answer(body: AnswerRequest, request: Request, response: Response, rerun: bool = False,
                    project: Project = Depends(get_project)):
        try:
            answer = add_answer(project, body.question_id, body.text)
        except KeyError:
            raise HTTPException(404, f"unknown question {body.question_id}")
        if rerun:
            # The default plan re-runs only what changed: refine and everything downstream of it.
            try:
                response.headers["X-Run-Id"] = _jobs(request).submit(project, RunRequest()).id
            except ProjectBusy as exc:
                response.headers["X-Run-Busy"] = exc.run_id
        return answer

    @app.get("/projects/{project_id}/answers", response_model=AnswerSet, tags=["questions"])
    def get_answers(project: Project = Depends(get_project)):
        return load_answers(project)

    # ---- files -----------------------------------------------------------------------------

    @app.get("/projects/{project_id}/tutorial.mp4", tags=["files"], response_class=FileResponse,
             summary="Rendered tutorial video (supports Range)")
    def get_tutorial_video(project: Project = Depends(get_project)):
        return _serve(project, "render/tutorial.mp4")

    @app.get("/projects/{project_id}/hands", tags=["files"], response_class=FileResponse,
             summary="Per-frame hand landmarks (hands/frames.jsonl, one HandFrame per line)")
    def get_hands(project: Project = Depends(get_project)):
        return _serve(project, "hands/frames.jsonl")

    @app.get("/projects/{project_id}/files/{file_path:path}", tags=["files"], response_class=FileResponse,
             summary="Any file under the project root (supports Range)")
    def get_file(file_path: str, project: Project = Depends(get_project)):
        return _serve(project, file_path)

    return app


__all__ = ["ApiSettings", "create_app"]
