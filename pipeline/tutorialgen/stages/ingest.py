"""Stage 'ingest'. See tutorialgen.stages.STAGES for its inputs and outputs."""

from __future__ import annotations

from . import StageContext


def run(ctx: StageContext) -> None:
    raise NotImplementedError("stage 'ingest' is implemented in milestone M1")
