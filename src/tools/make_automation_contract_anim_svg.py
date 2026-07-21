#!/usr/bin/env python3
"""Generate notes/figures/data-iteration-loop-v1.svg (Figure 9), the animated
automation contract.

Same visual language as make_grid_probe_anim_svg.py / make_amendment_anim_svg.py:
16s SMIL cycle, big phase word top-right, minimal text, icons over words.
Five stages light up in turn; the stage's artifact card travels the edge to the
next stage. Robot badge = runs itself, human badge = human on flag.
"""

import os

T = 16.0

GREEN = "#245F2B"
GREEN_FILL = "#A9C08F"
CLAY = "#C4633F"
BLUE = "#4A6B8A"
DARK = "#1c1c1c"
GREY = "#9a9a9a"


def f(t):
    return f"{t / T:.4f}"


def window(t_on, t_off, ramp=0.12):
    return (f'<animate attributeName="opacity" dur="{T:g}s" repeatCount="indefinite" '
            f'values="0;0;1;1;0;0" '
            f'keyTimes="0;{f(t_on)};{f(t_on + ramp)};{f(t_off - ramp)};{f(t_off)};1"/>')


parts = []
add = parts.append

add('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 540" '
    'font-family="Inter, system-ui, sans-serif">')
add('<defs>')
add(f'<marker id="aG" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
    f'markerHeight="7" orient="auto-start-reverse">'
    f'<path d="M0,0 L10,5 L0,10 z" fill="#b9b9b9"/></marker>')
add('</defs>')
add('<rect width="960" height="540" fill="#F4F4F4"/>')
add(f'<text x="24" y="42" font-size="24" font-weight="700" fill="{DARK}">'
    'The automation contract</text>')

# --- phase word (top right) ------------------------------------------------
SLOT = T / 5
phases = [("measure", GREEN), ("decide", BLUE), ("generate", GREEN),
          ("audit", BLUE), ("train", GREEN)]
for i, (name, col) in enumerate(phases):
    t0, t1 = i * SLOT, (i + 1) * SLOT
    if i == 0:
        vals, kts = "1;1;0;0", f"0;{f(t1 - 0.2)};{f(t1)};1"
    elif i == len(phases) - 1:
        vals, kts = "0;0;1;1", f"0;{f(t0)};{f(t0 + 0.2)};1"
    else:
        vals, kts = "0;0;1;1;0;0", f"0;{f(t0)};{f(t0 + 0.2)};{f(t1 - 0.2)};{f(t1)};1"
    add(f'<text x="936" y="46" font-size="32" font-weight="800" fill="{col}" '
        f'text-anchor="end" opacity="0">{name}'
        f'<animate attributeName="opacity" dur="{T:g}s" repeatCount="indefinite" '
        f'values="{vals}" keyTimes="{kts}"/></text>')


def robot(x, y, s=1.0):
    """robot badge = automated"""
    return (f'<g transform="translate({x},{y}) scale({s})">'
            f'<rect x="-9" y="-7" width="18" height="14" rx="4" fill="#FFFFFF" '
            f'stroke="{GREEN}" stroke-width="1.4"/>'
            f'<circle cx="-3.5" cy="0" r="1.8" fill="{GREEN}"/>'
            f'<circle cx="3.5" cy="0" r="1.8" fill="{GREEN}"/>'
            f'<line x1="0" y1="-7" x2="0" y2="-11" stroke="{GREEN}" stroke-width="1.4"/>'
            f'<circle cx="0" cy="-12" r="1.6" fill="{GREEN}"/></g>')


def human(x, y, s=1.0):
    """human badge = human on flag"""
    return (f'<g transform="translate({x},{y}) scale({s})" fill="none" '
            f'stroke="{BLUE}" stroke-width="1.6">'
            f'<circle cx="0" cy="-5" r="4.2" fill="#FFFFFF"/>'
            f'<path d="M-7,8 C-7,1 7,1 7,8" fill="#FFFFFF"/></g>')


# --- stage boxes -----------------------------------------------------------
BW, BH = 172, 86
stages = [
    # x, y, title, icon key, badge fn, phase idx
    (100, 110, "measure", "probe", robot, 0),
    (415, 110, "decide", "route", robot, 1),
    (730, 110, "generate", "rows", robot, 2),
    (730, 330, "audit", "eye", human, 3),
    (415, 330, "train", "chart", robot, 4),
]


