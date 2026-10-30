"""Video IO for rendering: source frame reader, audio decode, and an ffmpeg H.264 encoder fed raw frames.

There is no system ffmpeg; the binary bundled with imageio-ffmpeg is used (``ffmpeg_exe``).
"""

from __future__ import annotations

import functools
import logging
import shutil
import subprocess
import tempfile
import wave
from fractions import Fraction
from pathlib import Path

import cv2
import numpy as np

log = logging.getLogger(__name__)


@functools.lru_cache(maxsize=1)
def ffmpeg_exe() -> str:
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:  # noqa: BLE001 - any failure means "not bundled"
        exe = shutil.which("ffmpeg")
        if not exe:
            raise RuntimeError("no ffmpeg binary: install imageio-ffmpeg or put ffmpeg on PATH")
        return exe


@functools.lru_cache(maxsize=4)
def encoder_works(codec: str) -> bool:
    """Encode a few black frames with ``codec`` to check it really works here (nvenc needs a GPU)."""
    cmd = [ffmpeg_exe(), "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i", "color=black:s=256x256:d=0.2",
           "-c:v", codec, "-f", "null", "-"]
    try:
        return subprocess.run(cmd, capture_output=True, timeout=30).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def pick_encoder(device: str, preference: str = "auto") -> str:
    if preference != "auto":
        if encoder_works(preference):
            return preference
        log.warning("encoder %s unavailable, falling back to libx264", preference)
        return "libx264"
    if device.startswith("cuda") and encoder_works("h264_nvenc"):
        return "h264_nvenc"
    return "libx264"


def fps_fraction(fps: float) -> Fraction:
    return Fraction(fps).limit_denominator(1001)


def output_size(width: int, height: int, max_height: int) -> tuple[int, int]:
    """Scale down to ``max_height`` keeping aspect; both sides even (yuv420p)."""
    h = min(height, max_height) if max_height else height
    w = width * h / height
    return max(int(round(w / 2)) * 2, 2), max(int(round(h / 2)) * 2, 2)


# ---- audio ---------------------------------------------------------------------------------

def read_audio(path: Path, rate: int) -> np.ndarray | None:
    """Decode the first audio stream of any file to mono int16 at ``rate``; None if there is none."""
    cmd = [ffmpeg_exe(), "-hide_banner", "-loglevel", "error", "-i", str(path), "-vn", "-map", "0:a:0?",
           "-ac", "1", "-ar", str(rate), "-f", "s16le", "-"]
    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=600)
    except (OSError, subprocess.TimeoutExpired) as e:
        log.warning("audio decode failed for %s: %s", path, e)
        return None
    if proc.returncode != 0 or not proc.stdout:
        return None
    return np.frombuffer(proc.stdout, dtype=np.int16)


def write_wav(path: Path, samples: np.ndarray, rate: int) -> Path:
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(np.ascontiguousarray(samples, dtype=np.int16).tobytes())
    return path


def audio_slice(src: np.ndarray | None, start: int, length: int) -> np.ndarray:
    """``length`` samples of ``src`` from ``start``, zero-padded where the source runs out."""
    out = np.zeros(length, dtype=np.int16)
    if src is None or length <= 0 or start >= len(src):
        return out
    start = max(start, 0)
    part = src[start:start + length]
    out[: len(part)] = part
    return out


# ---- frames --------------------------------------------------------------------------------

class FrameReader:
    """Sequential reader with cheap forward skips; seeks only when going backwards or far ahead."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.cap = cv2.VideoCapture(str(self.path))
        if not self.cap.isOpened():
            raise RuntimeError(f"cannot open video {self.path}")
        self.pos = 0
        self.last: np.ndarray | None = None

    @property
    def fps(self) -> float:
        return float(self.cap.get(cv2.CAP_PROP_FPS) or 0)

    @property
    def size(self) -> tuple[int, int]:
        return int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    def read(self, index: int) -> np.ndarray | None:
        """Frame ``index`` (BGR); repeats the last good frame past the end of the stream."""
        if index < self.pos or index - self.pos > 600:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, index)
            self.pos = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
            if self.pos != index:  # inexact seek: reopen and walk forward
                self.cap.release()
                self.cap = cv2.VideoCapture(str(self.path))
                self.pos = 0
        while self.pos < index:
            if not self.cap.grab():
                return self.last
            self.pos += 1
        ok, frame = self.cap.read()
        if not ok:
            return self.last
        self.pos += 1
        self.last = frame
        return frame

    def close(self) -> None:
        self.cap.release()


class Encoder:
    """ffmpeg process that takes raw BGR frames on stdin and writes H.264/yuv420p MP4 (+ AAC from a wav)."""

    def __init__(self, path: Path, width: int, height: int, fps: float, audio_wav: Path | None = None,
                 codec: str = "libx264", crf: int = 20, preset: str = "fast", audio_bitrate: str = "128k"):
        self.path = Path(path)
        self.size = (width, height)
        self.frames = 0
        self._err = tempfile.TemporaryFile()
        rate = fps_fraction(fps)
        cmd = [ffmpeg_exe(), "-hide_banner", "-loglevel", "error", "-y",
               "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{width}x{height}",
               "-framerate", f"{rate.numerator}/{rate.denominator}", "-i", "-"]
        if audio_wav is not None:
            cmd += ["-i", str(audio_wav)]
        cmd += ["-map", "0:v:0"]
        if codec == "h264_nvenc":
            cmd += ["-c:v", "h264_nvenc", "-preset", "p5", "-rc", "vbr", "-cq", str(crf), "-b:v", "0"]
        else:
            cmd += ["-c:v", "libx264", "-preset", preset, "-crf", str(crf)]
        cmd += ["-pix_fmt", "yuv420p", "-r", f"{rate.numerator}/{rate.denominator}"]
        if audio_wav is not None:
            cmd += ["-map", "1:a:0", "-c:a", "aac", "-b:a", audio_bitrate, "-ac", "1"]
        else:
            cmd += ["-an"]
        cmd += ["-movflags", "+faststart", "-map_metadata", "-1", "-fflags", "+bitexact",
                "-flags:v", "+bitexact", "-flags:a", "+bitexact", str(self.path)]
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=self._err)

    def write(self, frame: np.ndarray) -> None:
        if frame.shape[1] != self.size[0] or frame.shape[0] != self.size[1]:
            frame = cv2.resize(frame, self.size, interpolation=cv2.INTER_AREA)
        try:
            self.proc.stdin.write(np.ascontiguousarray(frame).tobytes())
        except BrokenPipeError:
            self._fail()
        self.frames += 1

    def write_repeat(self, frame: np.ndarray, n: int) -> None:
        for _ in range(n):
            self.write(frame)

    def close(self) -> None:
        if self.proc.stdin and not self.proc.stdin.closed:
            try:
                self.proc.stdin.close()
            except BrokenPipeError:
                pass
        if self.proc.wait() != 0:
            self._fail()
        self._err.close()

    def abort(self) -> None:
        if self.proc.poll() is None:
            self.proc.kill()
            self.proc.wait()
        self._err.close()
        self.path.unlink(missing_ok=True)

    def _fail(self):
        self.proc.kill()
        self.proc.wait()
        self._err.seek(0)
        msg = self._err.read().decode(errors="replace")[-2000:]
        raise RuntimeError(f"ffmpeg failed writing {self.path}: {msg}")

    def __enter__(self) -> "Encoder":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if exc_type is None:
            self.close()
        else:
            self.abort()
