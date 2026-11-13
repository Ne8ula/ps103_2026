"""Build BenchMate_Maker_Day_3.html: Maker Day 2's styles, fonts, marks and nav + the slides here.

Run from the repo root:  python tmp/maker-day-3/build.py
"""
import base64, re
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parent.parent
md2 = (ROOT / 'BenchMate_Maker_Day_2.html').read_text(encoding='utf-8')

# Lucide paths (ISC, license comment is carried over from Maker Day 2).
ICONS = {
    'book-open': '<path d="M12 7v14"/><path d="M3 18a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h5a4 4 0 0 1 4 4 4 4 0 0 1 4-4h5a1 1 0 0 1 1 1v13a1 1 0 0 1-1 1h-6a3 3 0 0 0-3 3 3 3 0 0 0-3-3z"/>',
    'network': '<rect x="16" y="16" width="6" height="6" rx="1"/><rect x="2" y="16" width="6" height="6" rx="1"/><rect x="9" y="2" width="6" height="6" rx="1"/><path d="M5 16v-3a1 1 0 0 1 1-1h12a1 1 0 0 1 1 1v3"/><path d="M12 12V8"/>',
    'building2': '<path d="M6 22V4a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v18Z"/><path d="M6 12H4a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h2"/><path d="M18 9h2a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2h-2"/><path d="M10 6h4"/><path d="M10 10h4"/><path d="M10 14h4"/><path d="M10 18h4"/>',
    'factory': '<path d="M2 20a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V8l-7 5V8l-7 5V4a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2Z"/><path d="M17 18h1"/><path d="M12 18h1"/><path d="M7 18h1"/>',
    'printer': '<path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/><path d="M6 9V3a1 1 0 0 1 1-1h10a1 1 0 0 1 1 1v6"/><rect x="6" y="14" width="12" height="8" rx="1"/>',
    'badge-check': '<path d="M3.85 8.62a4 4 0 0 1 4.78-4.77 4 4 0 0 1 6.74 0 4 4 0 0 1 4.78 4.78 4 4 0 0 1 0 6.74 4 4 0 0 1-4.77 4.78 4 4 0 0 1-6.75 0 4 4 0 0 1-4.78-4.77 4 4 0 0 1 0-6.76Z"/><path d="m9 12 2 2 4-4"/>',
    'zap': '<path d="M4 14a1 1 0 0 1-.78-1.63l9.9-10.2a.5.5 0 0 1 .86.46l-1.92 6.02A1 1 0 0 0 13 10h7a1 1 0 0 1 .78 1.63l-9.9 10.2a.5.5 0 0 1-.86-.46l1.92-6.02A1 1 0 0 0 11 14z"/>',
    'film': '<rect width="18" height="18" x="3" y="3" rx="2"/><path d="M7 3v18"/><path d="M3 7.5h4"/><path d="M3 12h18"/><path d="M3 16.5h4"/><path d="M17 3v18"/><path d="M17 7.5h4"/><path d="M17 16.5h4"/>',
    'shield-check': '<path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/><path d="m9 12 2 2 4-4"/>',
    'clock': '<circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>',
}


def icon(m):
    name, size, stroke = m.group(1), m.group(2), m.group(3) or '1.5'
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
            f'stroke="currentColor" stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round" '
            f'aria-hidden="true">{ICONS[name]}</svg>')


def image(m):
    data = base64.b64encode((HERE / 'img' / m.group(1)).read_bytes()).decode()
    return f'data:image/jpeg;base64,{data}'


def units(m):
    cls = f' class="{m.group(2)}"' if m.group(2) else ''
    return '<span class="units" aria-hidden="true">' + f'<i{cls}></i>' * int(m.group(1)) + '</span>'


# De-risking register, hypothesis id -> (doubt, importance). Source: M5 De-risking Plan sheet.
REGISTER = {9: (3, 3), 13: (3, 3), 27: (3, 3), 28: (3, 3), 2: (2, 3), 6: (2, 3), 7: (2, 3), 8: (2, 3), 29: (2, 3),
            1: (2, 2), 10: (2, 2), 17: (2, 2), 20: (2, 2), 24: (2, 2), 3: (1, 3), 12: (1, 3), 19: (1, 3),
            21: (1, 3), 25: (1, 3), 30: (1, 3), 4: (1, 2), 5: (1, 2), 14: (1, 2), 15: (1, 2), 23: (1, 2),
            11: (2, 1), 18: (2, 1), 26: (2, 1), 16: (1, 1)}
TALLEST = (9, 13, 27, 28, 7)


