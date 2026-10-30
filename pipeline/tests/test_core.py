"""M0: project storage, config, LLM cache, runner fingerprints, CLI."""

from __future__ import annotations

import sys
import types

import pytest
from pydantic import BaseModel

from tutorialgen import runner
from tutorialgen.answers import add_answer, load_answers
from tutorialgen.cli import main
from tutorialgen.config import Config
from tutorialgen.llm import CachedLLM, LLMRequest, fake_handler, make_provider
from tutorialgen.llm.base import LLMError
from tutorialgen.project import Project
from tutorialgen.schemas import Question, QuestionSet, Step, StepList
from tutorialgen.stages import ORDER, STAGES, StageSpec


def test_project_create_load_and_inputs(tmp_path):
    p = Project.create("Hand Washing Demo")
    assert p.id.startswith("hand-washing-demo-")
    video = tmp_path / "clip.MP4"
    video.write_bytes(b"x")
    p.set_video(str(video))
    assert p.manifest.video.kind == "file" and p.exists(p.manifest.video.source)
    doc = tmp_path / "sop.txt"
    doc.write_text("Wash hands for 20 seconds.")
    d1 = p.add_document(doc)
    assert p.add_document(doc).id == d1.id  # same content is not added twice
    reloaded = Project.load(p.id)
    assert reloaded.manifest.documents[0].name == "sop.txt"

    p.set_video("https://www.youtube.com/watch?v=abc")
    assert Project.load(p.id).manifest.video.kind == "url"


def test_artifact_roundtrip_and_schema_rejects_unknown_fields():
    p = Project.create("rt")
    steps = StepList(revision=0, steps=[Step(id="s01", index=0, start=0, end=2.5, title="Wet hands",
                                             instruction="Wet your hands with clean running water.", confidence=0.8)])
    p.write("draft/steps.json", steps)
    assert p.read("draft/steps.json", StepList) == steps
    with pytest.raises(Exception):
        Step.model_validate({**steps.steps[0].model_dump(), "surprise": 1})


def test_config_layers(tmp_path, monkeypatch):
    p = Project.create("cfg")
    (p.root / "config.yaml").write_text("llm:\n  model: other-model\nperception:\n  sample_fps: 10\n")
    cfg = p.config()
    assert cfg.raw("llm")["model"] == "other-model"
    assert cfg.raw("llm")["provider"] == "fake"  # env from conftest wins over defaults
    assert cfg.raw("perception") == {"sample_fps": 10}
    assert cfg.fingerprint("llm") != Config.load().fingerprint("llm")


class Echo(BaseModel):
    text: str


@fake_handler("test_echo")
def _echo(req):
    return Echo(text=req.context["say"])


def test_fake_provider_and_cache(tmp_path):
    provider = make_provider(Config.load())
    assert provider.label == "fake:fake"
    llm = CachedLLM(provider, tmp_path / "cache")
    req = LLMRequest(task="test_echo", system="s", user="u", schema=Echo, context={"say": "hi"})
    out, key = llm.call(req)
    assert out.text == "hi" and (tmp_path / "cache" / f"{key}.json").exists()
    # Cached: a different context with the same prompt returns the cached answer.
    out2, key2 = llm.call(LLMRequest(task="test_echo", system="s", user="u", schema=Echo, context={"say": "bye"}))
    assert key2 == key and out2.text == "hi"
    with pytest.raises(LLMError):
        llm.call(LLMRequest(task="no_such_task", system="s", user="u", schema=Echo))


@pytest.fixture
def toy_stages(monkeypatch):
    """Replace the registry with two tiny stages that count their runs."""
    calls = {"a": 0, "b": 0}

    def run_a(ctx):
        calls["a"] += 1
        ctx.project.write_json("a/out.json", {"v": ctx.config.raw("toy").get("v", 1)})

    def run_b(ctx):
        calls["b"] += 1
        ctx.project.write_json("b/out.json", {"n": calls["b"]})

    monkeypatch.setitem(sys.modules, "tutorialgen.stages.toy_a", types.SimpleNamespace(run=run_a))
    monkeypatch.setitem(sys.modules, "tutorialgen.stages.toy_b", types.SimpleNamespace(run=run_b))
    specs = {
        "a": StageSpec("a", "toy_a", (), ("a/out.json",), ("toy",)),
        "b": StageSpec("b", "toy_b", ("a",), ("b/out.json",), (), inputs=("inputs/answers.json",)),
    }
    monkeypatch.setattr(runner, "STAGES", specs)
    monkeypatch.setattr(runner, "ORDER", list(specs))
    return calls


def test_runner_skips_unchanged_and_reruns_downstream(toy_stages):
    p = Project.create("toy")
    assert runner.run(p) == {"a": "ran", "b": "ran"}
    assert runner.run(p) == {"a": "skipped", "b": "skipped"}
    # A config change in a's section re-runs a; b re-runs only because a's output changed.
    assert runner.run(p, config_overrides={"toy": {"v": 2}}) == {"a": "ran", "b": "ran"}
    # Same output from a again -> b is skipped.
    assert runner.run(p, config_overrides={"toy": {"v": 2}}, force=["a"]) == {"a": "ran", "b": "skipped"}
    # A new input file for b re-runs only b.
    p.write_json("inputs/answers.json", {"answers": []})
    assert runner.run(p, config_overrides={"toy": {"v": 2}}) == {"a": "skipped", "b": "ran"}
    assert toy_stages == {"a": 3, "b": 3}


def test_runner_records_failure():
    p = Project.create("fail")
    with pytest.raises(runner.StageFailed):
        runner.run(p, stages=["ingest"])
    assert p.manifest.stages["ingest"].status == "failed"


def test_registry_is_consistent():
    for spec in STAGES.values():
        for req in spec.requires:
            assert ORDER.index(req) < ORDER.index(spec.name), f"{spec.name} requires later stage {req}"
    assert runner.closure(["segment"]) == ["ingest", "perception", "transcribe", "gestures", "candidates", "segment"]


def test_answers_replace_previous(tmp_path):
    p = Project.create("ans")
    with pytest.raises(KeyError):
        add_answer(p, "q001", "x")
    p.write("questions/questions.json", QuestionSet(round=1, questions=[
        Question(id="q001", step_id="s01", kind="missing_info", text="How long?", why="duration unknown", priority=1, blocking=True)]))
    add_answer(p, "q001", "20 seconds")
    add_answer(p, "q001", " 25 seconds ")
    answers = load_answers(p).answers
    assert len(answers) == 1 and answers[0].text == "25 seconds"


def test_cli_new_and_status(capsys, tmp_path):
    doc = tmp_path / "sop.md"
    doc.write_text("# SOP\nWash hands.")
    main(["new", "demo", "--video", "https://youtu.be/x", "--doc", str(doc)])
    pid = capsys.readouterr().out.strip()
    main(["status", pid])
    out = capsys.readouterr().out
    assert "https://youtu.be/x" in out and "sop.md" in out and "render" in out
