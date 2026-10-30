"""Stage 0-1 artifacts: ingest, hand landmarks, scene cuts, transcript. Owner: perception workstream."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from .common import Artifact


class VideoMeta(Artifact):
    """ingest/meta.json"""

    source: str = Field(description="original URL or file path")
    source_kind: Literal["url", "file"]
    title: str | None = None
    uploader: str | None = None
    license: str | None = None
    duration: float
    fps: float
    width: int
    height: int
    frame_count: int
    has_audio: bool
    video_path: str = Field(description="normalized video, relative to project root")
    audio_path: str | None = Field(default=None, description="16 kHz mono wav, relative to project root")


class Hand(Artifact):
    handedness: Literal["Left", "Right"]
    score: float
    landmarks: list[list[float]] = Field(description="21 x [x, y, z], x/y normalized to image size")
    world_landmarks: list[list[float]] | None = Field(default=None, description="21 x [x, y, z] metres, hand-centred")


class HandFrame(Artifact):
    """One line of hands/frames.jsonl"""

    frame: int
    t: float
    hands: list[Hand]


class HandsSummary(Artifact):
    """hands/summary.json"""

    model: str
    sample_fps: float
    frames_processed: int
    frames_with_hands: int
    smoothing: str
    device: str
    mirror_handedness: bool | None = Field(default=None, description="True if Left/Right labels were flipped")
    frames_with_two_hands: int | None = None
    elapsed_s: float | None = None


class SceneCut(Artifact):
    t: float
    frame: int
    score: float


class Scenes(Artifact):
    """hands/scenes.json"""

    cuts: list[SceneCut]


class Word(Artifact):
    start: float
    end: float
    word: str
    probability: float | None = None


class TranscriptSegment(Artifact):
    id: int
    start: float
    end: float
    text: str
    words: list[Word] = []


class Transcript(Artifact):
    """transcript/transcript.json — available=False when the video has no audio or no speech."""

    available: bool
    language: str | None = None
    model: str | None = None
    segments: list[TranscriptSegment] = []
