#!/usr/bin/env python3
"""Generate notes/figures/amendment-loop-anim-v1.svg, the animated s4.4.3
amendment due-process loop.

Self-contained SMIL animation, 16s cycle:
  petition (0-4s) -> precedent (4-8s) -> review (8-12s) -> ratify (12-16s).
Same visual language as make_grid_probe_anim_svg.py (shared palette, 16s
cycle, big phase word top-right, manual arrowheads so lines draw before
triangles).
"""

import math
import os

T = 16.0

GREEN = "#245F2B"
GREEN_FILL = "#A9C08F"
CLAY = "#C4633F"
BLUE = "#4A6B8A"
DARK = "#1c1c1c"


def f(t):
    return f"{t / T:.4f}"


def window(t_on, t_off, ramp=0.15):
    return (f'<animate attributeName="opacity" dur="{T:g}s" repeatCount="indefinite" '
            f'values="0;0;1;1;0;0" '
            f'keyTimes="0;{f(t_on)};{f(t_on + ramp)};{f(t_off - ramp)};{f(t_off)};1"/>')


def hold(t_on, t_off=15.4, t_gone=15.8):
    """fade in at t_on, hold until the cycle reset."""
    return (f'<animate attributeName="opacity" dur="{T:g}s" repeatCount="indefinite" '
            f'values="0;0;1;1;0;0" '
            f'keyTimes="0;{f(t_on - 0.05)};{f(t_on + 0.15)};{f(t_off)};{f(t_gone)};1"/>')


def draw_on(t_start, t_end, t_fade=15.4, t_gone=15.8):
    return (f'<animate attributeName="stroke-dashoffset" dur="{T:g}s" repeatCount="indefinite" '
            f'values="100;100;0;0" keyTimes="0;{f(t_start)};{f(t_end)};1"/>'
            f'<animate attributeName="opacity" dur="{T:g}s" repeatCount="indefinite" '
            f'values="0;0;1;1;0;0" '
            f'keyTimes="0;{f(t_start)};{f(t_start + 0.05)};{f(t_fade)};{f(t_gone)};1"/>')


def arrowhead(tip_x, tip_y, from_x, from_y, t_on, color=GREEN,
              t_fade=15.4, t_gone=15.8, size=11):
    """Manual arrowhead so the line draws before the triangle appears."""
    ang = math.degrees(math.atan2(tip_y - from_y, tip_x - from_x))
    return (f'<polygon points="0,0 {-size},{-size * 0.45:g} {-size},{size * 0.45:g}" '
            f'fill="{color}" transform="translate({tip_x:g},{tip_y:g}) rotate({ang:.1f})" '
            f'opacity="0"><animate attributeName="opacity" dur="{T:g}s" '
            f'repeatCount="indefinite" values="0;0;1;1;0;0" '
            f'keyTimes="0;{f(t_on - 0.1)};{f(t_on)};{f(t_fade)};{f(t_gone)};1"/></polygon>')


parts = []
add = parts.append

add('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 540" '
    'font-family="Inter, system-ui, sans-serif">')
add('<rect width="960" height="540" fill="#F4F4F4"/>')
add(f'<text x="24" y="42" font-size="24" font-weight="700" fill="{DARK}">'
    'Amending the constitution</text>')

# --- phase word (top right) ------------------------------------------------
phases = [("data petition", GREEN, 0.0, 4.0), ("regression", BLUE, 4.0, 8.0),
          ("red-team", CLAY, 8.0, 12.0), ("merge", GREEN, 12.0, 16.0)]
for name, col, t0, t1 in phases:
    if t0 == 0:
        vals, kts = "1;1;0;0", f"0;{f(t1 - 0.2)};{f(t1)};1"
    elif t1 == T:
        vals, kts = "0;0;1;1", f"0;{f(t0)};{f(t0 + 0.2)};1"
    else:
        vals, kts = "0;0;1;1;0;0", f"0;{f(t0)};{f(t0 + 0.2)};{f(t1 - 0.2)};{f(t1)};1"
    add(f'<text x="936" y="46" font-size="32" font-weight="800" fill="{col}" '
        f'text-anchor="end" opacity="0">{name}'
        f'<animate attributeName="opacity" dur="{T:g}s" repeatCount="indefinite" '
        f'values="{vals}" keyTimes="{kts}"/></text>')

# --- left: mini probe grid with a loophole cell ----------------------------
GX, GY, P, C = 64, 140, 34, 29
for r in range(3):
    for c in range(3):
        x, y = GX + c * P, GY + r * P
        if (r, c) == (1, 1):
            add(f'<rect x="{x}" y="{y}" width="{C}" height="{C}" fill="{CLAY}" '
                f'fill-opacity="0.9" stroke="#8f3f22" stroke-width="1.4">'
                f'<animate attributeName="fill-opacity" dur="1.6s" repeatCount="indefinite" '
                f'values="0.9;0.45;0.9"/></rect>')
        else:
            add(f'<rect x="{x}" y="{y}" width="{C}" height="{C}" fill="{GREEN_FILL}" '
                f'stroke="{GREEN}" stroke-width="0.8"/>')
