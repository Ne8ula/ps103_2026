"""M7: FastAPI data endpoints, exercised against a toy stage registry (the real stages are not needed)."""

from __future__ import annotations

import json
import os
import sys
import threading
import time
import types

import pytest
from fastapi.testclient import TestClient

from tutorialgen import runner
from tutorialgen.api import ApiSettings, create_app
from tutorialgen.project import Project
from tutorialgen.schemas import Question, QuestionSet, Step, StepList, VideoMeta
from tutorialgen.stages import StageSpec


@pytest.fixture
def toy(monkeypatch):
    """Three tiny stages: a -> b -> c. ``gate`` blocks b until set; ``fail`` makes c raise."""
    state = {"calls": {"a": 0, "b": 0, "c": 0}, "gate": threading.Event(), "fail": False}
    state["gate"].set()

    def run_a(ctx):
        state["calls"]["a"] += 1
        ctx.project.write_json("a/out.json", {"v": 1})

    def run_b(ctx):
        state["calls"]["b"] += 1
        assert state["gate"].wait(10)
        ctx.project.write_json("b/out.json", {"n": state["calls"]["b"]})

    def run_c(ctx):
        state["calls"]["c"] += 1
        if state["fail"]:
            raise ValueError("toy failure")
        ctx.project.write_json("c/out.json", {"ok": True})

    for name, fn in [("a", run_a), ("b", run_b), ("c", run_c)]:
        monkeypatch.setitem(sys.modules, f"tutorialgen.stages.toy_{name}", types.SimpleNamespace(run=fn))
    specs = {
        "a": StageSpec("a", "toy_a", (), ("a/out.json",), (), description="first"),
        "b": StageSpec("b", "toy_b", ("a",), ("b/out.json",), (), inputs=("inputs/answers.json",), gpu=True),
        "c": StageSpec("c", "toy_c", ("b",), ("c/out.json",), ()),
    }
    monkeypatch.setattr(runner, "STAGES", specs)
    monkeypatch.setattr(runner, "ORDER", list(specs))
    yield state
    state["gate"].set()


@pytest.fixture
def client(toy):
    with TestClient(create_app(ApiSettings(max_video_mb=1, max_document_mb=1))) as c:
        yield c


def new_project(client, **body) -> str:
    r = client.post("/projects", json={"name": "Demo Project", **body})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def wait_run(client, pid: str, run_id: str, timeout: float = 10) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        run = client.get(f"/projects/{pid}/runs/{run_id}").json()
        if run["status"] in ("done", "failed"):
            return run
        time.sleep(0.02)
    raise AssertionError(f"run {run_id} did not finish: {run}")


def test_health_stages_and_docs(client):
    assert client.get("/health").json()["status"] == "ok"
    stages = client.get("/stages").json()
    assert [s["name"] for s in stages] == ["a", "b", "c"]
    assert stages[1]["requires"] == ["a"] and stages[1]["gpu"] is True
    assert client.get("/openapi.json").status_code == 200 and client.get("/docs").status_code == 200


def test_project_crud(client, isolated_home):
    pid = new_project(client, video_url="https://youtu.be/abc")
    detail = client.get(f"/projects/{pid}").json()
    assert detail["name"] == "Demo Project" and detail["video"] == {"source": "https://youtu.be/abc", "kind": "url"}
    assert detail["active_run_id"] is None
    listed = client.get("/projects").json()
    assert [p["id"] for p in listed] == [pid] and listed[0]["documents"] == 0
    assert client.post("/projects", json={"name": "x", "video_url": "/etc/passwd"}).status_code == 422
    assert client.post("/projects", json={}).status_code == 422
    assert client.get("/projects/nope-123").status_code == 404
    assert client.get("/projects/..").status_code == 404
    assert client.delete(f"/projects/{pid}").status_code == 204
    assert client.get(f"/projects/{pid}").status_code == 404 and not (isolated_home / pid).exists()


