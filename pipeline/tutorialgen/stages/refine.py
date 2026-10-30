"""Stage 'refine': merge uploader answers into the steps they affect; every other step is copied untouched.

Reads draft/steps.json, inputs/answers.json (optional) and the previous round's
questions/questions.json (maps answer.question_id -> step / source refs); writes refine/steps.json.

Incremental by design: the previous refine/steps.json is the base as long as it was built on the
current draft (``base_hash``), and only answers not yet in its ``answer_log`` (matched on id AND text,
so a replaced answer counts as new) are applied, as one new revision. If the draft changed, the base
resets to the draft and all answers are re-applied as one round.

Routing an answer to a step:
1. the question's step_id, if that step exists;
2. otherwise the first source ref that names a step ("s03:missing:duration", "c:s03:conflict:d01:4");
3. otherwise the step with the largest keyword overlap with question + answer (at least
   ``min_keyword_overlap`` shared words);
4. otherwise it becomes a procedure-level note (StepList.notes) holding the question and the answer
   verbatim, with no LLM call: it is never silently dropped and never rewritten.
"""

from __future__ import annotations

import json
import re

from pydantic import BaseModel

from ..answers import load_answers, load_questions
from ..llm import LLMRequest
from ..prompts import load_prompt
from ..schemas import Answer, MissingInfo, Question, QuestionSet, Step, StepList, Transcript
from ..schemas.steps import AppliedAnswer, ProcedureNote
from ..steps import fakes  # noqa: F401  (registers the fake handlers)
from ..steps.guards import redact, ungrounded
from ..steps.llm_schemas import RefineStepOutput
from ..steps.upstream import DRAFT, REFINED, TRANSCRIPT, speech_in
from . import StageContext
from .draft import missing_key, to_missing

TASK = "refine_step"
STOP = set("a an the and or of to in on for with is are be it this that do does you your i we at by as from "
           "should how what which when where why not no yes step use used".split())


class RefineConfig(BaseModel):
    min_keyword_overlap: int = 2      # global answers sharing fewer words with every step become procedure notes


def run(ctx: StageContext) -> None:
    cfg = ctx.config.section("refine", RefineConfig)
    project = ctx.project
    draft = project.read(DRAFT, StepList)
    draft_hash = project.hash_paths([DRAFT])

    base = project.read(REFINED, StepList) if project.exists(REFINED) else None
    if base is None or base.base_hash != draft_hash:
        if base is not None:
            ctx.log.info("draft changed since the last refine: re-applying all answers")
        base = StepList(revision=0, steps=[s.model_copy(deep=True) for s in draft.steps], base_hash=draft_hash)

    applied = {(e.answer_id, e.text) for e in base.answer_log}
    new = [a for a in load_answers(project).answers if (a.id, a.text) not in applied]
    if not new:
        project.write(REFINED, base)
        ctx.log.info("refine: no new answers (revision %d)", base.revision)
        return

    questions = {q.id: q for q in (load_questions(project) or QuestionSet(round=0, questions=[])).questions}
    revision = base.revision + 1
    by_step: dict[str, list[tuple[Answer, Question | None]]] = {}
    for a in new:
        q = questions.get(a.question_id)
        sid = route(q, a, base.steps, cfg.min_keyword_overlap)
        if sid is None:
            base.notes.append(ProcedureNote(text=f"Q: {q.text if q else a.question_id} A: {a.text}", question_id=a.question_id,
                                            answer_ids=[a.id]))
            ctx.log.info("answer %s -> procedure note", a.id)
        else:
            by_step.setdefault(sid, []).append((a, q))
        base.answer_log.append(AppliedAnswer(answer_id=a.id, question_id=a.question_id, text=a.text, step_id=sid, revision=revision))

    prompt = load_prompt(TASK)
    transcript = _transcript(project)
    previous = {e.question_id: e.text for e in base.answer_log[: len(base.answer_log) - len(new)]}
    for i, step in enumerate(base.steps):
        if step.id in by_step:
            base.steps[i] = _apply(ctx, prompt, step, by_step[step.id], previous, transcript)
            ctx.log.info("refine: %s updated with %d answer(s)", step.id, len(by_step[step.id]))

    base.revision = revision
    base.applied_answer_ids = list(dict.fromkeys([*base.applied_answer_ids, *(a.id for a in new)]))
    project.write(REFINED, base)


def _transcript(project) -> Transcript:
    return project.read(TRANSCRIPT, Transcript) if project.exists(TRANSCRIPT) else Transcript(available=False)


