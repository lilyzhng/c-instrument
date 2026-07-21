#!/usr/bin/env python3
"""Generic animated-SVG -> static PNG export for paper figures.

Every opacity-animated element is set to its peak opacity over the cycle
(show everything), stroke-dash draw-ins are completed, and all <animate*>
tags are stripped. Figure-specific cleanups (overlapping cycled labels)
belong in a dedicated builder like build_fig1_static.py, not here.

Usage: python3 src/tools/svg_static_export.py <in.svg> <out.png>
"""

import re
import subprocess
import sys

ANIM = re.compile(r'<animate[^>]*attributeName="opacity"[^>]*values="([^"]*)"[^>]*/?>')


def freeze_line(line):
    m = ANIM.search(line)
    if m:
        peak = max(float(v) for v in m.group(1).split(";"))
        line = re.sub(r'(?<![\w-])opacity="[0-9.]*"', f'opacity="{peak:g}"',
                      line, count=1)
    line = re.sub(r"<animate[^>]*/>", "", line)
    line = re.sub(r"<animate[^>]*>.*?</animate[^>]*>", "", line)
    # draw-in paths (pathLength=100 + dasharray) render with bogus gaps in
    # rsvg (it ignores pathLength when scaling dashes); strip the dash trick
    if 'pathLength="100"' in line:
        line = re.sub(r' stroke-dasharray="[^"]*"', "", line)
        line = re.sub(r' stroke-dashoffset="[^"]*"', "", line)
        line = line.replace(' pathLength="100"', "")
    return line


POS = re.compile(r'<text x="([0-9.]+)" y="([0-9.]+)"')


def cycled_label_positions(lines):
    """Positions where 2+ animated <text> elements stack = cycling stage
    labels; a static frame drops the whole group (they only make sense in
    motion)."""
    seen = {}
    for l in lines:
        m = POS.search(l)
        if m and "<animate" in l:
            seen[m.group(0)] = seen.get(m.group(0), 0) + 1
    return {k for k, n in seen.items() if n >= 2}


def main():
    src, out = sys.argv[1], sys.argv[2]
    lines = list(open(src))
    drop = cycled_label_positions(lines)
    frozen = "".join(
        freeze_line(l) for l in lines
        # animateMotion tokens ride the loop in the animation; frozen they
        # pile up at the origin, so drop them entirely
        if "animateMotion" not in l and not any(p in l for p in drop))
    tmp = out.replace(".png", ".svg")
    open(tmp, "w").write(frozen)
    subprocess.run(["rsvg-convert", "--zoom", "2", "-o", out, tmp], check=True)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
