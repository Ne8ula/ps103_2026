"""Fake LLM handlers for the step tasks: deterministic, structurally realistic, clearly placeholder.

Every generated string starts with ``[fake LLM]`` so placeholder text can never be mistaken for model
output. Handlers only read ``request.context`` (the structured inputs the prompt was rendered from).
"""

from __future__ import annotations

import re

from ..llm import LLMRequest, fake_handler
from .llm_schemas import (DraftStepOutput, MissingItem, PhrasedQuestion, ProposedStep, QuestionsOutput,
                          RefineStepOutput, SegmentWindowOutput)

FAKE = "[fake LLM]"
CUE_WORDS = {"now", "next", "then", "first", "finally", "after", "start", "begin", "lastly", "second", "third"}
DURATION_CUES = re.compile(r"\b(wait|until|seconds?|minutes?|long|leave|let it|rub|scrub|hold|soak|dry)\b", re.I)
QUANTITY_CUES = re.compile(r"\b(some|a bit|little|amount|enough|pour|add|apply|squeeze)\b", re.I)
SETTING_CUES = re.compile(r"\b(set|setting|temperature|warm|hot|cold|speed|power|level|turn)\b", re.I)
VOCAB_TOOLS = ["knife", "screwdriver", "scissors", "brush", "pipette", "wrench", "spoon", "tap", "faucet", "hammer", "pliers", "tweezers"]
VOCAB_MATERIALS = ["soap", "water", "towel", "paper towel", "glue", "tape", "gloves", "flour", "oil", "screw", "solution", "sanitizer"]


def _words(texts: list[str], n: int) -> str:
    words = " ".join(texts).replace('"', "").split()
    return " ".join(words[:n])


def _found(text: str, vocab: list[str]) -> list[str]:
    low = text.lower()
    return [v for v in vocab if re.search(rf"\b{re.escape(v)}s?\b", low)]


@fake_handler("segment_steps")
def fake_segment(req: LLMRequest) -> SegmentWindowOutput:
    ctx = req.context
    intervals = ctx["intervals"]
    groups: list[list[dict]] = []
    for k, iv in enumerate(intervals):
        b = iv["start_boundary"]
        first_word = (iv["speech"][0].split() or [""])[0].lower().strip(",.") if iv["speech"] else ""
        starts = k == 0 or (b["score"] or 0) >= 0.5 or first_word in CUE_WORDS
        if starts or not groups:
            groups.append([iv])
        else:
            groups[-1].append(iv)
    # Respect the minimum step length by folding short groups into their predecessor.
    folded: list[list[dict]] = []
    for g in groups:
        if folded and g[-1]["end"] - g[0]["start"] < ctx["min_step_s"]:
            folded[-1].extend(g)
        else:
            folded.append(g)
    steps = []
    for g in folded:
        speech = [s for iv in g for s in iv["speech"]]
        gestures = [x for iv in g for x in iv["gestures"]]
        if speech:
            summary = f"{FAKE} Narrated: \"{_words(speech, 10)}\""
        elif gestures:
            summary = f"{FAKE} Hands {gestures[0]['activity']}: {gestures[0]['text'][:60]}"
        else:
            summary = f"{FAKE} Activity from {g[0]['start']:.1f}s to {g[-1]['end']:.1f}s"
        b = g[0]["start_boundary"]
        scores = [iv["start_boundary"]["score"] for iv in g if iv["start_boundary"]["score"] is not None]
        conf = sum(scores) / len(scores) if scores else 0.5
        steps.append(ProposedStep(
            start_s=g[0]["start"], end_s=g[-1]["end"], summary=summary,
            rationale=f"{FAKE} starts at {b['id']} ({', '.join(b['reasons']) or 'window edge'}); merges {len(g)} candidate interval(s)",
            confidence=round(min(0.9, max(0.3, conf)), 2),
        ))
    notes = [f"{FAKE} window {ctx['window']['index']}: {len(intervals)} intervals -> {len(steps)} steps"]
    return SegmentWindowOutput(steps=steps, notes=notes)


