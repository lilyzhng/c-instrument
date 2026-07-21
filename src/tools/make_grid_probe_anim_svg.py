#!/usr/bin/env python3
"""Generate notes/figures/grid-probe-anim-v1.svg, the animated s4.4 data-grid-probing loop.

Self-contained SMIL animation, 16s cycle:
  probe sweep (0.5-3.5s) -> attack sweep (4.5-7.5s) -> route dots (8.5-11.5s) -> train arrows (12-15s) -> reset.
All animations share dur=16s + keyTimes so phases stay in sync.
"""

import math
import os

T = 16.0  # cycle seconds


def f(t):
    """seconds -> keyTime fraction, trimmed."""
    return f"{t / T:.4f}"


def f2(t):
    """seconds -> absolute begin= string, trimmed."""
    return f"{t:.2f}"


# --- grid data -------------------------------------------------------------
# '.' empty  'g' healthy  'w' wavering  'x' confidently wrong
# 'a' healthy at probe time, flips to clay (ASR dirty) during attack
ROWS = [
    ("privacy",    "gwg.gaaw.g"),
    ("violence",   "ggwg.ag.w."),
    ("cyber",      "wggwggag.g"),
    ("fraud",      "gw.gwaagg."),
    ("weapons",    "gggw.wa.gw"),
    ("drugs",      "ggwggg.w.g"),
    ("copyright",  ".wg.xgg.g."),
    ("reg-advice", "w.gxga.gw."),
]
NCOL = 10
X0, Y0, PITCH, CELL = 126, 104, 34, 29

GREEN = "#245F2B"
GREEN_FILL = "#A9C08F"
CLAY = "#C4633F"
BLUE = "#4A6B8A"
GREY_EMPTY = "#F0F0EC"
DARK = "#1c1c1c"
WRONG = "#6b6b6b"

GRID_W = NCOL * PITCH - (PITCH - CELL)          # 236
GRID_H = len(ROWS) * PITCH - (PITCH - CELL)     # 188
GRID_R = X0 + GRID_W                            # right edge


def cxy(r, c):
    return X0 + c * PITCH, Y0 + r * PITCH


def opacity_anim(t_on, t_hold_end=15.4, t_off=15.8):
    """fade in at t_on, hold, fade out at cycle end (reset)."""
    return (f'<animate attributeName="opacity" dur="{T:g}s" repeatCount="indefinite" '
            f'values="0;0;1;1;0;0" '
            f'keyTimes="0;{f(t_on - 0.05)};{f(t_on + 0.15)};{f(t_hold_end)};{f(t_off)};1"/>')


def window_anim(t_on, t_off, ramp=0.1):
    """visible only inside [t_on, t_off]."""
    return (f'<animate attributeName="opacity" dur="{T:g}s" repeatCount="indefinite" '
            f'values="0;0;1;1;0;0" '
            f'keyTimes="0;{f(t_on)};{f(t_on + ramp)};{f(t_off - ramp)};{f(t_off)};1"/>')


def draw_on(t_start, t_end, t_fade=15.4, t_gone=15.8):
    """stroke draw-on via pathLength=100 dashoffset, then fade at reset."""
    return (f'<animate attributeName="stroke-dashoffset" dur="{T:g}s" repeatCount="indefinite" '
            f'values="100;100;0;0" keyTimes="0;{f(t_start)};{f(t_end)};1"/>'
            f'<animate attributeName="opacity" dur="{T:g}s" repeatCount="indefinite" '
            f'values="0;0;1;1;0;0" '
            f'keyTimes="0;{f(t_start)};{f(t_start + 0.05)};{f(t_fade)};{f(t_gone)};1"/>')


parts = []
add = parts.append

add('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 540" '
    'font-family="Inter, system-ui, sans-serif">')
add('<defs>')
add(f'<pattern id="wav" width="6" height="6" patternUnits="userSpaceOnUse" '
    f'patternTransform="rotate(45)"><rect width="6" height="6" fill="#FFFFFF"/>'
    f'<rect width="3" height="6" fill="{GREEN_FILL}"/></pattern>')
for mid, col in (("arrG", GREEN), ("arrGy", "#9a9a9a"), ("arrC", CLAY), ("arrN", "#9a9a9a")):
    add(f'<marker id="{mid}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
        f'markerHeight="7" orient="auto-start-reverse">'
        f'<path d="M0,0 L10,5 L0,10 z" fill="{col}"/></marker>')
add('</defs>')

add('<rect width="960" height="540" fill="#F4F4F4"/>')
add(f'<text x="24" y="42" font-size="24" font-weight="700" fill="{DARK}">'
    'Constitution probing</text>')