def _tokens(text: str) -> set[str]:
    text = re.sub(r"\[[^\]]*\]", " ", text)  # bracketed markers such as "[fake LLM]" or "[?]" carry no topic
    return {w for w in re.findall(r"[a-z]{3,}", text.lower()) if w not in STOP}


def route(q: Question | None, a: Answer, steps: list[Step], min_overlap: int) -> str | None:
    ids = {s.id for s in steps}
    if q is not None and q.step_id in ids:
        return q.step_id
    for ref in (q.source_refs if q else []):
        parts = ref.split(":")
        head = parts[1] if parts[0] == "c" and len(parts) > 1 else parts[0]
        if head in ids:
            return head
    words = _tokens(f"{q.text if q else ''} {a.text}")
    best, best_score = None, 0
    for s in steps:
        score = len(words & _tokens(" ".join([s.title, s.instruction, *s.details, *s.tools, *s.materials])))
        if score > best_score:
            best, best_score = s.id, score
    return best if best_score >= min_overlap else None


def _apply(ctx: StageContext, prompt, step: Step, items: list[tuple[Answer, Question | None]], previous: dict[str, str],
           transcript) -> Step:
    missing_lines = [f"{m.key}: {m.field}, {'blocking' if m.blocking else 'not blocking'}, {m.description}" for m in step.missing_info]
    answers_ctx, answer_lines = [], []
    for a, q in items:
        supersedes = previous.get(a.question_id)
        answers_ctx.append({"answer_id": a.id, "question_id": a.question_id, "question": q.text if q else None,
                            "answer": a.text, "source_refs": q.source_refs if q else [], "supersedes": supersedes})
        line = f"- Question: {q.text if q else '(question text unavailable)'}\n  Answer: {a.text}"
        if q and q.source_refs:
            line += f"\n  Raised by: {', '.join(q.source_refs)}"
        if supersedes:
            line += f"\n  Supersedes the earlier answer: {supersedes}"
        answer_lines.append(line)
    shown = step.model_dump(include={"title", "instruction", "details", "tools", "materials", "expected_result", "cautions",
                                     "confidence", "user_supplied"})
    user = prompt.render(step_id=step.id, start=step.start, end=step.end, step=json.dumps(shown, indent=2),
                         missing="\n".join(missing_lines) or "(none)", answers="\n".join(answer_lines))
    request = LLMRequest(task=TASK, system=prompt.system, user=user, schema=RefineStepOutput, prompt_version=prompt.version,
                         context={"step": shown | {"id": step.id}, "missing": [m.model_dump() for m in step.missing_info],
                                  "answers": answers_ctx})
    out, key = ctx.llm.call(request)

    resolved = set(out.resolved_missing_keys)
    taken = {m.key for m in step.missing_info if m.key}
    missing = [m for m in step.missing_info if m.key not in resolved] + to_missing(step.id, out.new_missing_info, taken)
    new = step.model_copy(deep=True)
    new.title, new.instruction = out.title.strip(), out.instruction.strip()
    new.details, new.tools, new.materials, new.cautions = out.details, out.tools, out.materials, out.cautions
    new.expected_result = (out.expected_result or "").strip() or None
    new.user_supplied = out.user_supplied
    new.confidence = round(min(1.0, max(0.0, out.confidence)), 3)

    # Guard: numbers must come from the answers, the step as it was, or the narration of the step.
    evidence = " ".join([*(a.text for a, _ in items), *(q.text for _, q in items if q), step.title, step.instruction, step.expected_result or "",
                         *step.details, *step.tools, *step.materials, *step.cautions, *step.user_supplied,
                         *(s.text for s in speech_in(transcript, step.start, step.end))])
    texts = [new.title, new.instruction, new.expected_result or "", *new.details, *new.tools, *new.materials, *new.cautions,
             *new.user_supplied]
    bad = ungrounded(texts, evidence)
    if bad:
        new.title, new.instruction = redact(new.title, bad), redact(new.instruction, bad)
        new.expected_result = redact(new.expected_result, bad) if new.expected_result else None
        new.details, new.cautions = [redact(x, bad) for x in new.details], [redact(x, bad) for x in new.cautions]
        new.user_supplied = [redact(x, bad) for x in new.user_supplied]
        missing.insert(0, MissingInfo(field="setting", blocking=True, key=missing_key(step.id, "unverified", taken),
                                      description=f"The update stated {', '.join(repr(b) for b in bad)}, which no answer supports; "
                                                  "the value was removed and needs confirming."))
    new.missing_info = sorted(missing, key=lambda m: not m.blocking)
    new.provenance.answer_ids = list(dict.fromkeys([*new.provenance.answer_ids, *(a.id for a, _ in items)]))
    new.provenance.llm_calls = [*new.provenance.llm_calls, key]
    return new