add(f'<text x="{GX + 1.5 * P:g}" y="{GY + 3 * P + 24}" font-size="13" '
    f'font-weight="600" fill="#8f3f22" text-anchor="middle">clause gap found</text>')

# petition card slides out of the grid toward the first gate
add(f'<g opacity="0">'
    f'<rect x="70" y="300" width="150" height="52" rx="8" fill="#FFFFFF" '
    f'stroke="{GREEN}" stroke-width="1.4"/>'
    f'<text x="145" y="321" font-size="13" font-weight="700" fill="{GREEN}" '
    f'text-anchor="middle">data petition</text>'
    f'<text x="145" y="339" font-size="11" fill="#555" text-anchor="middle">'
    f'probe evidence attached</text>{hold(0.6)}</g>')
add(f'<line x1="{GX + 1.5 * P + 14:g}" y1="{GY + 1.5 * P + 14:g}" x2="145" y2="296" '
    f'stroke="#8f3f22" stroke-width="1.4" stroke-dasharray="4 3" opacity="0">'
    f'{hold(0.4)}</line>')

# --- the three gates -------------------------------------------------------
GATE_Y, GATE_W, GATE_H = 260, 168, 74
gates = [
    (252, "evidence bar", "standing: cell error counts", GREEN, 0.0, 4.0),
    (462, "regression test", "precedent: re-judge dev rows", BLUE, 4.0, 8.0),
    (672, "red-team review", "a judge argues the other side", CLAY, 8.0, 12.0),
]
for gx, name, sub, col, t0, t1 in gates:
    cx = gx + GATE_W / 2
    add(f'<rect x="{gx}" y="{GATE_Y}" width="{GATE_W}" height="{GATE_H}" rx="9" '
        f'fill="#FFFFFF" stroke="{col}" stroke-width="1.6"/>')
    # highlight wash while the gate is deliberating
    add(f'<rect x="{gx}" y="{GATE_Y}" width="{GATE_W}" height="{GATE_H}" rx="9" '
        f'fill="{col}" opacity="0">'
        f'<animate attributeName="opacity" dur="{T:g}s" repeatCount="indefinite" '
        f'values="0;0;0.14;0.14;0;0" '
        f'keyTimes="0;{f(t0)};{f(t0 + 0.3)};{f(t1 - 0.3)};{f(t1)};1"/></rect>')
    add(f'<text x="{cx:g}" y="{GATE_Y + 30}" font-size="15" font-weight="700" '
        f'fill="{col}" text-anchor="middle">{name}</text>')
    add(f'<text x="{cx:g}" y="{GATE_Y + 51}" font-size="11.5" fill="#555" '
        f'text-anchor="middle">{sub}</text>')
    # check mark when the gate passes (end of its phase)
    add(f'<g opacity="0"><circle cx="{gx + GATE_W - 16}" cy="{GATE_Y + 16}" r="10" '
        f'fill="{GREEN_FILL}" stroke="{GREEN}" stroke-width="1.2"/>'
        f'<path d="M{gx + GATE_W - 21},{GATE_Y + 16} l3.5,4 l6,-8" fill="none" '
        f'stroke="{GREEN}" stroke-width="2" stroke-linecap="round"/>{hold(t1 - 0.4)}</g>')

# petition card -> gate 1, then gate -> gate arrows (line first, triangle after)
links = [
    ((224, 326), (246, GATE_Y + GATE_H / 2), 1.0, 1.8),
    ((252 + GATE_W + 6, GATE_Y + GATE_H / 2), (456, GATE_Y + GATE_H / 2), 3.6, 4.4),
    ((462 + GATE_W + 6, GATE_Y + GATE_H / 2), (666, GATE_Y + GATE_H / 2), 7.6, 8.4),
]
for (x1, y1), (x2, y2), t0, t1 in links:
    add(f'<path d="M{x1:g},{y1:g} L{x2:g},{y2:g}" fill="none" stroke="{GREEN}" '
        f'stroke-width="2" pathLength="100" stroke-dasharray="100" '
        f'stroke-dashoffset="100" opacity="0">{draw_on(t0, t1)}</path>')
    add(arrowhead(x2, y2, x1, y1, t_on=t1))

# reject branch: unjustified precedent flips kill the proposal
add(f'<path d="M{462 + GATE_W / 2:g},{GATE_Y + GATE_H} L{462 + GATE_W / 2:g},408" '
    f'fill="none" stroke="#8f3f22" stroke-width="1.4" stroke-dasharray="5 4" opacity="0.55"/>')
add(f'<polygon points="0,0 -9,-4 -9,4" fill="#8f3f22" opacity="0.55" '
    f'transform="translate({462 + GATE_W / 2:g},410) rotate(90)"/>')
