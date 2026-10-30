"""Stage 'transcribe': faster-whisper over ingest/audio.wav with word timestamps and VAD.

Writes transcript/transcript.json; ``available=False`` when there is no audio track or no speech.
"""

from __future__ import annotations

import time
import wave
from pathlib import Path

import numpy as np
from pydantic import BaseModel, ConfigDict, Field

from ..schemas.media import Transcript, TranscriptSegment, VideoMeta, Word
from . import StageContext


class TranscribeSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model: str | None = Field(None, description='faster-whisper size or path; None = "base" on cpu, "small" on cuda')
    compute_type: str | None = Field(None, description="None = int8 on cpu, float16 on cuda")
    language: str | None = Field(None, description="None = auto-detect")
    beam_size: int = 5
    vad_filter: bool = True
    word_timestamps: bool = True
    cpu_threads: int = 4
    min_language_probability: float = Field(0.0, description="below this, report the transcript as unavailable")


def load_wav(path: Path, rate: int = 16000) -> np.ndarray:
    """Mono float32 samples at ``rate``. Read directly because faster-whisper's own decoder breaks on PyAV>=15."""
    with wave.open(str(path), "rb") as w:
        sr, ch, width = w.getframerate(), w.getnchannels(), w.getsampwidth()
        raw = w.readframes(w.getnframes())
    if width != 2:
        raise ValueError(f"{path.name}: expected 16-bit PCM, got {8 * width}-bit")
    audio = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
    if ch > 1:
        audio = audio.reshape(-1, ch).mean(axis=1)
    if sr != rate and len(audio):
        n = int(round(len(audio) * rate / sr))
        audio = np.interp(np.linspace(0, len(audio) - 1, n), np.arange(len(audio)), audio).astype(np.float32)
    return audio


def _load(cfg: TranscribeSettings, device: str, log):
    from faster_whisper import WhisperModel

    cuda = device == "cuda"
    name = cfg.model or ("small" if cuda else "base")
    if cuda:
        try:
            return WhisperModel(name, device="cuda", compute_type=cfg.compute_type or "float16"), name, "cuda"
        except Exception as exc:  # noqa: BLE001 - missing CUDA libs etc. fall back to CPU
            log.warning("faster-whisper on CUDA failed, falling back to CPU: %s", exc)
    return WhisperModel(name, device="cpu", compute_type=cfg.compute_type or "int8",
                        cpu_threads=cfg.cpu_threads), name, "cpu"


def run(ctx: StageContext) -> None:
    p = ctx.project
    cfg = ctx.config.section("transcribe", TranscribeSettings)
    meta = p.read("ingest/meta.json", VideoMeta)
    if not meta.has_audio or not meta.audio_path or not p.exists(meta.audio_path):
        ctx.log.info("transcribe: no audio track, transcript unavailable")
        p.write("transcript/transcript.json", Transcript(available=False))
        return

    audio = load_wav(p.path(meta.audio_path))
    if not np.any(np.abs(audio) > 1e-4):
        ctx.log.info("transcribe: audio track is silent, transcript unavailable")
        p.write("transcript/transcript.json", Transcript(available=False))
        return
    started = time.perf_counter()
    model, name, device = _load(cfg, ctx.config.device, ctx.log)
    seg_iter, info = model.transcribe(
        audio, language=cfg.language, beam_size=cfg.beam_size,
        vad_filter=cfg.vad_filter, word_timestamps=cfg.word_timestamps,
    )
    segments: list[TranscriptSegment] = []
    for s in seg_iter:
        text = s.text.strip()
        if not text:
            continue
        words = [Word(start=round(w.start, 3), end=round(w.end, 3), word=w.word.strip(),
                      probability=round(w.probability, 4)) for w in (s.words or [])]
        segments.append(TranscriptSegment(id=len(segments), start=round(s.start, 3), end=round(s.end, 3),
                                          text=text, words=words))
    model_label = f"faster-whisper:{name}"
    available = bool(segments) and info.language_probability >= cfg.min_language_probability
    p.write("transcript/transcript.json", Transcript(
        available=available, language=info.language if available else None, model=model_label,
        segments=segments if available else [],
    ))
    ctx.log.info("transcribe: %d segments, language=%s (p=%.2f), %.1fs on %s", len(segments), info.language,
                 info.language_probability, time.perf_counter() - started, device)
