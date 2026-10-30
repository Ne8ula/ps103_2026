"""Typed contracts for every stage artifact. Each module has one owning workstream; others only read it."""

from .common import SCHEMA_VERSION, Artifact, Provenance, TimeRange
from .compliance import Citation, ComplianceNote, ComplianceReport, DocChunk, DocIndex, DocumentInfo, SopProcedureStep, StepCompliance
from .gestures import ActivitySample, BoundaryCandidate, Candidates, FingerState, GestureKeyframe, GestureTrack, HandDescription, Trajectory
from .media import Hand, HandFrame, HandsSummary, SceneCut, Scenes, Transcript, TranscriptSegment, VideoMeta, Word
from .steps import AppliedAnswer, Answer, AnswerSet, MissingInfo, ProcedureNote, Question, QuestionSet, Segmentation, Step, StepList, StepSegment
from .tutorial import Tutorial, TutorialStep

__all__ = [name for name in dir() if not name.startswith("_")]
