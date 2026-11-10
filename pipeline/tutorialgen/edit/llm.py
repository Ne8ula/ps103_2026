"""LLM labelling of spoken lines (strict structured output) and its deterministic stand-in."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from ..llm import LLMRequest, fake_handler

TASK = "edit_units"


class _Out(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LineLabel(_Out):
    unit_id: str = Field(description="one of the given line ids")
    label: Literal["task", "result", "explain", "aside"]
    reason: str = Field(description="a few words")


class EditLabelsOutput(_Out):
    labels: list[LineLabel]


@fake_handler(TASK)
def fake_edit_units(req: LLMRequest) -> EditLabelsOutput:
    """Placeholder: a line spoken while nothing is seen or moving is an aside, everything else is task."""
    out = []
    for u in req.context["units"]:
        aside = u["hands"] < 0.1 and u["motion"] < 0.15
        out.append(LineLabel(unit_id=u["id"], label="aside" if aside else "task",
                             reason="[fake LLM] " + ("nothing on screen" if aside else "spoken while working")))
    return EditLabelsOutput(labels=out)