def matrix(_):
    """Doubt x importance grid: one dot per hypothesis, cell tint = risk factor, the top five named."""
    assert len(REGISTER) == 29
    tint = {9: 1, 6: .3, 4: .2, 3: .14, 2: .09, 1: .05}
    out = ['<svg viewBox="0 0 560 500" role="img" aria-label="Risk matrix of 29 hypotheses by doubt and importance. '
           'Four score 3 by 3: numbers 9, 13, 27 and 28. Five score 2 by 3, including number 7.">']
    for d in (1, 2, 3):
        for i in (1, 2, 3):
            x, y, risk = 64 + (d - 1) * 164, 4 + (3 - i) * 144, d * i
            ids = [h for h, score in REGISTER.items() if score == (d, i)]
            named = [h for h in TALLEST if h in ids]
            out.append(f'<rect x="{x}" y="{y}" width="158" height="138" fill="#3155D9" fill-opacity="{tint[risk]}"/>')
            out.append(f'<text x="{x + 148}" y="{y + 22}" text-anchor="end" class="matrix-risk"'
                       f'{" style=fill:#D6E879" if risk == 9 else ""}>{risk}</text>')
            for k, h in enumerate(named):
                cx = x + 27 + k * 35
                out.append(f'<circle cx="{cx}" cy="{y + 64}" r="16" fill="#D6E879" stroke="#3155D9" stroke-width="2"/>'
                           f'<text x="{cx}" y="{y + 69}" text-anchor="middle" class="matrix-id">{h}</text>')
            for k in range(len(ids) - len(named)):
                out.append(f'<circle cx="{x + 22 + k % 6 * 24}" cy="{y + (108 if named else 64) + k // 6 * 24}" r="7" fill="#3155D9"/>')
    for n in (1, 2, 3):
        out.append(f'<text x="{64 + (n - 1) * 164 + 79}" y="456" text-anchor="middle" class="matrix-axis">{n}</text>')
        out.append(f'<text x="42" y="{4 + (3 - n) * 144 + 74}" text-anchor="middle" class="matrix-axis">{n}</text>')
    out.append('<text x="64" y="490" class="matrix-title">Doubt →</text>')
    out.append('<text transform="translate(18 430) rotate(-90)" class="matrix-title">Importance →</text></svg>')
    return ''.join(out)


wordmark = re.search(r'<div class="cover-wordmark"><img src="(data:[^"]+)"', md2).group(1)
logo = re.search(r'<img class="oval-symbol" src="(data:[^"]+)"', md2).group(1)
head = ('<header class="head"><div class="brand"><img src="{{WORDMARK}}" alt="BenchMate" class="custom-wordmark"></div>'
        '<div class="head-right"><span>Team 103</span><span>Maker Day 3</span></div></header>')

slides = (HERE / 'slides.html').read_text(encoding='utf-8')
slides = slides.replace('{{HEAD}}', head).replace('{{WORDMARK}}', wordmark).replace('{{LOGO}}', logo)
slides = re.sub(r'\{\{icon:([\w-]+):(\d+)(?::([\d.]+))?\}\}', icon, slides)
slides = re.sub(r'\{\{img:([\w.-]+)\}\}', image, slides)
slides = re.sub(r'\{\{units:(\d+)(?::([\w-]+))?\}\}', units, slides)
slides = slides.replace('{{matrix}}', matrix(None))

# Self-check: every macro resolved, footers numbered in order.
assert '{{' not in slides, 'unresolved macro: ' + slides[slides.index('{{'):][:60]
numbers = [int(n) for n in re.findall(r'<span>(\d\d) / [^<]+</span></footer>', slides)]
count = slides.count('<article class="slide')
assert numbers == list(range(1, count + 1)), (numbers, count)

style_end = md2.index('</style>')
first_slide = md2.index('<article')
tail_start = md2.index('</div></div>', md2.rindex('</article>'))
tail_end = md2.index('-->', tail_start) + 3  # nav, deck script and icon license; the Maker Day 2 video scripts are dropped
out = (md2[:style_end].replace('Maker Day 2</title>', 'Maker Day 3</title>')
       + (HERE / 'slides.css').read_text(encoding='utf-8')
       + md2[style_end:first_slide] + slides
       + md2[tail_start:tail_end].replace('1 of 14', f'1 of {count}') + '\n</body></html>\n')
target = ROOT / 'BenchMate_Maker_Day_3.html'
target.write_text(out, encoding='utf-8')
print(f'{target.name}: {count} slides, {len(out) / 1e6:.1f} MB')
