"""Uploader answers are project inputs (inputs/answers.json), not stage outputs."""

from __future__ import annotations

import uuid

from .project import Project, now_iso
from .schemas import Answer, AnswerSet, QuestionSet

ANSWERS = "inputs/answers.json"
QUESTIONS = "questions/questions.json"


def load_answers(project: Project) -> AnswerSet:
    return project.read(ANSWERS, AnswerSet) if project.exists(ANSWERS) else AnswerSet()


def load_questions(project: Project) -> QuestionSet | None:
    return project.read(QUESTIONS, QuestionSet) if project.exists(QUESTIONS) else None


def add_answer(project: Project, question_id: str, text: str) -> Answer:
    questions = load_questions(project)
    if questions is None or question_id not in {q.id for q in questions.questions}:
        raise KeyError(f"unknown question {question_id}")
    answers = load_answers(project)
    # A newer answer to the same question replaces the older one.
    answers.answers = [a for a in answers.answers if a.question_id != question_id]
    answer = Answer(id=f"a-{question_id}-{uuid.uuid4().hex[:6]}", question_id=question_id, text=text.strip(), created_at=now_iso())
    answers.answers.append(answer)
    project.write(ANSWERS, answers)
    return answer