@fake_handler("draft_step")
def fake_draft(req: LLMRequest) -> DraftStepOutput:
    ctx = req.context
    speech = " ".join(ctx["speech"])
    gestures = ctx["gestures"]
    words = _words(ctx["speech"], 6).rstrip(".,!?")
    if words:
        title = f"{FAKE} {words[0].upper()}{words[1:]}"
        instruction = f"{FAKE} {_words(ctx['speech'], 20).rstrip('.,!?')}."
    else:
        title = f"{FAKE} Step {ctx['index'] + 1}"
        instruction = f"{FAKE} Perform the action shown between {ctx['start']:.1f}s and {ctx['end']:.1f}s."
    details = [f"{FAKE} Hands: {g['text'][:80]}" for g in gestures[:2]]
    missing: list[MissingItem] = []
    if not speech:
        missing.append(MissingItem(field="purpose", description=f"{FAKE} No narration: what is this step for?", blocking=False))
    if DURATION_CUES.search(speech) and not re.search(r"\d", speech):
        missing.append(MissingItem(field="duration", description=f"{FAKE} How long this action lasts is not stated.", blocking=True))
    if QUANTITY_CUES.search(speech) and not re.search(r"\d", speech):
        missing.append(MissingItem(field="quantity", description=f"{FAKE} The amount used is not stated.", blocking=False))
    if SETTING_CUES.search(speech) and not re.search(r"\d", speech):
        missing.append(MissingItem(field="setting", description=f"{FAKE} The exact setting or temperature is not stated.", blocking=True))
    return DraftStepOutput(
        title=title,
        instruction=instruction,
        details=details,
        tools=_found(speech, VOCAB_TOOLS),
        materials=_found(speech, VOCAB_MATERIALS),
        expected_result=f"{FAKE} {ctx['summary'].removeprefix(FAKE).strip()}" if speech else None,
        cautions=[],
        confidence=0.75 if speech else 0.45,
        missing_info=missing,
    )


@fake_handler("refine_step")
def fake_refine(req: LLMRequest) -> RefineStepOutput:
    ctx = req.context
    step = ctx["step"]
    superseded = {a["supersedes"] for a in ctx["answers"] if a["supersedes"]}
    supplied = [f for f in step["user_supplied"] if not any(s in f for s in superseded)]
    resolved: list[str] = []
    details = list(step["details"])
    for a in ctx["answers"]:
        supplied.append(f"{a['answer']} (answer to: {a['question']})")
        details.append(f"{FAKE} Per the uploader: {a['answer']}")
        resolved += [k for k in a["source_refs"] if k in {m["key"] for m in ctx["missing"]} and k not in resolved]
    return RefineStepOutput(
        title=step["title"], instruction=step["instruction"], details=details, tools=step["tools"],
        materials=step["materials"], expected_result=step["expected_result"], cautions=step["cautions"],
        confidence=round(min(1.0, step["confidence"] + 0.1), 2), user_supplied=supplied,
        resolved_missing_keys=resolved, new_missing_info=[],
    )


@fake_handler("questions")
def fake_questions(req: LLMRequest) -> QuestionsOutput:
    out = []
    for gap in req.context["gaps"]:
        where = f"step {gap['step_id']} (\"{gap['step_title']}\")" if gap["step_id"] else "the procedure"
        answer_type, choices, priority = "free_text", [], 1 if gap["blocking"] else 2
        if gap["kind"] == "low_confidence":
            text = f"{FAKE} Is {where} described and cut correctly?"
            answer_type, choices = "choice", ["Yes, it is correct", "It should be split", "It should be merged with a neighbour", "The description is wrong"]
        elif gap["kind"] == "sop_missing_step":
            text = f"{FAKE} The SOP requires: {gap['description']} Is this done in your procedure?"
            answer_type = "yes_no"
        elif gap["kind"] == "sop_conflict":
            text = f"{FAKE} The video and the SOP disagree for {where}: {gap['description']} Which is correct?"
        else:
            text = f"{FAKE} For {where}: {gap['description']} Please specify."
        out.append(PhrasedQuestion(gap_keys=[gap["key"]], text=text, why=f"{FAKE} Needed so learners can follow {where} correctly.",
                                   answer_type=answer_type, choices=choices, priority=priority))
    return QuestionsOutput(questions=out)
