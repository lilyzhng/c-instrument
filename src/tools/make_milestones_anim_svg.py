#!/usr/bin/env python3
"""Generate notes/figures/milestones-anim-v1.svg — deliverable trail from PathFinder.

Plays once, then freezes (SMIL fill="freeze", no repeat). Milestones mirror
trace-explorer.html: baseline, four corpus versions (v1→it6), ship checkpoints
exp4 and exp15, PathFinder as the trace artifact.
"""

import os

GREEN = "#245F2B"
BLUE = "#4A6B8A"
GOLD = "#B8860B"
DARK = "#1c1c1c"

# OR = 1−safe_acc; UR = 1−unsafe_acc (plain under-refusal). From trace-explorer exp1/4/15.
milestones = [
    ("baseline", "Nemotron-4B", "OR 22.4% · UR 2.5%", BLUE, False),
    ("constitution v1", "11 topic charters", "340 grid cells", GREEN, False),
    ("corpus v1", "2,105 rows", "decon clean", GREEN, False),
    ("exp4 ship", "group B · v1 s57", "OR 16.8% · UR 3.0%", BLUE, False),
    ("corpus v2", "2,326 rows", "disguise anchors", GREEN, False),
    ("corpus v3", "2,513 rows", "ASR closed", GREEN, False),
    ("corpus it6", "7,241 rows", "8 packs", GREEN, False),
    ("exp15 ship", "group F · it6 s125", "OR 12.8% · UR 3.0%", GOLD, False),
    ("PathFinder", "5 groups · 19 runs", "lineage traced", DARK, False),
]

N = len(milestones)
T_FIRST, T_GAP = 1.0, 1.5
T_LAST = T_FIRST + (N - 1) * T_GAP
T = T_LAST + 1.2  # last node must finish fading in before animation ends


def f(t):
    return f"{min(t / T, 1.0):.4f}"


def hold(t_on):
    return (f'<animate attributeName="opacity" dur="{T:g}s" fill="freeze" '
            f'values="0;0;1;1" '
            f'keyTimes="0;{f(t_on - 0.05)};{f(t_on + 0.2)};1"/>')


parts = []
add = parts.append

add('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 420" '
    'font-family="Inter, system-ui, sans-serif">')
add('<rect width="960" height="420" fill="#F4F4F4"/>')

add(f'<circle cx="700" cy="36" r="6" fill="{GREEN}"/>')
add(f'<text x="712" y="41" font-size="13" fill="#555">data</text>')
add(f'<circle cx="772" cy="36" r="6" fill="{BLUE}"/>')
add(f'<text x="784" y="41" font-size="13" fill="#555">model</text>')
add(f'<circle cx="844" cy="36" r="6" fill="{GOLD}"/>')
add(f'<text x="856" y="41" font-size="13" fill="#555">ship</text>')

Y = 220
X0, X1 = 80, 880  # inset so end labels aren't clipped
STEP = (X1 - X0) / (N - 1)

add(f'<line x1="{X0}" y1="{Y}" x2="{X1}" y2="{Y}" stroke="#d9d9d9" stroke-width="2"/>')
t_draw0, t_draw1 = T_FIRST, T_LAST
add(f'<path d="M{X0},{Y} L{X1},{Y}" fill="none" stroke="{GREEN}" stroke-width="3" '
    f'pathLength="100" stroke-dasharray="100" stroke-dashoffset="100" opacity="0">'
    f'<animate attributeName="stroke-dashoffset" dur="{T:g}s" fill="freeze" '
    f'values="100;100;0" keyTimes="0;{f(t_draw0)};{f(t_draw1)}"/>'
    f'<animate attributeName="opacity" dur="{T:g}s" fill="freeze" '
    f'values="0;0;1" keyTimes="0;{f(t_draw0 - 0.05)};{f(t_draw0)}"/></path>')

for i, (title, sub1, sub2, col, dashed) in enumerate(milestones):
    x = X0 + i * STEP
    t_on = T_FIRST + i * T_GAP
    above = i % 2 == 0
    ty = Y - 96 if above else Y + 44
    stalk_y1, stalk_y2 = (Y - 14, Y - 40) if above else (Y + 14, Y + 32)
    dash = ' stroke-dasharray="5 4"' if dashed else ""
    node = (f'<circle cx="{x:g}" cy="{Y}" r="11" fill="#FFFFFF" stroke="{col}" '
            f'stroke-width="2.5"{dash}/>')
    if not dashed:
        node += f'<circle cx="{x:g}" cy="{Y}" r="5" fill="{col}"/>'
    node += (f'<line x1="{x:g}" y1="{stalk_y1}" x2="{x:g}" y2="{stalk_y2}" '
             f'stroke="{col}" stroke-width="1.2"{dash}/>')
    node += (f'<text x="{x:g}" y="{ty}" font-size="15" font-weight="700" '
             f'fill="{col}" text-anchor="middle">{title}</text>')
    node += (f'<text x="{x:g}" y="{ty + 20}" font-size="11" fill="#555" '
             f'text-anchor="middle">{sub1}</text>')
    node += (f'<text x="{x:g}" y="{ty + 35}" font-size="11" fill="#555" '
             f'text-anchor="middle">{sub2}</text>')
    if not dashed:
        node += (f'<circle cx="{x:g}" cy="{Y}" r="11" fill="none" stroke="{col}" '
                 f'stroke-width="2" opacity="0">'
                 f'<animate attributeName="r" dur="{T:g}s" fill="freeze" '
                 f'values="11;11;26" keyTimes="0;{f(t_on)};{f(t_on + 0.5)}"/>'
                 f'<animate attributeName="opacity" dur="{T:g}s" fill="freeze" '
                 f'values="0;0;0.7;0" keyTimes="0;{f(t_on)};{f(t_on + 0.1)};'
                 f'{f(t_on + 0.55)}"/></circle>')
    add(f'<g opacity="0">{node}{hold(t_on)}</g>')

add('</svg>')

out = os.path.join(os.path.dirname(__file__), "..", "notes", "figures",
                   "milestones-anim-v1.svg")
with open(os.path.abspath(out), "w") as fh:
    fh.write("\n".join(parts) + "\n")
print("wrote", os.path.abspath(out))