def test_video_by_url_and_upload(client):
    pid = new_project(client)
    r = client.put(f"/projects/{pid}/video", json={"url": "https://www.youtube.com/watch?v=x"})
    assert r.status_code == 200 and r.json()["video"]["kind"] == "url"
    assert client.put(f"/projects/{pid}/video", json={"url": "file:///etc/passwd"}).status_code == 422
    assert client.put(f"/projects/{pid}/video", json={"nope": 1}).status_code == 422

    r = client.put(f"/projects/{pid}/video", files={"file": ("../../clip.MOV", b"\x00fakevideo", "video/quicktime")})
    assert r.status_code == 200, r.text
    assert r.json()["video"] == {"source": "inputs/video.mov", "kind": "file"}
    p = Project.load(pid)
    assert p.path("inputs/video.mov").read_bytes() == b"\x00fakevideo"
    assert not any(p.path("api/uploads").iterdir())  # temp upload removed

    assert client.put(f"/projects/{pid}/video", files={"file": ("x.exe", b"MZ", "application/octet-stream")}).status_code == 415
    big = b"0" * (1024 * 1024 + 10)
    assert client.put(f"/projects/{pid}/video", files={"file": ("big.mp4", big, "video/mp4")}).status_code == 413
    assert client.put(f"/projects/{pid}/video", files={"other": ("a.mp4", b"x", "video/mp4")}).status_code == 422


def test_document_upload(client):
    pid = new_project(client)
    r = client.post(f"/projects/{pid}/documents", files={"file": ("Food Code.PDF", b"%PDF-1.4 fake", "application/pdf")})
    assert r.status_code == 201, r.text
    doc = r.json()
    assert doc["id"] == "d01" and doc["name"] == "Food Code.PDF" and doc["path"].endswith(".pdf")
    # Identical content is not attached twice.
    again = client.post(f"/projects/{pid}/documents", files={"file": ("copy.pdf", b"%PDF-1.4 fake", "application/pdf")})
    assert again.status_code == 200 and again.json()["id"] == "d01"
    r = client.post(f"/projects/{pid}/documents", data={"name": "Hand SOP"},
                    files={"file": ("sop.md", b"# Wash for 20 s", "text/markdown")})
    assert r.status_code == 201 and r.json()["name"] == "Hand SOP"
    assert [d["id"] for d in client.get(f"/projects/{pid}/documents").json()] == ["d01", "d02"]
    assert client.post(f"/projects/{pid}/documents", files={"file": ("x.html", b"<p>", "text/html")}).status_code == 415
    assert client.post(f"/projects/{pid}/documents", files={"file": ("empty.txt", b"", "text/plain")}).status_code == 400


def test_run_lifecycle_history_and_log(client, toy):
    pid = new_project(client)
    r = client.post(f"/projects/{pid}/runs", json={})
    assert r.status_code == 202 and r.headers["location"].endswith(r.json()["id"])
    run = wait_run(client, pid, r.json()["id"])
    assert run["status"] == "done" and run["results"] == {"a": "ran", "b": "ran", "c": "ran"} and run["error"] is None
    stages = client.get(f"/projects/{pid}").json()["stages"]
    assert {n: s["status"] for n, s in stages.items()} == {"a": "done", "b": "done", "c": "done"}

    run2 = wait_run(client, pid, client.post(f"/projects/{pid}/runs", json={"until": "b", "force": ["b"]}).json()["id"])
    assert run2["results"] == {"a": "skipped", "b": "ran"}
    history = client.get(f"/projects/{pid}/runs").json()
    assert [h["id"] for h in history] == [run["id"], run2["id"]]

    # The JSONL log survives a restart: a fresh app reads the same history.
    with TestClient(create_app()) as other:
        again = other.get(f"/projects/{pid}/runs").json()
        assert [(h["id"], h["status"]) for h in again] == [(run["id"], "done"), (run2["id"], "done")]
        assert other.get(f"/projects/{pid}/runs/{run['id']}").json()["results"] == run["results"]
    lines = [json.loads(x) for x in Project.load(pid).path("api/runs.jsonl").read_text().splitlines()]
    assert [x["status"] for x in lines if x["id"] == run["id"]] == ["queued", "running", "done"]

    assert client.get(f"/projects/{pid}/runs/r-nope").status_code == 404
    assert client.post(f"/projects/{pid}/runs", json={"stages": ["zzz"]}).status_code == 422
    assert client.post(f"/projects/{pid}/runs", json={"force": ["zzz"]}).status_code == 422


