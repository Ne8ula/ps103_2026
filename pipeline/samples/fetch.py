"""Download the development samples into samples/data/ (gitignored). Usage: python samples/fetch.py"""

from __future__ import annotations

import json
import subprocess
import sys
import urllib.request
from pathlib import Path

DATA = Path(__file__).with_name("data")
SAMPLES = json.loads(Path(__file__).with_name("samples.json").read_text())


def main() -> int:
    DATA.mkdir(exist_ok=True)
    for item in SAMPLES:
        dest = DATA / item["file"]
        if dest.exists():
            print(f"have {dest.name}")
            continue
        print(f"fetching {item['file']} ({item['license']})")
        req = urllib.request.Request(item["url"], headers={"User-Agent": "tutorialgen-dev/0.1 (research prototype)"})
        with urllib.request.urlopen(req, timeout=120) as resp, open(dest, "wb") as f:
            f.write(resp.read())
        if md := item.get("markdown"):
            # Isolated interpreter: the converter reads downloaded HTML.
            subprocess.run([sys.executable, "-I", str(Path(__file__).with_name("html2md.py")), str(dest),
                            str(DATA / md), item["url"], item["title"]], check=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
