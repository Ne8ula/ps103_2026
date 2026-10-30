"""Minimal HTML -> Markdown for a wiki page: headings, paragraphs, list items, with source header."""

import re
import sys
from html.parser import HTMLParser

src, dest, url, title = sys.argv[1:5]
html = open(src, encoding="utf-8", errors="replace").read()
# Wiki.js keeps the rendered article inside <template slot="contents">.
m = re.search(r'<template slot="contents">(.*?)</template>', html, re.S)
html = m.group(1) if m else html


class P(HTMLParser):
    def __init__(self):
        super().__init__()
        self.out, self.buf, self.prefix, self.skip = [], [], "", 0

    def flush(self):
        text = re.sub(r"\s+", " ", "".join(self.buf)).strip()
        if text:
            self.out.append(self.prefix + text)
        self.buf, self.prefix = [], ""

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.skip += 1
        elif tag in ("h1", "h2", "h3", "h4"):
            self.flush(); self.prefix = "#" * int(tag[1]) + " "
        elif tag in ("p", "div", "br", "tr"):
            self.flush()
        elif tag == "li":
            self.flush(); self.prefix = "- "
        elif tag == "img":
            alt = dict(attrs).get("alt")
            if alt:
                self.buf.append(f" [image: {alt}] ")

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.skip -= 1
        elif tag in ("h1", "h2", "h3", "h4", "p", "li", "div", "tr"):
            self.flush()

    def handle_data(self, data):
        if not self.skip:
            self.buf.append(data)


p = P()
p.feed(html)
p.flush()
lines = [l for l in p.out if l.strip()]
with open(dest, "w") as f:
    f.write(f"# {title}\n\nSource: {url}\n\n" + "\n\n".join(lines) + "\n")
print(len(lines), "blocks")
