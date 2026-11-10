"""Edit stage: units, rules, guards, the stage on a synthetic project, and render playing an edit list."""

from __future__ import annotations

import logging

import av
import numpy as np
import pytest
from test_render import FAST, FPS, decode, make_project
from test_render import render as render_project

from tutorialgen.edit import EditConfig, apply_rules, build_units
from tutorialgen.edit.units import Line, Unit
from tutorialgen.llm import CachedLLM, make_provider
from tutorialgen.schemas import EditDecisionList, EditUnit, Step, StepEdit, Transcript, TranscriptSegment, Word
from tutorialgen.stages import StageContext
from tutorialgen.stages import edit as edit_stage

NO_MOTION = (np.arange(0, 60, 0.25), np.zeros(240))


def step(start=0.0, end=20.0, text="Fit the plate.", **kw) -> Step:
    return Step(id="s01", index=0, start=start, end=end, title="Fit the plate", instruction=text, confidence=0.9, **kw)


def test_units_cover_the_step_and_pad_lines():
    lines = [Line(2.0, 3.0, "first"), Line(3.2, 4.0, "close to the first"), Line(10.0, 11.0, "later")]
    units = build_units("s01", 0.0, 20.0, lines, [], NO_MOTION, absorb_gap_s=0.4, pad_s=0.12)
    assert units[0].start == 0.0 and units[-1].end == 20.0
    for a, b in zip(units, units[1:]):
        assert a.end == pytest.approx(b.start)
    assert [u.kind for u in units] == ["gap", "speech", "speech", "gap", "speech", "gap"]
    speech = [u for u in units if u.kind == "speech"]
    assert speech[0].start == pytest.approx(1.88) and speech[-1].end == pytest.approx(11.12)  # padded into gaps
    assert speech[0].end == pytest.approx(3.2)                                                # tiny gap absorbed


def unit(uid, a, b, kind="gap", text=None, hands=0.0, motion=0.0):
    from tutorialgen.steps.guards import numbers_in
    return Unit(id=uid, start=a, end=b, kind=kind, text=text, hands=hands, motion=motion,
                numbers=numbers_in(text) if text else set())


def test_rules_cut_idle_speed_long_work_and_handle_asides():
    cfg = EditConfig()
    units = [unit("u1", 0, 5),                                        # nothing happens -> cut
             unit("u2", 5, 20, hands=0.8, motion=0.6),                 # 15 s of silent work -> speed
             unit("u3", 20, 23, "speech", "this was on sale", hands=0.0),            # aside, idle -> cut
             unit("u4", 23, 26, "speech", "my dog says hi", hands=0.9, motion=0.5),  # aside while working -> speed
             unit("u5", 26, 28, "speech", "tighten it snug", hands=0.9),             # task -> keep
             unit("u6", 28, 28.8)]                                     # short pause -> keep
    labels = {"u3": ("aside", "sale"), "u4": ("aside", "chat"), "u5": ("task", "")}
    out = {e.id: e for e in apply_rules(step(0, 28.8), units, labels, cfg)}
    assert [out[k].action for k in ("u1", "u2", "u3", "u4", "u5", "u6")] == ["cut", "speed", "cut", "speed", "keep", "keep"]
    assert out["u1"].label == "idle" and out["u1"].label_source == "rule" and out["u5"].label_source == "llm"
    assert out["u2"].speed == 3.0


def test_guards_keep_stated_numbers_and_a_minimum_length():
    cfg = EditConfig(min_step_s=3.0)
    units = [unit("u1", 0, 4, "speech", "open them up to one-eighth", hands=0.0),
             unit("u2", 4, 8, "speech", "nice weather today", hands=0.0)]
    labels = {"u1": ("aside", ""), "u2": ("aside", "")}
    out = apply_rules(step(0, 8, "Open the holes to 1/8 inch."), units, labels, cfg)
    assert out[0].action == "keep" and "8" in out[0].restored_by
    assert out[1].action == "cut"

    spoken = apply_rules(step(0, 8, "Wait."), [unit("u1", 0, 4, "speech", "what is it, X 163?")], {"u1": ("aside", "")}, cfg)
    assert spoken[0].action == "keep" and spoken[0].restored_by == "says a number"

    units[0] = unit("u1", 0, 4, "speech", "open them up wide", hands=0.0)
    out = apply_rules(step(0, 8, "Wait."), units, labels, cfg)          # everything cut -> restore to >= 3 s
    assert sum(e.end - e.start for e in out if e.action == "keep") >= 3.0
    assert any(e.restored_by and "minimum" in e.restored_by for e in out)


