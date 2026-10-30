"""Stage 'questions': turn gaps in the refined steps into prioritized questions for the uploader.

Reads refine/steps.json, compliance/compliance.json (optional), inputs/answers.json and the previous
questions/questions.json; writes questions/questions.json (QuestionSet) and questions/state.json.

Gaps are collected deterministically, each with a stable key:
  "<step>:missing:<field>[:n]"  missing_info item (key assigned by draft/refine), blocking ones first
  "<step>:low_confidence"       step confidence below ``low_confidence``
  "c:<step|global>:<kind>:<chunk>"  compliance note of kind conflict / missing_step (note ids are
                                ordinal per run, so the key uses step, kind and first cited chunk)
One LLM call phrases, prioritizes and deduplicates them (a question may cover several keys).

Id stability: questions/state.json keeps key -> question id for every key ever seen (rebuilt from the
previous questions.json if missing), so the same gap keeps its id across rounds even when it was
capped out or temporarily disappeared. A question merging keys with different ids takes the lowest.

Answered questions (their answer is in refine's answer_log) are kept with status "answered" and not
re-asked, except a missing_info gap that is still present after its answer was merged: that one is
re-opened under the same id. Low-confidence and compliance gaps cannot be observed to resolve, so an
applied answer closes them. At most ``max_open`` questions are open, by priority.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from pydantic import BaseModel

from ..answers import load_answers, load_questions
from ..llm import LLMRequest
from ..prompts import load_prompt
from ..schemas import ComplianceReport, Question, QuestionSet, StepList
from ..steps import fakes  # noqa: F401  (registers the fake handlers)
from ..steps.llm_schemas import QuestionsOutput
from ..steps.upstream import COMPLIANCE, QUESTIONS, REFINED
from . import StageContext

TASK = "questions"
STATE = "questions/state.json"
KIND_ORDER = {"sop_conflict": 0, "missing_info": 1, "sop_missing_step": 2, "low_confidence": 3}


class QuestionsConfig(BaseModel):
    max_open: int = 8                  # cap on open questions per round
    low_confidence: float = 0.6        # steps below this confidence get a check question
    include_compliance: bool = True


@dataclass
class Gap:
    key: str
    step_id: str | None
    step_title: str | None
    kind: str
    field: str | None
    description: str
    blocking: bool
    order: int


def collect_gaps(steps: StepList, compliance: ComplianceReport | None, cfg: QuestionsConfig) -> list[Gap]:
    gaps: list[Gap] = []
    seen: set[str] = set()

    def add(g: Gap):
        if g.key not in seen:
            seen.add(g.key)
            gaps.append(g)

    for s in steps.steps:
        for n, m in enumerate(s.missing_info):
            add(Gap(m.key or f"{s.id}:missing:{m.field}:{n + 1}", s.id, s.title, "missing_info", m.field, m.description,
                    m.blocking, s.index))
        if s.confidence < cfg.low_confidence:
            add(Gap(f"{s.id}:low_confidence", s.id, s.title, "low_confidence", None,
                    f"Low confidence ({s.confidence:.2f}) that this step is cut and described correctly.", False, s.index))
    if compliance is not None and cfg.include_compliance:
        titles = {s.id: (s.title, s.index) for s in steps.steps}
        notes = [(n, n.step_id or sc.step_id) for sc in compliance.steps for n in sc.notes]
        notes += [(n, n.step_id) for n in compliance.global_notes]
        for note, sid in notes:
            if note.kind not in ("conflict", "missing_step"):
                continue
            cite = note.citations[0]
            where = f" ({cite.doc_name}{f', p. {cite.page}' if cite.page else ''})"
            title, index = titles.get(sid, (None, len(steps.steps)))
            # Note ids are ordinal within a compliance run, so the key uses step, kind and cited chunk instead.
            add(Gap(f"c:{sid or 'global'}:{note.kind}:{cite.chunk_id}", sid if sid in titles else None, title,
                    "sop_conflict" if note.kind == "conflict" else "sop_missing_step", None, note.text + where,
                    note.severity == "critical" or note.kind == "conflict", index))
    return sorted(gaps, key=lambda g: (not g.blocking, KIND_ORDER[g.kind], g.order))


def _load_state(ctx: StageContext, prev: QuestionSet | None) -> dict:
    state = {"key_to_id": {}, "next": 1, "answers_sig": None, "round": 0}
    if ctx.project.exists(STATE):
        state |= json.loads(ctx.project.path(STATE).read_text())
    if prev is not None:
        for q in prev.questions:
            for ref in q.source_refs:
                state["key_to_id"].setdefault(ref, q.id)
        state["round"] = max(state["round"], prev.round)
    nums = [int(q[1:]) for q in state["key_to_id"].values() if q[1:].isdigit()]
    state["next"] = max([state["next"], *(n + 1 for n in nums)])
    return state


def run(ctx: StageContext) -> None:
    cfg = ctx.config.section("questions", QuestionsConfig)
    project = ctx.project
    steps = project.read(REFINED, StepList)
    compliance = project.read(COMPLIANCE, ComplianceReport) if project.exists(COMPLIANCE) else None
    prev = load_questions(project)
    state = _load_state(ctx, prev)
    answers = load_answers(project).answers

    sig = hashlib.sha256(json.dumps(sorted((a.id, a.text) for a in answers)).encode()).hexdigest()[:16]
    round_ = state["round"] + 1 if state["answers_sig"] != sig or state["round"] == 0 else state["round"]
    answered = {e.question_id: e.text for e in steps.answer_log}

    gaps = collect_gaps(steps, compliance, cfg)
    by_key = {g.key: g for g in gaps}
    groups = _phrase(ctx, steps, gaps, answered, state) if gaps else []

    def qid_for(keys: list[str]) -> str:
        known = sorted(state["key_to_id"][k] for k in keys if k in state["key_to_id"])
        qid = known[0] if known else f"q{state['next']:03d}"
        if not known:
            state["next"] += 1
        for k in keys:
            state["key_to_id"][k] = qid
        return qid

    open_qs: list[Question] = []
    asked: set[str] = set()
    for keys, phrased in groups:
        qid = qid_for(keys)
        if qid in asked:  # two groups collapsed onto one id: keep the first
            continue
        member = [by_key[k] for k in keys]
        if qid in answered and not any(g.kind == "missing_info" for g in member):
            continue  # answered; the gap cannot be observed to resolve, so the answer closes it
        blocking = any(g.blocking for g in member)
        step_ids = {g.step_id for g in member}
        why = phrased["why"]
        if qid in answered:
            why = f"Your earlier answer (\"{answered[qid]}\") did not fully resolve this. {why}"
        asked.add(qid)
        open_qs.append(Question(
            id=qid, step_id=step_ids.pop() if len(step_ids) == 1 else None, kind=member[0].kind, text=phrased["text"],
            why=why, answer_type=phrased["answer_type"],
            choices=phrased["choices"] if phrased["answer_type"] == "choice" else [],
            priority=1 if blocking else min(3, max(1, phrased["priority"])), blocking=blocking, status="open", source_refs=keys,
        ))
    open_qs.sort(key=lambda q: (q.priority, not q.blocking, min(by_key[k].order for k in q.source_refs)))
    if len(open_qs) > cfg.max_open:
        ctx.log.info("questions: %d open, capped to %d", len(open_qs), cfg.max_open)
        open_qs = open_qs[: cfg.max_open]

    done = []
    for q in (prev.questions if prev else []):
        if q.id in answered and q.id not in asked:
            done.append(q.model_copy(update={"status": "answered"}))
    state |= {"answers_sig": sig, "round": round_}
    project.write(QUESTIONS, QuestionSet(round=round_, questions=open_qs + done))
    project.write_json(STATE, state)
    ctx.log.info("questions: round %d, %d open, %d answered", round_, len(open_qs), len(done))


def _phrase(ctx: StageContext, steps: StepList, gaps: list[Gap], answered: dict[str, str], state: dict) -> list[tuple[list[str], dict]]:
    """One LLM call -> [(gap keys, phrased question fields)]; every gap ends up in exactly one group."""
    prompt = load_prompt(TASK)
    gap_lines = []
    for g in gaps:
        line = f"{g.key} | {g.step_title or 'whole procedure'} | {g.kind}{f' ({g.field})' if g.field else ''} | " \
               f"{'blocking' if g.blocking else 'not blocking'} | {g.description}"
        qid = state["key_to_id"].get(g.key)
        if qid in answered:
            line += f" | asked before, answer was: \"{answered[qid]}\""
        gap_lines.append(line)
    step_lines = [f"- {s.title} ({s.start:.1f}-{s.end:.1f}s): {s.instruction}" for s in steps.steps]
    request = LLMRequest(
        task=TASK, system=prompt.system, user=prompt.render(steps="\n".join(step_lines), gaps="\n".join(gap_lines)),
        schema=QuestionsOutput, prompt_version=prompt.version,
        context={"gaps": [g.__dict__ | {"previous_answer": answered.get(state["key_to_id"].get(g.key, ""))} for g in gaps]},
    )
    out, _ = ctx.llm.call(request)

    valid = {g.key for g in gaps}
    used: set[str] = set()
    groups = []
    for q in out.questions:
        keys = [k for k in dict.fromkeys(q.gap_keys) if k in valid and k not in used]
        if not keys or not q.text.strip():
            continue
        used.update(keys)
        groups.append((keys, {"text": q.text.strip(), "why": q.why.strip(), "answer_type": q.answer_type,
                              "choices": q.choices, "priority": q.priority}))
    for g in gaps:  # gaps the model skipped still get a plain question
        if g.key not in used:
            where = f"step \"{g.step_title}\"" if g.step_title else "the procedure"
            groups.append(([g.key], {"text": f"For {where}: {g.description}", "why": "Flagged as missing or uncertain.",
                                     "answer_type": "free_text", "choices": [], "priority": 1 if g.blocking else 2}))
    return groups