# --- phase label (top right) ----------------------------------------------
phases = [("probe", GREEN, 0.0, 4.0), ("attack", CLAY, 4.0, 8.0),
          ("route", BLUE, 8.0, 12.0), ("train", GREEN, 12.0, 16.0)]
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

# --- grid ------------------------------------------------------------------
add(f'<text x="{X0}" y="{Y0 + GRID_H + 14}" font-size="9" fill="#888">topic rows x style columns</text>')
# mark fiction / roleplay columns (staggered so the labels do not overlap)
for c, lbl, dy in ((5, "fiction", 22), (6, "roleplay", 8)):
    x = X0 + c * PITCH + CELL / 2
    add(f'<text x="{x:g}" y="{Y0 - dy}" font-size="11" fill="#8f3f22" '
        f'text-anchor="middle">{lbl}</text>')
    add(f'<line x1="{x:g}" y1="{Y0 - dy + 2}" x2="{x:g}" y2="{Y0 - 2}" '
        f'stroke="#8f3f22" stroke-width="0.6"/>')

add('<g font-size="13" fill="#666" text-anchor="end">')
for r, (label, _) in enumerate(ROWS):
    add(f'<text x="{X0 - 8}" y="{Y0 + r * PITCH + CELL / 2 + 4:g}">{label}</text>')
add('</g>')

# base cells
add('<g stroke-width="1">')
for r, (_, states) in enumerate(ROWS):
    for c, s in enumerate(states):
        x, y = cxy(r, c)
        if s == ".":
            add(f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" '
                f'fill="{GREY_EMPTY}" stroke="#e0e0dc"/>')
        else:
            add(f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" '
                f'fill="#FFFFFF" stroke="#bbb"/>')
add('</g>')

# probe overlays, one animated group per column
PROBE_T0, PROBE_T1 = 0.5, 3.5
ATT_T0, ATT_T1 = 4.5, 7.5
for c in range(NCOL):
    t_on = PROBE_T0 + (PROBE_T1 - PROBE_T0) * (c + 0.5) / NCOL
    cells = []
    for r, (_, states) in enumerate(ROWS):
        s = states[c]
        if s in ".":
            continue
        x, y = cxy(r, c)
        fill = {"g": GREEN_FILL, "a": GREEN_FILL, "w": "url(#wav)", "x": WRONG}[s]
        stroke = "#8a8a8a" if s == "x" else GREEN
        cells.append(f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" '
                     f'fill="{fill}" stroke="{stroke}" stroke-width="0.8"/>')
    if cells:
        add(f'<g opacity="0">{"".join(cells)}{opacity_anim(t_on)}</g>')

# attack overlays (ASR flips), per column
for c in range(NCOL):
    t_on = ATT_T0 + (ATT_T1 - ATT_T0) * (c + 0.5) / NCOL
    cells = []
    for r, (_, states) in enumerate(ROWS):
        if states[c] != "a":
            continue
        x, y = cxy(r, c)
        cells.append(f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" '
                     f'fill="{CLAY}" fill-opacity="0.85" stroke="#8f3f22" stroke-width="1.4"/>')
    if cells:
        add(f'<g opacity="0">{"".join(cells)}{opacity_anim(t_on)}</g>')

# --- sweeps ----------------------------------------------------------------
for col, t0, t1 in ((GREEN, PROBE_T0, PROBE_T1), (CLAY, ATT_T0, ATT_T1)):
    add(f'<rect x="{X0 - 28}" y="{Y0 - 4}" width="24" height="{GRID_H + 8}" rx="3" '
        f'fill="{col}" fill-opacity="0.16" stroke="{col}" stroke-width="1.2" opacity="0">'
        f'<animate attributeName="x" dur="{T:g}s" repeatCount="indefinite" '
        f'values="{X0 - 28};{X0 - 28};{GRID_R + 6};{GRID_R + 6}" '
        f'keyTimes="0;{f(t0)};{f(t1)};1"/>'
        f'<animate attributeName="opacity" dur="{T:g}s" repeatCount="indefinite" '
        f'values="0;0;1;1;0;0" keyTimes="0;{f(t0 - 0.05)};{f(t0 + 0.05)};'
        f'{f(t1 - 0.05)};{f(t1 + 0.05)};1"/></rect>')