def test_stage_writes_a_contiguous_edit_list():
    p = make_project()
    words = [Word(start=0.2, end=0.5, word=" turn"), Word(start=0.5, end=0.8, word=" off"), Word(start=0.8, end=1.0, word=" tap."),
             Word(start=2.0, end=2.4, word=" lather"), Word(start=2.4, end=2.8, word=" well.")]
    p.write("transcript/transcript.json", Transcript(available=True, language="en", segments=[
        TranscriptSegment(id=0, start=0.2, end=1.0, text="turn off tap.", words=words[:3]),
        TranscriptSegment(id=1, start=2.0, end=2.8, text="lather well.", words=words[3:])]))
    config = p.config({"edit": {"min_cut_s": 0.3, "speed_after_s": 0.6, "min_step_s": 0.3}})
    ctx = StageContext(project=p, config=config, llm=CachedLLM(make_provider(config), p.path("llm_cache")),
                       log=logging.getLogger("test"))
    edit_stage.run(ctx)
    edl = p.read("edit/edl.json", EditDecisionList)
    assert edl.enabled and [e.step_id for e in edl.steps] == ["s01", "s02"] and edl.llm_calls
    for e in edl.steps:
        assert e.units[0].start == pytest.approx(0.0 if e.step_id == "s01" else 1.5)
        for a, b in zip(e.units, e.units[1:]):
            assert a.end == pytest.approx(b.start)
        assert 0 < e.output_s <= e.source_s + 1e-6
    assert {u.label_source for e in edl.steps for u in e.units} >= {"llm", "rule"}

    p2 = make_project()
    ctx2 = StageContext(project=p2, config=p2.config({"edit": {"enabled": False}}), llm=None, log=logging.getLogger("test"))
    edit_stage.run(ctx2)
    off = p2.read("edit/edl.json", EditDecisionList)
    assert not off.enabled and off.output_s == pytest.approx(off.source_s)


def test_render_plays_the_edit_list():
    p = make_project()

    def u(uid, a, b, action, speed=1.0):
        return EditUnit(id=uid, start=a, end=b, kind="gap", hands=1, motion=1, label="task", label_source="rule",
                        action=action, speed=speed, reason="test")

    p.write("edit/edl.json", EditDecisionList(version="t", enabled=True, source_s=3.0, output_s=1.5, steps=[
        StepEdit(step_id="s01", source_s=1.5, output_s=1.0, units=[u("a", 0, 0.5, "keep"), u("b", 0.5, 1.0, "cut"), u("c", 1.0, 1.5, "keep")]),
        StepEdit(step_id="s02", source_s=1.5, output_s=0.5, units=[u("d", 1.5, 3.0, "speed", 3.0)])]))
    t = render_project(p)
    # s01 keeps frames 0-7 and 15-21 (15 frames); s02 takes every 3rd frame of 22-44 (8 frames); 4 one-second cards.
    frames = decode(p.path("render/tutorial.mp4"))
    assert abs(len(frames) - (4 * FPS + 15 + 8)) <= 1
    assert abs(len(decode(p.path("render/steps/s02.mp4"))) - 8) <= 1
    with av.open(str(p.path("render/tutorial.mp4"))) as c:
        a, v = c.streams.audio[0], c.streams.video[0]
        assert abs(float(a.duration * a.time_base) - float(v.duration * v.time_base)) < 0.1
    assert t.artifacts["edl"] == "edit/edl.json" and FAST["preset"] == "ultrafast"


def test_label_schema_is_strict_output_compatible():
    from openai.lib._pydantic import to_strict_json_schema

    from tutorialgen.edit.llm import EditLabelsOutput

    schema = to_strict_json_schema(EditLabelsOutput)
    item = schema["$defs"]["LineLabel"]
    assert set(item["required"]) == set(item["properties"]) and item["additionalProperties"] is False
