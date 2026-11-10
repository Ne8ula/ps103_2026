"""Build the comparison + expert-studio demo page from a finished project and a recorded API session.

    python demo/build_demo.py <project_id> <capture_dir> <out_dir>

Writes <out_dir>/studio.html (data inlined) and <out_dir>/media/*.mp4 (compressed to fit artifact limits).
The capture dir comes from demo/capture_api.py: api_log.json, before.json, after.json and home/<project>.
"""

from __future__ import annotations

import collections
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
import yaml

from tutorialgen.eval import Labels, evaluate
from tutorialgen.media.video import ffmpeg_exe
from tutorialgen.project import Project
from tutorialgen.edit import subtitle_lines
from tutorialgen.schemas import HandFrame, Transcript, VideoMeta
from tutorialgen.stages.render import RenderConfig

PIPELINE = Path(__file__).resolve().parents[1]
CARD_BGR = np.array([51, 39, 41])  # render cards are drawn on ink #292733

# The curated tutorial is linked, not re-hosted (standard YouTube license). Outline from its captions.
CURATED = {
    "id": "DPtA6Nmu70I", "url": "https://www.youtube.com/watch?v=DPtA6Nmu70I",
    "title": "Installing The SteinWipe Nozzle Wiper On Your Bambu Lab P1P P1S X1C 3D Printer",
    "channel": "Leckiestein", "duration": 681, "views": 26291, "likes": 518, "uploaded": "2025-01-20",
    "cuts_per_min": 2.4, "license": "Standard YouTube License (linked, not re-hosted)",
    "outline": [
        (0, "Why this video: viewers' holes drifting and wipers tipping"),
        (67, "A better way to drill the back-panel holes: pre-drill small, then larger, to avoid fly cutting"),
        (113, "Use a small drill so you can stay perpendicular in the tight space"),
        (158, "Problems with the first template: too much play, people drilling straight through"),
        (208, "The new template registers on two surfaces and keeps the drill square"),
        (278, "Start with the outside hole; mark through the template rather than drilling through it"),
        (323, "1/8 in drill bit, about 3.2 mm; pre-drill the template's own holes first"),
        (400, "Drilling: the small bit finds the mark, then open up with the 1/8 in"),
        (449, "Deburr the holes so nothing affects fitment"),
        (474, "Backing plate: one screw first, then the two outer screws, then tighten the centre snug"),
        (545, "Swapping a worn wiper later: unscrew and fit a pre-mounted one, no realignment"),
        (615, "Check the wiper height against the nozzle"),
    ],
}

RAW = {
    "url": "https://www.youtube.com/watch?v=7787-1g8l4Y", "title": "Bambu Lab X1 Carbon Mod Install LIVE",
    "channel": "Leckiestein", "license": "CC BY (YouTube)", "excerpt": "49:00–62:30", "cuts_per_min": 0.1,
}


def encode(src: Path, dest: Path, crf: int) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([ffmpeg_exe(), "-loglevel", "error", "-y", "-i", str(src), "-vf", "fps=15,scale=640:-2",
                    "-c:v", "libx264", "-preset", "slow", "-crf", str(crf), "-maxrate", "380k", "-bufsize", "760k",
                    "-pix_fmt", "yuv420p", "-c:a", "aac", "-ac", "1", "-b:a", "48k", "-movflags", "+faststart", str(dest)],
                   check=True)


def encode_under(src: Path, dest: Path, limit_mb: float = 14.5) -> None:
    if dest.exists() and dest.stat().st_mtime > src.stat().st_mtime and dest.stat().st_size <= limit_mb * 1e6:
        return  # already encoded from this source
    for crf in (31, 33, 35, 37):
        encode(src, dest, crf)
        if dest.stat().st_size <= limit_mb * 1e6:
            return
    raise SystemExit(f"{dest.name} is still over {limit_mb} MB")


def card_runs(path: Path, step_s: float = 0.25) -> tuple[list[tuple[float, float]], float]:
    """Time ranges where the tutorial shows a full-frame text card (intro, step cards, outro)."""
    cap = cv2.VideoCapture(str(path))
    fps = cap.get(cv2.CAP_PROP_FPS)
    dur = cap.get(cv2.CAP_PROP_FRAME_COUNT) / fps
    runs, start, t = [], None, 0.0
    while t < dur:
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
        ok, f = cap.read()
        if not ok:
            break
        small = cv2.resize(f, (64, 36)).reshape(-1, 3).astype(int)
        is_card = (np.abs(small - CARD_BGR).sum(axis=1) < 30).mean() > 0.55
        if is_card and start is None:
            start = t
        elif not is_card and start is not None:
            runs.append((start, t))
            start = None
        t += step_s
    if start is not None:
        runs.append((start, dur))
    return runs, dur


def stage_timings(project: Project) -> list[dict]:
    out = []
    for name, st in project.manifest.stages.items():
        if st.started_at and st.finished_at:
            secs = (datetime.fromisoformat(st.finished_at) - datetime.fromisoformat(st.started_at)).total_seconds()
            out.append({"stage": name, "seconds": round(secs, 1), "status": st.status})
    return out