def test_concurrent_run_conflicts_and_busy_project_is_protected(client, toy):
    pid = new_project(client)
    toy["gate"].clear()
    run_id = client.post(f"/projects/{pid}/runs", json={}).json()["id"]
    deadline = time.monotonic() + 5
    while client.get(f"/projects/{pid}/runs/{run_id}").json()["current_stage"] != "b":
        assert time.monotonic() < deadline
        time.sleep(0.02)
    assert client.get(f"/projects/{pid}").json()["active_run_id"] == run_id
    assert client.post(f"/projects/{pid}/runs", json={}).status_code == 409
    assert client.delete(f"/projects/{pid}").status_code == 409
    assert client.put(f"/projects/{pid}/video", json={"url": "https://youtu.be/x"}).status_code == 409
    assert client.post(f"/projects/{pid}/documents", files={"file": ("a.txt", b"x", "text/plain")}).status_code == 409
    toy["gate"].set()
    assert wait_run(client, pid, run_id)["status"] == "done"
    assert client.get(f"/projects/{pid}").json()["active_run_id"] is None
    assert client.post(f"/projects/{pid}/runs", json={"force": True}).status_code == 202


def test_failing_stage_surfaces_error(client, toy):
    pid = new_project(client)
    toy["fail"] = True
    run = wait_run(client, pid, client.post(f"/projects/{pid}/runs").json()["id"])
    assert run["status"] == "failed" and run["failed_stage"] == "c" and "toy failure" in run["error"]
    stage = client.get(f"/projects/{pid}").json()["stages"]["c"]
    assert stage["status"] == "failed" and "toy failure" in stage["error"]
    # The project is free again; a fixed stage succeeds and earlier stages are skipped.
    toy["fail"] = False
    run = wait_run(client, pid, client.post(f"/projects/{pid}/runs").json()["id"])
    assert run["results"] == {"a": "skipped", "b": "skipped", "c": "ran"}


def _step(sid: str, title: str) -> Step:
    return Step(id=sid, index=0, start=0, end=2, title=title, instruction="Do it.", confidence=0.7)


def test_read_endpoints_404_then_200(client):
    pid = new_project(client)
    for name in ["meta", "transcript", "gestures", "candidates", "segments", "steps", "compliance", "questions", "tutorial"]:
        assert client.get(f"/projects/{pid}/{name}").status_code == 404, name
    p = Project.load(pid)
    p.write("ingest/meta.json", VideoMeta(source="https://youtu.be/x", source_kind="url", duration=3, fps=30, width=640,
                                          height=360, frame_count=90, has_audio=False, video_path="ingest/video.mp4"))
    assert client.get(f"/projects/{pid}/meta").json()["frame_count"] == 90

    p.write("draft/steps.json", StepList(revision=0, steps=[_step("s01", "Draft title")]))
    r = client.get(f"/projects/{pid}/steps")
    assert r.headers["x-steps-source"] == "draft" and r.json()["steps"][0]["title"] == "Draft title"
    p.write("refine/steps.json", StepList(revision=1, steps=[_step("s01", "Refined title")]))
    r = client.get(f"/projects/{pid}/steps")
    assert r.headers["x-steps-source"] == "refine" and r.json()["revision"] == 1

    p.write_json("segment/segments.json", {"segments": "not a list"})
    assert client.get(f"/projects/{pid}/segments").status_code == 500


