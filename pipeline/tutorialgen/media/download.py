"""URL download: yt-dlp Python API for pages (YouTube and anything else yt-dlp supports); plain HTTP for direct
media files, identified with a descriptive User-Agent (Wikimedia's robot policy rejects yt-dlp's request
fingerprint, while an honest direct GET is allowed).
"""

from __future__ import annotations

import logging
import shutil
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urlparse

from .video import ffmpeg_exe

log = logging.getLogger("tutorialgen.media")


@dataclass
class Download:
    path: Path
    title: str | None = None
    uploader: str | None = None
    license: str | None = None


def format_selector(max_height: int) -> str:
    """Prefer mp4/m4a at <= max_height, then any container at <= max_height, then whatever exists."""
    h = f"[height<={max_height}]"
    return "/".join([
        f"bv*{h}[ext=mp4]+ba[ext=m4a]",
        f"b{h}[ext=mp4]",
        f"bv*{h}+ba",
        f"b{h}",
        "bv*+ba",
        "b",
    ])


MEDIA_EXTS = {".mp4", ".m4v", ".mov", ".webm", ".mkv", ".avi", ".ogv", ".ogg", ".mpg", ".mpeg", ".wmv", ".flv"}
USER_AGENT = "tutorialgen/0.1 (research prototype; demo-video tutorial pipeline)"


def is_direct_media(url: str) -> bool:
    return Path(urlparse(url).path).suffix.lower() in MEDIA_EXTS


def download_direct(url: str, dest_dir: Path, stem: str = "source", user_agent: str = USER_AGENT) -> Download:
    name = Path(unquote(urlparse(url).path)).name
    dest = dest_dir / f"{stem}{Path(name).suffix.lower()}"
    tmp = dest.with_suffix(dest.suffix + ".part")
    req = urllib.request.Request(url, headers={"User-Agent": user_agent})
    with urllib.request.urlopen(req, timeout=120) as resp, open(tmp, "wb") as f:
        shutil.copyfileobj(resp, f, 1 << 20)
    tmp.replace(dest)
    return Download(path=dest, title=Path(name).stem.replace("_", " "))


def download(url: str, dest_dir: Path, max_height: int = 720, stem: str = "source",
             user_agent: str = USER_AGENT) -> Download:
    """Download one video into ``dest_dir/<stem>.<ext>``."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    for old in dest_dir.glob(f"{stem}.*"):
        old.unlink()
    if is_direct_media(url):
        return download_direct(url, dest_dir, stem, user_agent)

    import yt_dlp

    opts = {
        "format": format_selector(max_height),
        "outtmpl": str(dest_dir / f"{stem}.%(ext)s"),
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "ffmpeg_location": ffmpeg_exe(),
        "merge_output_format": "mp4",
        "retries": 3,
        "logger": log,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
    if info.get("_type") == "playlist" and info.get("entries"):
        info = next(e for e in info["entries"] if e)
    files = [Path(d["filepath"]) for d in info.get("requested_downloads") or [] if d.get("filepath")]
    path = files[0] if files else next((p for p in dest_dir.glob(f"{stem}.*") if not p.name.endswith(".part")), None)
    if path is None or not path.exists():
        raise RuntimeError(f"yt-dlp reported success but no file was written for {url}")
    return Download(path=path, title=info.get("title"), uploader=info.get("uploader") or info.get("channel"),
                    license=info.get("license"))