# --- legend (right of grid) ------------------------------------------------
LX, LY = GRID_R + 40, 116
legend = [
    (GREEN_FILL, GREEN, "passes", None),
    ("url(#wav)", GREEN, "mixed pass rate", None),
    (WRONG, "#8a8a8a", "always wrong", None),
    (CLAY, "#8f3f22", "attack lands", None),
    (GREY_EMPTY, "#e0e0dc", "no data yet", None),
]
add('<g font-size="11" fill="#333">')
for i, (fill, stroke, txt, _) in enumerate(legend):
    y = LY + i * 24
    add(f'<rect x="{LX}" y="{y}" width="14" height="14" fill="{fill}" '
        f'stroke="{stroke}" stroke-width="0.8"/>')
    add(f'<text x="{LX + 22}" y="{y + 12}">{txt}</text>')
add('</g>')

# --- audit gate + bins -----------------------------------------------------
GATE_X, GATE_Y, GATE_W, GATE_H = 300, 400, 64, 26
add(f'<rect x="{GATE_X}" y="{GATE_Y}" width="{GATE_W}" height="{GATE_H}" rx="6" '
    f'fill="#E2E9F0" stroke="{BLUE}" stroke-width="1.2"/>')
add(f'<text x="{GATE_X + GATE_W / 2:g}" y="{GATE_Y + 18}" font-size="13" '
    f'font-weight="600" fill="{BLUE}" text-anchor="middle">audit</text>')

BIN_Y, BIN_H, BIN_W = 452, 52, 148
bins = [
    (96,  "contrast pairs", "from mixed cells", GREEN, "#E8EFE2"),
    (268, "balance", "from attacked cells", CLAY, "#F4E4DC"),
    (440, "coverage fill", "from empty cells", "#777", "#ECECEC"),
]
for bx, name, sub, col, bg in bins:
    add(f'<rect x="{bx}" y="{BIN_Y}" width="{BIN_W}" height="{BIN_H}" rx="8" '
        f'fill="{bg}" stroke="{col}" stroke-width="1.4"/>')
    add(f'<text x="{bx + BIN_W / 2:g}" y="{BIN_Y + 21}" font-size="13" font-weight="700" '
        f'fill="{col}" text-anchor="middle">{name}</text>')
    add(f'<text x="{bx + BIN_W / 2:g}" y="{BIN_Y + 38}" font-size="10" fill="#555" '
        f'text-anchor="middle">{sub}</text>')

# --- route: blinking dashed arrows (cell -> gate -> bin) --------------------
GATE_CX, GATE_CY = GATE_X + GATE_W / 2, GATE_Y + GATE_H / 2
BIN_CENTERS = {"rl": (96 + BIN_W / 2, BIN_Y + 6), "bal": (268 + BIN_W / 2, BIN_Y + 6),
               "cov": (440 + BIN_W / 2, BIN_Y + 6)}


def route_path(sx, sy, bin_key):
    bx, by = BIN_CENTERS[bin_key]
    return (f"M{sx},{sy} C{sx},{sy + 70} {GATE_CX:g},{GATE_CY - 60:g} "
            f"{GATE_CX:g},{GATE_CY:g} C{GATE_CX:g},{GATE_CY + 14:g} "
            f"{bx:g},{by - 18:g} {bx:g},{by:g}")


routes = [
    # (source cell (r,c), color, bin, arrowhead marker id, t_start)
    ((0, 1), GREEN, "rl", "arrG", 8.6),
    ((4, 3), GREEN, "rl", "arrG", 9.0),
    ((0, 6), CLAY, "bal", "arrC", 8.9),
    ((3, 5), CLAY, "bal", "arrC", 9.3),
    ((2, 8), "#9a9a9a", "cov", "arrN", 9.1),
    ((5, 6), "#9a9a9a", "cov", "arrN", 9.5),
]
for (r, c), col, bin_key, mk, t0 in routes:
    x, y = cxy(r, c)
    sx, sy = x + CELL / 2, y + CELL / 2
    # blinking dashed arrow: fades in during the route phase, dash marches to
    # imply flow, opacity pulses (blink) while the route budget is being spent
    add(f'<path d="{route_path(sx, sy, bin_key)}" fill="none" stroke="{col}" '
        f'stroke-width="1.6" stroke-dasharray="5 4" marker-end="url(#{mk})" opacity="0">'
        f'<animate attributeName="stroke-dashoffset" values="18;0" '
        f'dur="0.9s" begin="{f2(t0)}s" repeatCount="indefinite"/>'
        f'<animate attributeName="opacity" dur="{T:g}s" repeatCount="indefinite" '
        f'values="0;0;1;0.35;1;0.35;1;0" '
        f'keyTimes="0;{f(t0)};{f(t0+0.3)};{f(t0+0.7)};{f(t0+1.1)};{f(t0+1.5)};{f(t0+1.9)};1"/>'
        f'</path>')