def icon(kind, cx, cy):
    if kind == "probe":  # magnifier over a mini grid
        g = ""
        for i, fill in enumerate([GREEN_FILL, "#E4B04A", "#E4B04A", GREEN_FILL]):
            g += (f'<rect x="{cx - 14 + (i % 2) * 13}" y="{cy - 14 + (i // 2) * 13}" '
                  f'width="11" height="11" fill="{fill}" stroke="{GREEN}" stroke-width="0.7"/>')
        g += (f'<circle cx="{cx + 6}" cy="{cy + 4}" r="9" fill="none" stroke="{DARK}" '
              f'stroke-width="2.2"/>'
              f'<line x1="{cx + 12.5}" y1="{cy + 10.5}" x2="{cx + 19}" y2="{cy + 17}" '
              f'stroke="{DARK}" stroke-width="2.6" stroke-linecap="round"/>')
        return g
    if kind == "route":  # one dot forking into three arrows
        g = f'<circle cx="{cx - 12}" cy="{cy}" r="3.4" fill="{BLUE}"/>'
        for dy, col in ((-11, GREEN), (0, CLAY), (11, GREY)):
            g += (f'<path d="M{cx - 8},{cy} C{cx},{cy} {cx},{cy + dy} {cx + 12},{cy + dy}" '
                  f'fill="none" stroke="{col}" stroke-width="2.2"/>'
                  f'<polygon points="0,0 -7,-3 -7,3" fill="{col}" '
                  f'transform="translate({cx + 15},{cy + dy})"/>')
        return g
    if kind == "rows":  # rows being stacked, plus sign
        g = ""
        for i in range(3):
            g += (f'<rect x="{cx - 16}" y="{cy - 12 + i * 9}" width="26" height="6" rx="2" '
                  f'fill="{GREEN_FILL}" stroke="{GREEN}" stroke-width="0.8"/>')
        g += (f'<line x1="{cx + 17}" y1="{cy - 6}" x2="{cx + 17}" y2="{cy + 6}" '
              f'stroke="{GREEN}" stroke-width="2.4" stroke-linecap="round"/>'
              f'<line x1="{cx + 11}" y1="{cy}" x2="{cx + 23}" y2="{cy}" '
              f'stroke="{GREEN}" stroke-width="2.4" stroke-linecap="round"/>')
        return g
    if kind == "eye":  # audit eye
        return (f'<path d="M{cx - 17},{cy} C{cx - 8},{cy - 12} {cx + 8},{cy - 12} {cx + 17},{cy} '
                f'C{cx + 8},{cy + 12} {cx - 8},{cy + 12} {cx - 17},{cy} Z" fill="#FFFFFF" '
                f'stroke="{BLUE}" stroke-width="2"/>'
                f'<circle cx="{cx}" cy="{cy}" r="5" fill="{BLUE}"/>')
    if kind == "chart":  # training curve going up
        return (f'<path d="M{cx - 16},{cy + 10} L{cx - 6},{cy + 2} L{cx + 2},{cy + 6} '
                f'L{cx + 14},{cy - 9}" fill="none" stroke="{GREEN}" stroke-width="2.6" '
                f'stroke-linecap="round" stroke-linejoin="round"/>'
                f'<polygon points="0,0 -8,-1 -3,7" fill="{GREEN}" '
                f'transform="translate({cx + 16},{cy - 11})"/>')
    return ""


for x, y, title, ic, badge, pi in stages:
    t0, t1 = pi * SLOT, (pi + 1) * SLOT
    add(f'<rect x="{x}" y="{y}" width="{BW}" height="{BH}" rx="10" fill="#FFFFFF" '
        f'stroke="{GREEN if badge is robot else BLUE}" stroke-width="1.6"/>')
    # highlight wash while the stage runs
    add(f'<rect x="{x}" y="{y}" width="{BW}" height="{BH}" rx="10" '
        f'fill="{GREEN if badge is robot else BLUE}" opacity="0">'
        f'<animate attributeName="opacity" dur="{T:g}s" repeatCount="indefinite" '
        f'values="0;0;0.13;0.13;0;0" '
        f'keyTimes="0;{f(t0)};{f(t0 + 0.25)};{f(t1 - 0.25)};{f(t1)};1"/></rect>')
    add(icon(ic, x + 38, y + BH / 2))
    add(f'<text x="{x + 74}" y="{y + BH / 2 + 6:g}" font-size="17" font-weight="700" '
        f'fill="{DARK}">{title}</text>')
    add(badge(x + BW - 20, y + 20))

# --- legend: robot vs human ------------------------------------------------
add(robot(120, 480))
add(f'<text x="140" y="485" font-size="12.5" fill="#555">runs itself</text>')
add(human(240, 479))
add(f'<text x="258" y="485" font-size="12.5" fill="#555">human on flag</text>')

