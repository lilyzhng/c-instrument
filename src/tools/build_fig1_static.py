#!/usr/bin/env python3
"""Build the static Figure 1 (CPR loop) from the animated grid-probe SVG.

Show-everything strategy: every opacity-animated element is set to its PEAK
opacity over the cycle, so the full loop (probe states, attack hits, routing
arrows, packs, merge + re-probe arcs) appears in one frame. Two hand-edits on
top: (1) the four stacked cycling stage words at the top right are replaced by
one static "probe -> attack -> route -> train" strip; (2) the dark train-stage
highlight rect over the RL box is dropped so the box text stays readable.

Usage: python3 src/tools/build_fig1_static.py
Output: latex/figure/fig1-cpr-loop.png (+ .svg beside it)
"""

import re
import subprocess

SRC = "notes/figures/grid-probe-anim-v1.svg"
OUT_SVG = "latex/figure/fig1-cpr-loop.svg"
OUT_PNG = "latex/figure/fig1-cpr-loop.png"

ANIM = re.compile(r'<animate[^>]*attributeName="opacity"[^>]*values="([^"]*)"[^>]*/?>')

# horizontal topic-row highlight (privacy row): crosses the vertical roleplay
# cursor so row x column = one cell reads directly off the figure
ROW_BAND = (
    '<rect x="122" y="100" width="343" height="37" rx="3" fill="#245F2B" '
    'fill-opacity="0.10" stroke="#245F2B" stroke-width="1.2"/>'
)

STAGE_STRIP = (
    '<text x="936" y="46" font-size="19" font-weight="800" text-anchor="end">'
    '<tspan fill="#245F2B">probe</tspan><tspan fill="#999"> → </tspan>'
    '<tspan fill="#C4633F">attack</tspan><tspan fill="#999"> → </tspan>'
    '<tspan fill="#4A6B8A">route</tspan><tspan fill="#999"> → </tspan>'
    '<tspan fill="#245F2B">train</tspan></text>'
)


def keep(line):
    # drop the four cycling stage words (replaced by STAGE_STRIP)
    if 'x="936" y="46"' in line and "<animate" in line:
        return False
    # drop the dark train-stage highlight over the RL box
    if 'fill="#245F2B" opacity="0"' in line and "<rect" in line:
        return False
    # drop the green probe-stage sweep band (would overlap the red one)
    if 'height="275"' in line and 'fill="#245F2B"' in line:
        return False
    return True


def retitle(line):
    line = line.replace(">Constitution probing<",
                        ">Constitution probing &amp; routing (CPR)<")
    # drop the re-probe label well below the arc, into the empty pocket
    # between the legend (ends ~x=615) and the RL box (starts x=706, y=150)
    if "next checkpoint, re-probe" in line:
        line = line.replace('x="600"', 'x="660"').replace('y="66"', 'y="105"')
    # nudge the merged-bins label clear of the curve it sits on
    if "merged bins" in line:
        line = line.replace('x="682"', 'x="696"')
    # merged-bins arrow: enter the RL box through its bottom edge (y=234),
    # not beside its left corner
    line = line.replace('d="M594,478 C680,468 700,324 700,192"',
                        'd="M594,478 C700,470 780,380 780,240"')
    line = line.replace('transform="translate(700,192) rotate(-90.0)"',
                        'transform="translate(780,240) rotate(-90.0)"')
    return line


def freeze_line(line):
    m = ANIM.search(line)
    if m:
        peak = max(float(v) for v in m.group(1).split(";"))
        # (?<![\w-]) so fill-opacity/stroke-opacity are never touched
        line = re.sub(r'(?<![\w-])opacity="[0-9.]*"', f'opacity="{peak:g}"',
                      line, count=1)
    # red attack sweep cursor: scans one column at a time. Park on roleplay
    # (cells at x=330, width 29; cursor width 37 wraps it) — fiction to its
    # left is already scanned, its red cells are the results.
    if 'height="275"' in line and 'fill="#C4633F"' in line:
        line = re.sub(r'(?<![\w-])x="[0-9.]*"', 'x="326"', line, count=1)
        line = line.replace('width="24"', 'width="37"')
    line = re.sub(r"<animate[^>]*/>", "", line)
    line = re.sub(r"<animate[^>]*>.*?</animate[^>]*>", "", line)
    # draw-in paths (pathLength=100 + dasharray) render with bogus gaps in
    # rsvg (it ignores pathLength when scaling dashes); strip the dash trick
    if 'pathLength="100"' in line:
        line = re.sub(r' stroke-dasharray="[^"]*"', "", line)
        line = re.sub(r' stroke-dashoffset="[^"]*"', "", line)
        line = line.replace(' pathLength="100"', "")
    return line


def main():
    out = []
    for line in open(SRC):
        if not keep(line):
            continue
        line = freeze_line(retitle(line))
        if line.startswith("</svg>"):
            out.append(ROW_BAND + "\n")
            out.append(STAGE_STRIP + "\n")
        out.append(line)
    open(OUT_SVG, "w").write("".join(out))
    subprocess.run(["rsvg-convert", "--zoom", "2", "-o", OUT_PNG, OUT_SVG], check=True)
    print(f"wrote {OUT_PNG}")


if __name__ == "__main__":
    main()
