"""Command-line entry point: ``python -m tutorialgen <command>``."""

from __future__ import annotations

import argparse
import json
import logging
import sys

from . import runner
from .config import load_env_files
from .answers import add_answer, load_questions
from .project import Project
from .stages import ORDER, STAGES


def _project(args) -> Project:
    return Project.load(args.project)


def cmd_new(args):
    project = Project.create(args.name)
    if args.video:
        project.set_video(args.video)
    for doc in args.doc or []:
        project.add_document(doc)
    print(project.id)


def cmd_add_doc(args):
    doc = _project(args).add_document(args.path, args.name)
    print(doc.id)


def cmd_run(args):
    project = _project(args)
    force = True if args.force_all else (args.force or False)
    try:
        results = runner.run(project, stages=args.stage or args.only, until=args.until, force=force, exact=bool(args.only))
    except runner.StageFailed as exc:
        print(exc, file=sys.stderr)
        sys.exit(1)
    for name, outcome in results.items():
        print(f"{name:12s} {outcome}")


def cmd_status(args):
    project = _project(args)
    m = project.manifest
    print(f"{m.id}  {m.name}")
    print(f"video: {m.video.source if m.video else '-'}")
    for d in m.documents:
        print(f"doc {d.id}: {d.name}")
    for name in ORDER:
        st = m.stages.get(name)
        line = f"  {name:12s} {st.status if st else 'pending':8s}"
        if st and st.error:
            line += "  " + st.error.splitlines()[0]
        print(line)


def cmd_questions(args):
    qs = load_questions(_project(args))
    if qs is None:
        print("no questions yet; run the pipeline through 'questions'")
        return
    for q in qs.questions:
        if args.all or q.status == "open":
            flag = "BLOCKING " if q.blocking else ""
            print(f"[{q.id}] P{q.priority} {flag}{q.status} step={q.step_id or '-'}\n    {q.text}\n    why: {q.why}")


def cmd_answer(args):
    answer = add_answer(_project(args), args.question_id, args.text)
    print(f"saved {answer.id}; re-run with: run {args.project} --stage render")


def cmd_show(args):
    project = _project(args)
    print(json.dumps(json.loads(project.path(args.artifact).read_text()), indent=2))


def cmd_serve(args):
    import uvicorn

    from .api import create_app

    uvicorn.run(create_app(), host=args.host, port=args.port, log_level="debug" if args.verbose else "info")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="tutorialgen", description=__doc__)
    p.add_argument("-v", "--verbose", action="store_true")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("new", help="create a project")
    s.add_argument("name")
    s.add_argument("--video", help="URL (YouTube or any yt-dlp source) or local file")
    s.add_argument("--doc", action="append", help="SOP/manual (pdf, docx, txt, md); repeatable")
    s.set_defaults(fn=cmd_new)

    s = sub.add_parser("add-doc", help="attach a compliance manual / SOP")
    s.add_argument("project")
    s.add_argument("path")
    s.add_argument("--name")
    s.set_defaults(fn=cmd_add_doc)

    s = sub.add_parser("run", help="run stages (skips unchanged ones)")
    s.add_argument("project")
    s.add_argument("--stage", action="append", choices=list(STAGES), help="run this stage and its requirements")
    s.add_argument("--only", action="append", choices=list(STAGES),
                   help="run exactly this stage, requirements must already be done (remote workers)")
    s.add_argument("--until", choices=list(STAGES))
    s.add_argument("--force", action="append", choices=list(STAGES), help="re-run even if unchanged")
    s.add_argument("--force-all", action="store_true")
    s.set_defaults(fn=cmd_run)

    s = sub.add_parser("status")
    s.add_argument("project")
    s.set_defaults(fn=cmd_status)

    s = sub.add_parser("questions", help="list questions for the uploader")
    s.add_argument("project")
    s.add_argument("--all", action="store_true")
    s.set_defaults(fn=cmd_questions)

    s = sub.add_parser("answer", help="answer a question")
    s.add_argument("project")
    s.add_argument("question_id")
    s.add_argument("text")
    s.set_defaults(fn=cmd_answer)

    s = sub.add_parser("show", help="print a JSON artifact")
    s.add_argument("project")
    s.add_argument("artifact", help="e.g. refine/steps.json")
    s.set_defaults(fn=cmd_show)

    s = sub.add_parser("serve", help="run the HTTP data endpoints (OpenAPI docs at /docs)")
    s.add_argument("--host", default="127.0.0.1")
    s.add_argument("--port", type=int, default=8000)
    s.set_defaults(fn=cmd_serve)
    return p


def main(argv: list[str] | None = None):
    args = build_parser().parse_args(argv)
    load_env_files()
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    args.fn(args)


if __name__ == "__main__":
    main()