# --- GRPO box + arrows -----------------------------------------------------
GB_X, GB_Y, GB_W, GB_H = 706, 150, 226, 84
add(f'<rect x="{GB_X}" y="{GB_Y}" width="{GB_W}" height="{GB_H}" rx="10" '
    f'fill="#E8EFE2" stroke="{GREEN}" stroke-width="1.6"/>')
add(f'<rect x="{GB_X}" y="{GB_Y}" width="{GB_W}" height="{GB_H}" rx="10" '
    f'fill="{GREEN}" opacity="0">'
    f'<animate attributeName="opacity" dur="{T:g}s" repeatCount="indefinite" '
    f'values="0;0;0.16;0;0.16;0;0" '
    f'keyTimes="0;{f(13.0)};{f(13.4)};{f(13.8)};{f(14.2)};{f(14.6)};1"/></rect>')
add(f'<text x="{GB_X + GB_W / 2:g}" y="{GB_Y + 36}" font-size="16" font-weight="700" '
    f'fill="{GREEN}" text-anchor="middle">RL post-training</text>')
add(f'<text x="{GB_X + GB_W / 2:g}" y="{GB_Y + 56}" font-size="10.5" fill="#555" '
    f'text-anchor="middle">trains on the routed data</text>')

def arrowhead(tip_x, tip_y, from_x, from_y, t_on, t_fade=15.4, t_gone=15.8, size=11):
    """Manual arrowhead triangle, fading in only once the line has finished
    drawing (marker-end would pop in before the stroke, triangle-first)."""
    ang = math.degrees(math.atan2(tip_y - from_y, tip_x - from_x))
    return (f'<polygon points="0,0 {-size},{-size * 0.45:g} {-size},{size * 0.45:g}" '
            f'fill="{GREEN}" transform="translate({tip_x:g},{tip_y:g}) rotate({ang:.1f})" '
            f'opacity="0"><animate attributeName="opacity" dur="{T:g}s" '
            f'repeatCount="indefinite" values="0;0;1;1;0;0" '
            f'keyTimes="0;{f(t_on - 0.1)};{f(t_on)};{f(t_fade)};{f(t_gone)};1"/></polygon>')


# bins -> GRPO (draws during train; arrowhead appears at draw completion)
BG_TIP = (GB_X - 6, GB_Y + GB_H / 2)
BG_CTRL = (700, GB_Y + GB_H + 90)
add(f'<path d="M{440 + BIN_W + 6},{BIN_Y + BIN_H / 2:g} C680,{BIN_Y + BIN_H / 2 - 10:g} '
    f'{BG_CTRL[0]},{BG_CTRL[1]} {BG_TIP[0]},{BG_TIP[1]:g}" fill="none" '
    f'stroke="{GREEN}" stroke-width="2" pathLength="100" stroke-dasharray="100" '
    f'stroke-dashoffset="100" opacity="0">{draw_on(12.0, 13.0)}</path>')
add(arrowhead(*BG_TIP, *BG_CTRL, t_on=13.0))
add(f'<text x="682" y="380" font-size="12" fill="#555" opacity="0">merged bins'
    f'{window_anim(12.4, 15.4, ramp=0.2)}</text>')

# GRPO -> grid (loop back, draws late in train)
GG_TIP = (GRID_R + 14, Y0 + 8)
GG_CTRL = (480, 66)
add(f'<path d="M{GB_X + GB_W / 2:g},{GB_Y} C{GB_X + GB_W / 2:g},74 {GG_CTRL[0]},{GG_CTRL[1]} '
    f'{GG_TIP[0]},{GG_TIP[1]}" fill="none" stroke="{GREEN}" stroke-width="2" '
    f'stroke-dasharray="100" pathLength="100" stroke-dashoffset="100" '
    f'opacity="0">{draw_on(14.0, 15.2, t_fade=15.6, t_gone=15.9)}</path>')
add(arrowhead(*GG_TIP, *GG_CTRL, t_on=15.2, t_fade=15.6, t_gone=15.9))
add(f'<text x="600" y="66" font-size="10.5" font-weight="600" fill="{GREEN}" '
    f'text-anchor="middle" opacity="0">next checkpoint, re-probe'
    f'{window_anim(14.4, 15.9, ramp=0.2)}</text>')

add('</svg>')

out = os.path.join(os.path.dirname(__file__), "..", "notes", "figures", "grid-probe-anim-v1.svg")
with open(os.path.abspath(out), "w") as fh:
    fh.write("\n".join(parts) + "\n")
print("wrote", os.path.abspath(out))