# --- static edges ----------------------------------------------------------
edges = [
    "M272,153 L411,153",                       # measure -> decide
    "M587,153 L726,153",                       # decide -> generate
    "M816,196 L816,326",                       # generate -> audit (down)
    "M730,373 L587,373",                       # audit -> train (left)
    "M415,373 C230,373 186,300 186,200",       # train -> measure (loop back)
]
for d in edges:
    add(f'<path d="{d}" fill="none" stroke="#b9b9b9" stroke-width="2" '
        f'marker-end="url(#aG)"/>')

# --- artifact cards traveling each edge ------------------------------------
CARD_W, CARD_H = 66, 26


def card(inner, label_w=CARD_W):
    return (f'<rect x="{-label_w / 2:g}" y="{-CARD_H / 2:g}" width="{label_w}" '
            f'height="{CARD_H}" rx="5" fill="#FFFFFF" stroke="{GREEN}" '
            f'stroke-width="1.3"/>{inner}')


heat = "".join(
    f'<rect x="{-24 + i * 11}" y="-6" width="9" height="12" fill="{c}" '
    f'stroke="{GREEN}" stroke-width="0.5"/>'
    for i, c in enumerate([GREEN_FILL, "#E4B04A", CLAY, GREEN_FILL]))
heat += f'<text x="8" y="4" font-size="10.5" fill="#555">heatmap</text>'

budget = (f'<circle cx="-20" cy="0" r="6.5" fill="#E4B04A" stroke="#a97c1e" '
          f'stroke-width="1"/><text x="-23" y="3.5" font-size="9" fill="#5d4408" '
          f'font-weight="700">$</text>'
          f'<text x="-8" y="4" font-size="10.5" fill="#555">budget</text>')

pack = "".join(
    f'<rect x="-24" y="{-8 + i * 6}" width="18" height="4" rx="1.5" fill="{GREEN_FILL}"/>'
    for i in range(3))
pack += f'<text x="0" y="4" font-size="10.5" fill="#555">pack</text>'

verdict = (f'<path d="M-22,-1 l4,5 l7,-9" fill="none" stroke="{GREEN}" '
           f'stroke-width="2.4" stroke-linecap="round"/>'
           f'<text x="-6" y="4" font-size="10.5" fill="#555">verdict</text>')

ckpt = (f'<path d="M-24,5 L-16,-1 L-10,2 L-2,-5" fill="none" stroke="{GREEN}" '
        f'stroke-width="2"/><text x="2" y="4" font-size="10.5" fill="#555">ckpt</text>')

cards = [
    # motion path, inner, width, phase idx (card moves at the END of its stage)
    ("M272,153 L411,153", heat, 70, 0),
    ("M587,153 L726,153", budget, 66, 1),
    ("M816,196 L816,326", pack, 60, 2),
    ("M730,373 L587,373", verdict, 66, 3),
    ("M415,373 C230,373 186,300 186,200", ckpt, 58, 4),
]
for mpath, inner, w, pi in cards:
    t_go = (pi + 1) * SLOT - 1.1          # start moving late in the stage
    t_arrive = (pi + 1) * SLOT - 0.15
    add(f'<g opacity="0">{card(inner, w)}'
        f'<animateMotion dur="{T:g}s" repeatCount="indefinite" path="{mpath}" '
        f'keyPoints="0;0;1;1" keyTimes="0;{f(t_go)};{f(t_arrive)};1" '
        f'calcMode="linear"/>'
        f'{window(t_go - 0.15, min(t_arrive + 0.3, 15.9))}</g>')

# --- XSTest scoreboard, read-only ------------------------------------------
add(f'<rect x="100" y="330" width="172" height="86" rx="10" fill="none" '
    f'stroke="#999" stroke-width="1.4" stroke-dasharray="6 4"/>')
add(icon("eye", 138, 373).replace(BLUE, "#888"))
add(f'<text x="166" y="368" font-size="15" font-weight="700" fill="#777">XSTest</text>')
add(f'<text x="166" y="387" font-size="11.5" fill="#999">read-only</text>')
# train glances at the scoreboard (dashed, no write-back)
add(f'<path d="M411,392 L280,392" fill="none" stroke="#bbb" stroke-width="1.6" '
    f'stroke-dasharray="4 4" marker-end="url(#aG)"/>')

add('</svg>')

out = os.path.join(os.path.dirname(__file__), "..", "notes", "figures",
                   "data-iteration-loop-v1.svg")
with open(os.path.abspath(out), "w") as fh:
    fh.write("\n".join(parts) + "\n")
print("wrote", os.path.abspath(out))
