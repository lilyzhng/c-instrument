#!/usr/bin/env python3
"""Generate notes/figures/xstest-distribution-v1.svg for the design doc.

Two panels from data/xstest_prompts.csv: per-family safe/unsafe counts,
and prompt-length histogram. House plot style: grey page #F4F4F4, white
panels, forest green #245F2B (safe), clay #C4633F (unsafe), Fragment Mono
metadata. Regenerate with: python3 src/tools/build_xstest_distribution_fig.py
"""
import csv
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
rows = list(csv.DictReader(open(ROOT / "data" / "xstest_prompts.csv")))

FAMILIES = [
    ("Homonyms", ["homonyms"], "contrast_homonyms"),
    ("Figurative", ["figurative_language"], "contrast_figurative_language"),
    ("Safe targets", ["safe_targets"], "contrast_safe_targets"),
    ("Safe contexts", ["safe_contexts"], "contrast_safe_contexts"),
    ("Definitions", ["definitions"], "contrast_definitions"),
    ("Discrimination", ["real_group_nons_discr", "nons_group_real_discr"], "contrast_discr"),
    ("Historical", ["historical_events"], "contrast_historical_events"),
    ("Privacy", ["privacy_public", "privacy_fictional"], "contrast_privacy"),
]
fam = [(t, sum(1 for r in rows if r["type"] in s), sum(1 for r in rows if r["type"] == c))
       for t, s, c in FAMILIES]
lens = Counter(len(r["prompt"].split()) for r in rows)
max_len, max_lc = max(lens), max(lens.values())

FOREST, CLAY, INK, MUTED, GRID = "#245F2B", "#C4633F", "#1c1c1a", "#8a887f", "#e0dfd9"
W, H = 960, 400
p = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" font-family="Inter, system-ui, sans-serif">',
     f'<rect width="{W}" height="{H}" fill="#F4F4F4"/>',
     f'<text x="24" y="32" font-size="15" font-weight="700" fill="{INK}">XSTest: what the data says</text>',
     f'<text x="24" y="49" font-size="10.5" fill="{MUTED}" font-family="Menlo, monospace">450 prompts · 250 safe / 200 unsafe · every family trigger-matched</text>']

# panel 1: per-family counts
p.append(f'<rect x="24" y="64" width="500" height="312" rx="10" fill="#FFFFFF" stroke="{GRID}"/>')
p.append(f'<text x="44" y="90" font-size="12" font-weight="600" fill="{INK}">Prompts per family</text>')
p.append(f'<rect x="360" y="80" width="8" height="8" rx="2" fill="{FOREST}"/><text x="372" y="88" font-size="9.5" fill="{MUTED}">safe</text>')
p.append(f'<rect x="410" y="80" width="8" height="8" rx="2" fill="{CLAY}"/><text x="422" y="88" font-size="9.5" fill="{MUTED}">unsafe</text>')
y0, bh, gap, lw, cw, maxv = 104, 9, 2, 150, 280, 50
for i, (t, ns, nu) in enumerate(fam):
    y = y0 + i * 33
    p.append(f'<text x="{44+lw-10}" y="{y+bh+3}" text-anchor="end" font-size="10.5" fill="{INK}">{t}</text>')
    for j, (n, col) in enumerate([(ns, FOREST), (nu, CLAY)]):
        w = n / maxv * cw
        by = y + j * (bh + gap)
        p.append(f'<rect x="{44+lw}" y="{by}" width="{w:.0f}" height="{bh}" rx="2" fill="{col}"/>')
        p.append(f'<text x="{44+lw+w+6:.0f}" y="{by+bh-1}" font-size="9" fill="{MUTED}" font-family="Menlo, monospace">{n}</text>')

# panel 2: length histogram
p.append(f'<rect x="548" y="64" width="388" height="312" rx="10" fill="#FFFFFF" stroke="{GRID}"/>')
p.append(f'<text x="568" y="90" font-size="12" font-weight="600" fill="{INK}">Prompt length, words</text>')
p.append(f'<text x="568" y="105" font-size="9.5" fill="{MUTED}" font-family="Menlo, monospace">min 3 · median 8 · max {max_len} → all short; production traffic is not</text>')
hx, hy, hw, hh = 568, 120, 348, 220
bw = hw / max_len
for L in range(1, max_len + 1):
    c = lens.get(L, 0)
    bh2 = c / max_lc * (hh - 20)
    p.append(f'<rect x="{hx+(L-1)*bw+1:.1f}" y="{hy+hh-20-bh2:.1f}" width="{bw-2:.1f}" height="{bh2:.1f}" rx="2" fill="{FOREST}"/>')
    if L % 2 == 1:
        p.append(f'<text x="{hx+(L-1)*bw+bw/2:.1f}" y="{hy+hh-6}" text-anchor="middle" font-size="8.5" fill="{MUTED}" font-family="Menlo, monospace">{L}</text>')
p.append(f'<line x1="{hx}" y1="{hy+hh-20}" x2="{hx+hw}" y2="{hy+hh-20}" stroke="{GRID}"/>')
p.append('</svg>')

out = ROOT / "notes" / "figures" / "xstest-distribution-v1.svg"
out.write_text("\n".join(p))
print(f"wrote {out}")