add(f'<text x="{462 + GATE_W / 2:g}" y="428" font-size="11.5" fill="#8f3f22" '
    f'text-anchor="middle">unjustified flips -&gt; rejected</text>')

# --- right: the constitution document --------------------------------------
DX, DY, DW, DH = 806, 118, 126, 158
add(f'<rect x="{DX}" y="{DY}" width="{DW}" height="{DH}" rx="6" fill="#FFFFFF" '
    f'stroke="{GREEN}" stroke-width="1.8"/>')
for i in range(5):
    add(f'<line x1="{DX + 16}" y1="{DY + 58 + i * 16}" x2="{DX + DW - 16}" '
        f'y2="{DY + 58 + i * 16}" stroke="#c9c9c9" stroke-width="2"/>')
# the amended clause line turns green on ratify
add(f'<line x1="{DX + 16}" y1="{DY + 90}" x2="{DX + DW - 16}" y2="{DY + 90}" '
    f'stroke="{GREEN}" stroke-width="3" opacity="0">{hold(13.0)}</line>')
add(f'<text x="{DX + DW / 2:g}" y="{DY + 26}" font-size="13" font-weight="700" '
    f'fill="{GREEN}" text-anchor="middle">constitution</text>')
add(f'<text x="{DX + DW / 2:g}" y="{DY + 44}" font-size="12" fill="#555" '
    f'text-anchor="middle" opacity="1">v2'
    f'<animate attributeName="opacity" dur="{T:g}s" repeatCount="indefinite" '
    f'values="1;1;0;0;1" keyTimes="0;{f(12.9)};{f(13.1)};{f(15.6)};1"/></text>')
add(f'<text x="{DX + DW / 2:g}" y="{DY + 44}" font-size="12" font-weight="700" '
    f'fill="{GREEN}" text-anchor="middle" opacity="0">v3'
    f'<animate attributeName="opacity" dur="{T:g}s" repeatCount="indefinite" '
    f'values="0;0;1;1;0;0" keyTimes="0;{f(12.9)};{f(13.1)};{f(15.4)};{f(15.8)};1"/></text>')
# ratified stamp
add(f'<g opacity="0" transform="rotate(-12 {DX + DW / 2:g} {DY + DH - 34})">'
    f'<rect x="{DX + 18}" y="{DY + DH - 48}" width="{DW - 36}" height="28" rx="5" '
    f'fill="none" stroke="{CLAY}" stroke-width="2.4"/>'
    f'<text x="{DX + DW / 2:g}" y="{DY + DH - 28}" font-size="14" font-weight="800" '
    f'fill="{CLAY}" text-anchor="middle">MERGED</text></g>')
parts[-1] = parts[-1].replace('</g>', f'{hold(13.4)}</g>')

# gate 3 -> document (draws early in ratify)
add(f'<path d="M{672 + GATE_W + 6:g},{GATE_Y + GATE_H / 2:g} C880,{GATE_Y + GATE_H / 2 - 4:g} '
    f'{DX + DW / 2:g},{DY + DH + 56} {DX + DW / 2:g},{DY + DH + 6}" fill="none" '
    f'stroke="{GREEN}" stroke-width="2" pathLength="100" stroke-dasharray="100" '
    f'stroke-dashoffset="100" opacity="0">{draw_on(11.8, 12.8)}</path>')
add(arrowhead(DX + DW / 2, DY + DH + 6, DX + DW / 2, DY + DH + 56, t_on=12.8))

# loop back: document -> grid, ex-post review (line first, triangle at the end)
add(f'<path d="M{DX},{DY + 30} C560,58 220,60 {GX + 3 * P + 10},{GY + 24}" fill="none" '
    f'stroke="{GREEN}" stroke-width="2" pathLength="100" stroke-dasharray="100" '
    f'stroke-dashoffset="100" opacity="0">{draw_on(13.6, 15.0, t_fade=15.6, t_gone=15.9)}</path>')
add(arrowhead(GX + 3 * P + 10, GY + 24, 260, 62, t_on=15.0, t_fade=15.6, t_gone=15.9))
add(f'<text x="480" y="82" font-size="13" font-weight="600" fill="{GREEN}" '
    f'text-anchor="middle" opacity="0">re-probe: is the gap closed?'
    f'{window(14.0, 15.8, ramp=0.2)}</text>')

# what the merge triggers downstream (data + training, not just paperwork)
add(f'<text x="480" y="486" font-size="13" font-weight="600" fill="{GREEN}" '
    f'text-anchor="middle" opacity="0">constitution v3 -&gt; regenerate the cell\'s data '
    f'-&gt; retrain{window(13.2, 15.8, ramp=0.2)}</text>')

add('</svg>')

out = os.path.join(os.path.dirname(__file__), "..", "notes", "figures",
                   "amendment-loop-anim-v1.svg")
with open(os.path.abspath(out), "w") as fh:
    fh.write("\n".join(parts) + "\n")
print("wrote", os.path.abspath(out))