def _ts(t: float) -> str:
    t = max(0.0, t)
    return f"{int(t // 3600):02d}:{int(t % 3600 // 60):02d}:{t % 60:06.3f}"


def vtt(cues: list[tuple[float, float, str]], settings: str = "") -> str:
    lines = ["WEBVTT", ""]
    for i, (a, b, text) in enumerate(c for c in cues if c[1] - c[0] > 0.05):
        lines += [str(i + 1), f"{_ts(a)} --> {_ts(b)}{(' ' + settings) if settings else ''}", text, ""]
    return "\n".join(lines)


def kept_segments(step: dict, edit: dict | None) -> list[list[float]]:
    """[[source start, source end, output start within the clip, speed], ...] for one step's clip.
    Without an edit list the clip is the whole step at 1x."""
    if not edit:
        return [[step["start"], step["end"], 0.0, 1.0]]
    out, t = [], 0.0
    for u in edit["units"]:
        if u["action"] == "cut":
            continue
        speed = u["speed"] if u["action"] == "speed" else 1.0
        if out and speed == 1.0 == out[-1][3] and abs(out[-1][1] - u["start"]) < 1e-6:
            out[-1][1] = u["end"]                       # merge contiguous kept units
        else:
            out.append([u["start"], u["end"], t, speed])
        t += (u["end"] - u["start"]) / speed
    return [[round(x, 3) for x in seg] for seg in out]


def tutorial_cues(segments: list[dict], steps: list[dict], offsets: list[dict], title: str, tut_dur: float,
                  kept: list[list[list[float]]]) -> list[tuple[float, float, str]]:
    """Narration re-timed into the rendered tutorial through each step's kept segments. Sped-up parts
    are muted, so their lines get no subtitle; cut parts are not in the tutorial at all."""
    cues = [(0.0, offsets[0]["card"], title)] if offsets else []
    for i, (s, o) in enumerate(zip(steps, offsets)):
        cues.append((o["card"], o["clip"], f"Step {i + 1} of {len(steps)}: {s['title']}"))
        for a0, b0, out0, speed in kept[i]:
            if speed != 1.0:
                continue
            shift = o["clip"] + out0 - a0
            for seg in segments:
                a, b = max(seg["start"], a0), min(seg["end"], b0)
                if b - a > 0.15:
                    cues.append((a + shift, min(b + shift, o["end"]), seg["text"]))
    if offsets:
        cues.append((offsets[-1]["end"], tut_dur, "Open questions for the expert"))
    return sorted(cues)


def write_local_compare(out: Path) -> None:
    """Three players side by side for local viewing; the curated video is a local-only copy (never published)."""
    curated = PIPELINE / "samples" / "data" / "reference" / f"{CURATED['id']}.mp4"
    rel = Path("..", "..", "samples", "data", "reference", curated.name).as_posix() if out.resolve() == (PIPELINE / "demo" / "out").resolve() else curated.as_uri()
    cols = [("1 · Raw livestream excerpt", "media/raw.mp4", "media/raw.vtt"),
            ("2 · Our generated tutorial", "media/tutorial.mp4", "media/tutorial.vtt"),
            (f"3 · {CURATED['channel']}: curated tutorial ({CURATED['views']:,} views)", rel, rel.replace(".mp4", ".en.vtt"))]
    players = "".join(f'<figure><figcaption>{t}</figcaption><video src="{s}" controls preload="metadata">'
                      f'<track kind="subtitles" srclang="en" label="English" src="{v}" default></video></figure>' for t, s, v in cols)
    (out / "compare_local.html").write_text(f"""<!doctype html><meta charset="utf-8"><title>SteinWipe: three videos</title>
<style>body{{font:15px system-ui;margin:16px;background:#111;color:#eee}}main{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}}
figure{{margin:0}}video{{width:100%;background:#000}}button{{font:inherit;padding:6px 12px;margin-bottom:12px}}</style>
<button onclick="document.querySelectorAll('video').forEach(v=>{{v.currentTime=0;v.play()}})">Play all from the start</button>
<button onclick="document.querySelectorAll('video').forEach(v=>v.pause())">Pause all</button>
<main>{players}</main><p>Local only: the curated video is a standard-license YouTube download kept in samples/data (gitignored).</p>""")


