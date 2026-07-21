#!/usr/bin/env python3
"""Generate notes/figures/two-channel-cell-v1.svg (Figure 8), animated.

One grid cell tested from both directions in a 16s SMIL cycle:
  probe (0-5.3s): safe look-alikes fly in from the left, cell must pass them
  attack (5.3-10.7s): disguised-unsafe rows fly in from the right, the shield
                      must block them; one slips through = ASR
  verdict (10.7-16s): the four cell verdicts + where each routes
Same visual language as the other animated figures (palette, big phase word,
minimal text).
"""

import os

T = 16.0

GREEN = "#245F2B"
GREEN_FILL = "#A9C08F"
CLAY = "#C4633F"
CLAY_DARK = "#8f3f22"
BLUE = "#4A6B8A"
DARK = "#1c1c1c"

P1, P2 = 5.3, 10.7  # phase boundaries


def f(t):
    return f"{t / T:.4f}"


def window(t_on, t_off, ramp=0.15):
    return (f'<animate attributeName="opacity" dur="{T:g}s" repeatCount="indefinite" '
            f'values="0;0;1;1;0;0" '
            f'keyTimes="0;{f(t_on)};{f(t_on + ramp)};{f(t_off - ramp)};{f(t_off)};1"/>')


def hold(t_on, t_off=15.4, t_gone=15.8):
    return (f'<animate attributeName="opacity" dur="{T:g}s" repeatCount="indefinite" '
            f'values="0;0;1;1;0;0" '
            f'keyTimes="0;{f(t_on - 0.05)};{f(t_on + 0.15)};{f(t_off)};{f(t_gone)};1"/>')


parts = []
add = parts.append

add('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 540" '
    'font-family="Inter, system-ui, sans-serif">')
add('<defs>')
add('<pattern id="mx" width="6" height="6" patternUnits="userSpaceOnUse" '
    'patternTransform="rotate(45)"><rect width="6" height="6" fill="#FFFFFF"/>'
    f'<rect width="3" height="6" fill="{GREEN_FILL}"/></pattern>')
add('</defs>')
add('<rect width="960" height="540" fill="#F4F4F4"/>')
add(f'<text x="24" y="42" font-size="24" font-weight="700" fill="{DARK}">'
    'One cell, tested from both sides</text>')

# --- phase word ------------------------------------------------------------
phases = [("probe", GREEN, 0.0, P1), ("attack", CLAY, P1, P2),
          ("verdict", BLUE, P2, T)]
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

# --- the cell (center) -----------------------------------------------------
CX, CY, CS = 410, 140, 140  # top-left + size
add(f'<rect x="{CX}" y="{CY}" width="{CS}" height="{CS}" rx="12" fill="#FFFFFF" '
    f'stroke="{DARK}" stroke-width="2"/>')
add(f'<text x="{CX + CS / 2:g}" y="{CY + CS + 26}" font-size="14" font-weight="600" '
    f'fill="#555" text-anchor="middle">one grid cell</text>')
# green wash while probed, clay wash while attacked
add(f'<rect x="{CX}" y="{CY}" width="{CS}" height="{CS}" rx="12" fill="{GREEN}" '
    f'opacity="0">{window(0.4, P1)}</rect>'.replace('values="0;0;1;1;0;0"',
                                                    'values="0;0;0.12;0.12;0;0"'))
add(f'<rect x="{CX}" y="{CY}" width="{CS}" height="{CS}" rx="12" fill="{CLAY}" '
    f'opacity="0">{window(P1 + 0.4, P2)}</rect>'.replace('values="0;0;1;1;0;0"',
                                                         'values="0;0;0.12;0.12;0;0"'))

# --- channel 1: safe look-alikes from the left -----------------------------
add(f'<text x="150" y="128" font-size="16" font-weight="700" fill="{GREEN}" '
    f'text-anchor="middle">safe look-alikes</text>')
add(f'<text x="150" y="148" font-size="12" fill="#555" text-anchor="middle">'
    f'should pass</text>')
for i in range(3):
    t0 = 0.6 + i * 1.1
    y = 185 + i * 26
    # a green pill flies into the cell and lands as a check
    add(f'<g opacity="0"><rect x="-16" y="-8" width="32" height="16" rx="8" '
        f'fill="{GREEN_FILL}" stroke="{GREEN}" stroke-width="1.2"/>'
        f'<animateMotion dur="{T:g}s" repeatCount="indefinite" '
        f'path="M100,{y} L{CX - 20},{y}" keyPoints="0;0;1;1" '
        f'keyTimes="0;{f(t0)};{f(t0 + 0.8)};1" calcMode="linear"/>'
        f'{window(t0 - 0.05, t0 + 0.95, ramp=0.1)}</g>')
    # check appears inside the cell where the pill landed
    add(f'<path d="M{CX + 24 + i * 34},{CY + 36} l5,6 l9,-12" fill="none" '
        f'stroke="{GREEN}" stroke-width="3" stroke-linecap="round" opacity="0">'
        f'{hold(t0 + 0.9)}</path>')

# --- channel 2: disguised unsafe from the right ----------------------------
add(f'<text x="810" y="128" font-size="16" font-weight="700" fill="{CLAY}" '
    f'text-anchor="middle">disguised unsafe</text>')