def test_questions_and_answers_flow(client, toy):
    pid = new_project(client)
    assert client.post(f"/projects/{pid}/answers", json={"question_id": "q001", "text": "x"}).status_code == 404
    Project.load(pid).write("questions/questions.json", QuestionSet(round=1, questions=[
        Question(id="q001", step_id="s01", kind="missing_info", text="How long?", why="duration", priority=1, blocking=True),
        Question(id="q002", step_id=None, kind="other", text="Old?", why="x", priority=3, blocking=False, status="answered"),
    ]))
    assert [q["id"] for q in client.get(f"/projects/{pid}/questions").json()["questions"]] == ["q001", "q002"]
    assert [q["id"] for q in client.get(f"/projects/{pid}/questions?status=open").json()["questions"]] == ["q001"]
    assert client.get(f"/projects/{pid}/questions?status=bogus").status_code == 422

    r = client.post(f"/projects/{pid}/answers", json={"question_id": "q001", "text": " 20 seconds "})
    assert r.status_code == 201 and r.json()["text"] == "20 seconds" and "x-run-id" not in r.headers
    assert client.post(f"/projects/{pid}/answers", json={"question_id": "q404", "text": "x"}).status_code == 404
    assert client.post(f"/projects/{pid}/answers", json={"question_id": "q001", "text": ""}).status_code == 422
    assert [a["text"] for a in client.get(f"/projects/{pid}/answers").json()["answers"]] == ["20 seconds"]

    first = wait_run(client, pid, client.post(f"/projects/{pid}/runs").json()["id"])
    assert first["results"] == {"a": "ran", "b": "ran", "c": "ran"}
    # A new answer with ?rerun=true re-runs only the stage reading answers (b) and what is downstream of it.
    r = client.post(f"/projects/{pid}/answers?rerun=true", json={"question_id": "q001", "text": "25 seconds"})
    assert r.status_code == 201
    run = wait_run(client, pid, r.headers["x-run-id"])
    assert run["results"]["a"] == "skipped" and run["results"]["b"] == "ran"


def test_file_download_and_traversal(client, isolated_home):
    pid = new_project(client)
    p = Project.load(pid)
    p.path("render").mkdir()
    p.path("render/tutorial.mp4").write_bytes(bytes(range(256)) * 4)
    p.path("hands").mkdir()
    p.path("hands/frames.jsonl").write_text('{"frame": 0, "t": 0.0, "hands": []}\n')
    (isolated_home / "secret.txt").write_text("top secret")

    r = client.get(f"/projects/{pid}/files/render/tutorial.mp4", headers={"Range": "bytes=10-19"})
    assert r.status_code == 206 and r.content == bytes(range(10, 20)) and r.headers["content-type"] == "video/mp4"
    assert client.get(f"/projects/{pid}/tutorial.mp4").content == bytes(range(256)) * 4
    r = client.get(f"/projects/{pid}/hands")
    assert r.status_code == 200 and r.headers["content-type"].startswith("application/x-ndjson") and '"frame": 0' in r.text
    assert client.get(f"/projects/{pid}/files/project.json").json()["id"] == pid
    assert client.get(f"/projects/{pid}/files/render/missing.png").status_code == 404
    assert client.get(f"/projects/{pid}/files/render").status_code == 404  # directories are not served

    for bad in ["..%2fsecret.txt", "%2e%2e/secret.txt", "%2e%2e%2f%2e%2e%2fetc%2fpasswd", "render/%2e%2e/%2e%2e/secret.txt",
                "%2fetc%2fpasswd", "/etc/passwd", "..%5csecret.txt", "render/..%2F..%2Fsecret.txt"]:
        r = client.get(f"/projects/{pid}/files/{bad}")
        assert r.status_code == 400, (bad, r.status_code)
        assert "top secret" not in r.text and "root:" not in r.text

    # A symlink inside the project that points outside it is refused; one that stays inside is fine.
    os.symlink(isolated_home / "secret.txt", p.path("render/escape.txt"))
    os.symlink(p.path("hands/frames.jsonl"), p.path("render/inside.jsonl"))
    os.symlink(isolated_home, p.path("outside_dir"))
    assert client.get(f"/projects/{pid}/files/render/escape.txt").status_code == 404
    assert client.get(f"/projects/{pid}/files/outside_dir/secret.txt").status_code == 404
    assert client.get(f"/projects/{pid}/files/render/inside.jsonl").status_code == 200

    # Project ids are never treated as paths.
    assert client.get("/projects/%2e%2e/files/secret.txt").status_code == 404
    assert client.get(f"/projects/{pid}%2f..%2f{pid}").status_code == 404
