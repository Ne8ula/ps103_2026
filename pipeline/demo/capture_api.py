"""Record a real expert session against the tutorialgen API, for the mock studio to replay.

Copies a finished project into a scratch TUTORIALGEN_HOME, then drives the FastAPI app in-process:
read the generated tutorial, answer some of the open questions with ``?rerun=true``, wait for the
re-run, and read the updated steps and questions. Every request and response is written to
``<out>/api_log.json``; before/after artifacts go next to it.

    python demo/capture_api.py <project_id> <answers.json> <out_dir>

answers.json: [{"question_id": "q003", "text": "..."}, ...]
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import time
from pathlib import Path

PIPELINE = Path(__file__).resolve().parents[1]


def main(project_id: str, answers_path: str, out_dir: str) -> None:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    home = out / "home"
    src = PIPELINE / "projects" / project_id
    dest = home / project_id
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest, ignore=shutil.ignore_patterns("api"))
    os.environ["TUTORIALGEN_HOME"] = str(home)

    from fastapi.testclient import TestClient

    from tutorialgen.api import create_app

    log: list[dict] = []
    client = TestClient(create_app())

    def call(method: str, path: str, body=None, keep: int = 6000) -> dict | list | None:
        t0 = time.monotonic()
        r = client.request(method, path, json=body)
        entry = {"method": method, "path": path, "status": r.status_code, "ms": round((time.monotonic() - t0) * 1000),
                 "request": body, "headers": {k: v for k, v in r.headers.items() if k.startswith("x-") or k == "location"}}
        try:
            data = r.json()
        except ValueError:
            data = None
        text = json.dumps(data)
        entry["response"] = data if len(text) <= keep else {"_truncated": True, "_bytes": len(text), "preview": text[:keep]}
        log.append(entry)
        return data

    pid = project_id
    call("GET", "/health")
    call("GET", f"/projects/{pid}")
    before = {name: call("GET", f"/projects/{pid}/{name}") for name in ("steps", "questions", "compliance")}
    call("GET", f"/projects/{pid}/questions?status=open")

    answers = json.loads(Path(answers_path).read_text())
    for i, a in enumerate(answers):
        # Only the last answer asks for a re-run; that run merges every saved answer at once.
        path = f"/projects/{pid}/answers" + ("?rerun=true" if i == len(answers) - 1 else "")
        r = client.post(path, json=a)
        log.append({"method": "POST", "path": path, "status": r.status_code, "request": a, "response": r.json(),
                    "headers": {k: v for k, v in r.headers.items() if k.startswith("x-")}})
    run_id = r.headers.get("x-run-id")
    polls = 0
    while (rec := client.get(f"/projects/{pid}/runs/{run_id}").json())["status"] in ("queued", "running"):
        polls += 1
        time.sleep(2)
    log.append({"method": "GET", "path": f"/projects/{pid}/runs/{run_id}", "status": 200, "request": None,
                "response": rec, "headers": {}, "polls": polls})
    if rec["status"] == "failed":
        raise SystemExit(f"run failed: {rec.get('error')}")

    after = {name: call("GET", f"/projects/{pid}/{name}") for name in ("steps", "questions", "compliance")}
    call("GET", f"/projects/{pid}/answers")
    (out / "api_log.json").write_text(json.dumps(log, indent=1))
    (out / "before.json").write_text(json.dumps(before))
    (out / "after.json").write_text(json.dumps(after))
    print(f"{len(log)} calls recorded; project copy at {dest}")


if __name__ == "__main__":
    main(*sys.argv[1:4])