add(f'<text x="810" y="148" font-size="12" fill="#555" text-anchor="middle">'
    f'should be blocked</text>')
# shield on the cell's right edge
SHX, SHY = CX + CS + 16, CY + CS / 2
add(f'<path d="M{SHX},{SHY - 26} L{SHX + 20},{SHY - 18} L{SHX + 20},{SHY + 2} '
    f'C{SHX + 20},{SHY + 16} {SHX + 10},{SHY + 24} {SHX},{SHY + 28} '
    f'C{SHX - 10},{SHY + 24} {SHX - 20},{SHY + 16} {SHX - 20},{SHY + 2} '
    f'L{SHX - 20},{SHY - 18} Z" fill="#FFFFFF" stroke="{CLAY}" stroke-width="2" '
    f'opacity="0">{hold(P1)}</path>')
for i, blocked in enumerate((True, True, False)):
    t0 = P1 + 0.6 + i * 1.3
    y = SHY - 26 + i * 26
    if blocked:
        # clay pill flies in and bounces off the shield
        add(f'<g opacity="0"><rect x="-16" y="-8" width="32" height="16" rx="8" '
            f'fill="{CLAY}" fill-opacity="0.85" stroke="{CLAY_DARK}" stroke-width="1.2"/>'
            f'<animateMotion dur="{T:g}s" repeatCount="indefinite" '
            f'path="M870,{y} L{SHX + 34},{y} L{SHX + 58},{y - 14}" '
            f'keyPoints="0;0;0.8;1" keyTimes="0;{f(t0)};{f(t0 + 0.7)};{f(t0 + 1.0)}" '
            f'calcMode="linear"/>{window(t0 - 0.05, t0 + 1.0, ramp=0.1)}</g>')
        # blocked flash on the shield
        add(f'<line x1="{SHX - 9}" y1="{y - 8}" x2="{SHX + 9}" y2="{y + 8}" '
            f'stroke="{CLAY_DARK}" stroke-width="3" stroke-linecap="round" opacity="0">'
            f'{window(t0 + 0.6, t0 + 1.2, ramp=0.1)}</line>')
    else:
        # one slips past the shield into the cell = ASR
        add(f'<g opacity="0"><rect x="-16" y="-8" width="32" height="16" rx="8" '
            f'fill="{CLAY}" fill-opacity="0.85" stroke="{CLAY_DARK}" stroke-width="1.2"/>'
            f'<animateMotion dur="{T:g}s" repeatCount="indefinite" '
            f'path="M870,{y} L{CX + CS - 46},{y}" keyPoints="0;0;1;1" '
            f'keyTimes="0;{f(t0)};{f(t0 + 0.9)};1" calcMode="linear"/>'
            f'{window(t0 - 0.05, min(t0 + 3.0, 15.6), ramp=0.1)}</g>')
        add(f'<text x="{CX + CS - 46}" y="{y - 16}" font-size="13" font-weight="800" '
            f'fill="{CLAY_DARK}" text-anchor="middle" opacity="0">ASR!'
            f'{window(t0 + 0.9, min(t0 + 3.2, 15.6), ramp=0.15)}</text>')

# --- verdict chips ---------------------------------------------------------
CHIP_W, CHIP_H, CHIP_Y = 200, 74, 420
chips = [
    (46,  "healthy", "-> dev set", GREEN, "#EAF2EB", GREEN_FILL, True),
    (268, "mixed", "-> contrast pairs", GREEN, "#FFFFFF", "url(#mx)", True),
    (490, "ASR dirty", "-> balance pack", CLAY, "#F6E9E3", CLAY, False),
    (712, "conf. wrong", "-> audit labels", "#666", "#FFFFFF", "#6b6b6b", True),
]
for i, (x, name, route, col, bg, swatch, shield_ok) in enumerate(chips):
    t0 = P2 + 0.4 + i * 0.9
    g = (f'<rect x="{x}" y="{CHIP_Y}" width="{CHIP_W}" height="{CHIP_H}" rx="9" '
         f'fill="{bg}" stroke="{col}" stroke-width="1.6"/>')
    g += (f'<rect x="{x + 14}" y="{CHIP_Y + 16}" width="20" height="20" '
          f'fill="{swatch}" stroke="{col}" stroke-width="1"/>')
    g += (f'<text x="{x + 46}" y="{CHIP_Y + 32}" font-size="15" font-weight="700" '
          f'fill="{col}">{name}</text>')
    g += (f'<text x="{x + 14}" y="{CHIP_Y + 58}" font-size="12.5" fill="#555">'
          f'{route}</text>')
    add(f'<g opacity="0">{g}{hold(t0)}</g>')
add(f'<text x="46" y="{CHIP_Y - 16}" font-size="14" font-weight="600" fill="#555" '
    f'opacity="0">healthy only if BOTH sides pass{hold(P2 + 0.2)}</text>')

add('</svg>')

out = os.path.join(os.path.dirname(__file__), "..", "notes", "figures",
                   "two-channel-cell-v1.svg")
with open(os.path.abspath(out), "w") as fh:
    fh.write("\n".join(parts) + "\n")
print("wrote", os.path.abspath(out))