def main(project_id: str, capture_dir: str, out_dir: str) -> None:
    out, cap_dir = Path(out_dir), Path(capture_dir)
    orig = Project.load(PIPELINE / "projects" / project_id)
    after_project = Project(cap_dir / "home" / project_id)
    before, after = json.loads((cap_dir / "before.json").read_text()), json.loads((cap_dir / "after.json").read_text())
    api_log = json.loads((cap_dir / "api_log.json").read_text())

    meta = orig.read("ingest/meta.json", VideoMeta)
    tr = orig.read("transcript/transcript.json", Transcript)
    frames = orig.read_jsonl("hands/frames.jsonl", HandFrame)
    buckets = collections.defaultdict(list)
    for f in frames:
        buckets[int(f.t // 2)].append(min(len(f.hands), 2))
    hands = [round(sum(v) / len(v) / 2, 3) for _, v in sorted(buckets.items())]

    print("encoding raw excerpt and tutorial ...", flush=True)
    encode_under(orig.path(meta.video_path), out / "media" / "raw.mp4")
    tutorial_src = after_project.path("render/tutorial.mp4")
    encode_under(tutorial_src, out / "media" / "tutorial.mp4")

    runs, tut_dur = card_runs(tutorial_src)
    n = len(after["steps"]["steps"])
    offsets = []
    if len(runs) == n + 1:  # the intro card runs straight into step 1's card: split at the intro length
        intro = after_project.config().raw("render").get("intro_seconds", RenderConfig().intro_seconds)
        runs = [(runs[0][0], runs[0][0] + intro), (runs[0][0] + intro, runs[0][1]), *runs[1:]]
    if len(runs) == n + 2:  # intro, one card per step, outro
        for i in range(n):
            clip_end = runs[i + 2][0]
            offsets.append({"card": round(runs[i + 1][0], 2), "clip": round(runs[i + 1][1], 2), "end": round(clip_end, 2)})
    else:
        print(f"warning: found {len(runs)} card runs for {n} steps; step offsets left out", flush=True)

    segments = [{"start": l.start, "end": l.end, "text": l.text} for l in subtitle_lines(tr)]
    edl = json.loads(after_project.path("edit/edl.json").read_text()) if after_project.exists("edit/edl.json") else None
    edits = {e["step_id"]: e for e in edl["steps"]} if edl and edl["enabled"] else {}
    kept = [kept_segments(s, edits.get(s["id"])) for s in after["steps"]["steps"]]
    raw_cues = [(s["start"], s["end"], s["text"]) for s in segments]
    tut_cues = tutorial_cues(segments, after["steps"]["steps"], offsets, after_project.manifest.name, tut_dur, kept) if offsets else []
    # .vtt files serve the local compare page; the published page adds the same cues from its inline data.
    (out / "media" / "raw.vtt").write_text(vtt(raw_cues))
    (out / "media" / "tutorial.vtt").write_text(vtt(tut_cues, "line:6% position:50% align:center"))

    labels = Labels.model_validate(yaml.safe_load((PIPELINE / "eval" / "x1c-steinwipe-livestream.yaml").read_text()))
    ev_before, ev_after = evaluate(orig, labels), evaluate(after_project, labels)
    served = collections.Counter(json.loads(p.read_text()).get("served_by")
                                 for p in after_project.path("llm_cache").glob("*.json"))

    data = {
        "project_id": project_id, "raw": RAW, "curated": CURATED,
        "duration": meta.duration, "excerpt_start": meta.excerpt_start,
        "transcript": [{"id": s.id, "start": s.start, "end": s.end, "text": s.text.strip()} for s in tr.segments],
        "subs": {"raw": [[round(a, 2), round(b, 2), t] for a, b, t in raw_cues],
                 "tutorial": [[round(a, 2), round(b, 2), t] for a, b, t in tut_cues]},
        "kept": kept,
        "edl": {"enabled": bool(edits), "source_s": edl["source_s"] if edl else None, "output_s": edl["output_s"] if edl else None,
                "steps": [[[u["start"], u["end"], u["action"], u["label"], u["reason"]] for u in edits[s["id"]]["units"]]
                          if s["id"] in edits else [] for s in after["steps"]["steps"]]},
        "hands": hands, "labels": labels.steps, "tutorial_duration": round(tut_dur, 1), "offsets": offsets,
        "before": before, "after": after, "api_log": api_log,
        "stages": stage_timings(orig) + [t for t in stage_timings(after_project) if t["stage"] == "edit"],
        "rerun_stages": stage_timings(after_project),
        "manifest": json.loads(orig.path("project.json").read_text()),
        "sop": (PIPELINE / "samples" / "data" / "bambu-x1-replace-nozzle-wiper.md").read_text(),
        "answers": json.loads(after_project.path("inputs/answers.json").read_text())["answers"],
        "eval": {"before": ev_before, "after": ev_after},
        "llm_calls": {k or "unknown": v for k, v in served.items()},
        "llm_by_task": dict(collections.Counter(json.loads(p.read_text())["task"]
                                                for p in after_project.path("llm_cache").glob("*.json"))),
    }
    html = (Path(__file__).with_name("studio_template.html")).read_text()
    (out / "studio.html").write_text(html.replace("__DATA__", json.dumps(data).replace("</", "<\\/")))
    write_local_compare(out)
    sizes = {p.name: round(p.stat().st_size / 1e6, 1) for p in (out / "media").glob("*.mp4")}
    print(f"wrote {out / 'studio.html'} ({(out / 'studio.html').stat().st_size // 1024} KB); media MB: {sizes}; "
          f"{len(offsets)} step offsets")


if __name__ == "__main__":
    main(*sys.argv[1:4])
