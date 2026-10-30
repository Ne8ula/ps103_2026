"""Video IO: bundled ffmpeg (imageio-ffmpeg) for transcoding, PyAV for probing and decoding. No ffprobe needed."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import numpy as np


class FFmpegError(RuntimeError):
    pass


def ffmpeg_exe() -> str:
    import imageio_ffmpeg

    return imageio_ffmpeg.get_ffmpeg_exe()


def run_ffmpeg(args: list[str]) -> None:
    cmd = [ffmpeg_exe(), "-hide_banner", "-nostdin", "-loglevel", "error", "-y", *args]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise FFmpegError(f"ffmpeg failed ({proc.returncode}): {proc.stderr.strip()[-2000:]}")


@dataclass
class ProbeInfo:
    duration: float
    fps: float
    width: int
    height: int
    frame_count: int
    has_video: bool
    has_audio: bool
    title: str | None = None


def _stream_fps(container, stream) -> float:
    """Nominal fps; webm often reports a 1000 fps time base, so cross-check with packet spacing."""
    rate = stream.guessed_rate or stream.average_rate or stream.base_rate
    fps = float(rate) if rate else 0.0
    if 1.0 <= fps <= 120.0:
        return fps
    pts = []
    for packet in container.demux(stream):
        if packet.pts is not None:
            pts.append(packet.pts)
        if len(pts) >= 120:
            break
    container.seek(0)
    if len(pts) >= 2 and stream.time_base:
        delta = float(np.median(np.diff(np.sort(pts)))) * float(stream.time_base)
        if delta > 0:
            return 1.0 / delta
    return 30.0


def probe(path: str | Path, count_frames: bool = False) -> ProbeInfo:
    """Probe a media file with PyAV. ``count_frames`` decodes nothing but demuxes every video packet."""
    import av

    with av.open(str(path)) as c:
        vs = c.streams.video[0] if c.streams.video else None
        has_audio = bool(c.streams.audio)
        title = (c.metadata or {}).get("title") or None
        duration = float(c.duration / av.time_base) if c.duration else 0.0
        if vs is None:
            return ProbeInfo(duration, 0.0, 0, 0, 0, False, has_audio, title)
        if vs.duration and vs.time_base:
            duration = float(vs.duration * vs.time_base) or duration
        fps = _stream_fps(c, vs)
        frames = int(vs.frames or 0)
        if count_frames or not frames:
            frames = sum(1 for p in c.demux(vs) if p.size)
        if not duration and fps:
            duration = frames / fps
        return ProbeInfo(duration, fps, vs.codec_context.width, vs.codec_context.height, frames, True, has_audio, title)


def _range(start: float | None, end: float | None) -> list[str]:
    """Input options selecting one continuous excerpt [start, end) of the source, in seconds."""
    return (["-ss", f"{start:.3f}"] if start else []) + (["-to", f"{end:.3f}"] if end else [])


def normalize(src: Path, dest: Path, fps: float, max_height: int, crf: int = 20, preset: str = "veryfast",
              keep_audio: bool = True, threads: int = 0, start: float | None = None, end: float | None = None) -> None:
    """H.264/yuv420p, constant ``fps``, height <= ``max_height`` (even dims), +faststart; AAC audio if present."""
    vf = f"scale=-2:'min({max_height},trunc(ih/2)*2)':flags=bicubic,fps={fps:.6g},format=yuv420p"
    args = [*_range(start, end), "-i", str(src), "-map", "0:v:0", "-vf", vf, "-c:v", "libx264", "-preset", preset, "-crf", str(crf),
            "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-threads", str(threads)]
    args += ["-map", "0:a:0?", "-c:a", "aac", "-b:a", "128k"] if keep_audio else ["-an"]
    dest.parent.mkdir(parents=True, exist_ok=True)
    run_ffmpeg([*args, str(dest)])


def extract_audio(src: Path, dest: Path, rate: int = 16000, start: float | None = None, end: float | None = None) -> None:
    """Mono 16-bit PCM wav at ``rate``."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    run_ffmpeg([*_range(start, end), "-i", str(src), "-map", "0:a:0", "-vn", "-ac", "1", "-ar", str(rate), "-c:a", "pcm_s16le", str(dest)])


def sample_indices(n_frames: int, fps: float, sample_fps: float | None) -> list[int]:
    """Frame indices that sample a constant-fps video at ``sample_fps`` (every frame if sample_fps >= fps)."""
    if not sample_fps or sample_fps >= fps:
        return list(range(n_frames))
    step = fps / sample_fps
    return [i for k in range(int(n_frames / step) + 2) if (i := int(k * step + 1e-9)) < n_frames]


def iter_frames(path: str | Path, fps: float, sample_fps: float | None = None) -> Iterator[tuple[int, float, np.ndarray]]:
    """Yield (frame_index, t_seconds, rgb uint8 HxWx3) for a constant-fps video, optionally subsampled.

    Frame index counts decoded frames, so t = index / fps matches the normalized file exactly.
    """
    import av

    with av.open(str(path)) as c:
        vs = c.streams.video[0]
        vs.thread_type = "AUTO"
        step = None if not sample_fps or sample_fps >= fps else fps / sample_fps
        k = 0
        for i, frame in enumerate(c.decode(vs)):
            if step is not None:
                if i != int(k * step + 1e-9):
                    continue
                k += 1
            yield i, i / fps, frame.to_ndarray(format="rgb24")
