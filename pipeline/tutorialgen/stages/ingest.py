"""Stage 'ingest': download or copy the video, normalize it to constant-fps H.264 and extract 16 kHz mono audio.

Outputs (relative to the project): ingest/video.mp4, ingest/audio.wav (if the source has audio), ingest/meta.json.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from ..media import video
from ..media.download import USER_AGENT, download
from ..schemas.media import VideoMeta
from . import StageContext


class IngestSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_height: int = Field(720, description="normalized video height cap (never upscaled)")
    max_fps: float = Field(30.0, description="source fps is kept up to this cap")
    crf: int = 20
    preset: str = "veryfast"
    audio_rate: int = 16000
    download_max_height: int = 720
    threads: int = Field(4, description="ffmpeg encoder threads; 0 = all cores")
    user_agent: str = Field(USER_AGENT, description="descriptive User-Agent for direct media-file downloads")
    start_s: float | None = Field(None, ge=0, description="process one continuous excerpt of a long source (e.g. a livestream)")
    end_s: float | None = Field(None, gt=0)


def run(ctx: StageContext) -> None:
    p = ctx.project
    vin = p.manifest.video
    if vin is None:
        raise ValueError("project has no video; use `tutorialgen new --video` or Project.set_video")
    cfg = ctx.config.section("ingest", IngestSettings)
    out = p.stage_dir("ingest")
    title = uploader = license_ = None

    if vin.kind == "url":
        ctx.log.info("downloading %s", vin.source)
        dl = download(vin.source, out, cfg.download_max_height, user_agent=cfg.user_agent)
        src, title, uploader, license_ = dl.path, dl.title, dl.uploader, dl.license
    else:
        src = Path(vin.source)
        src = src if src.is_absolute() else p.path(src)
        if not src.exists():
            raise FileNotFoundError(f"video file {vin.source} is missing")

    info = video.probe(src)
    if not info.has_video:
        raise ValueError(f"{src.name} has no video stream")
    if cfg.start_s is not None and cfg.end_s is not None and cfg.end_s <= cfg.start_s:
        raise ValueError("ingest.end_s must be after ingest.start_s")
    if cfg.start_s or cfg.end_s:
        ctx.log.info("excerpt %.1fs-%s of the source", cfg.start_s or 0, f"{cfg.end_s:.1f}s" if cfg.end_s else "end")
    fps = round(min(info.fps, cfg.max_fps), 3)
    ctx.log.info("normalizing %s (%dx%d @ %.3f fps, audio=%s) -> %.3f fps, <=%dp",
                 src.name, info.width, info.height, info.fps, info.has_audio, fps, cfg.max_height)
    video_path = out / "video.mp4"
    video.normalize(src, video_path, fps, cfg.max_height, cfg.crf, cfg.preset, threads=cfg.threads,
                    start=cfg.start_s, end=cfg.end_s)

    audio_path = out / "audio.wav"
    audio_path.unlink(missing_ok=True)
    has_audio = info.has_audio
    if has_audio:
        try:
            video.extract_audio(src, audio_path, cfg.audio_rate, start=cfg.start_s, end=cfg.end_s)
        except video.FFmpegError as exc:
            ctx.log.warning("audio stream could not be decoded, continuing without audio: %s", exc)
            has_audio = False

    norm = video.probe(video_path, count_frames=True)
    p.write("ingest/meta.json", VideoMeta(
        source=vin.source, source_kind=vin.kind, title=title or info.title, uploader=uploader, license=license_,
        duration=round(norm.frame_count / norm.fps, 3) if norm.fps else norm.duration,
        fps=norm.fps, width=norm.width, height=norm.height, frame_count=norm.frame_count,
        has_audio=has_audio, video_path=p.rel(video_path),
        audio_path=p.rel(audio_path) if has_audio else None,
        excerpt_start=cfg.start_s, excerpt_end=cfg.end_s,
    ))
