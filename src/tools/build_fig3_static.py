#!/usr/bin/env python3
"""Build the static Figure 3 (two channels per cell) for the paper.

The animation fires prompt "bullets" at one grid cell from both sides; a
frozen frame catches none of them mid-flight, so the static version draws
the story explicitly: two safe look-alikes fly in from the left and pass,
one disguised-unsafe from the right is blocked by the shield, and one slips
past it into the cell (the ASR event). The four cell states stay at the
bottom. Base elements come from the generic freezer in svg_static_export.

Usage: python3 src/tools/build_fig3_static.py
Output: latex/figure/fig3-two-channel.png (+ .svg)
"""

import subprocess

from svg_static_export import cycled_label_positions, freeze_line

SRC = "deliverables/figures/two-channel-cell-v1.svg"
OUT_SVG = "latex/figure/fig3-two-channel.svg"
OUT_PNG = "latex/figure/fig3-two-channel.png"

G, R, RD = "#245F2B", "#C4633F", "#8f3f22"


def pill(cx, cy, color, edge):
    return (f'<rect x="{cx-16}" y="{cy-8}" width="32" height="16" rx="8" '
            f'fill="{color}" fill-opacity="0.85" stroke="{edge}" stroke-width="1.2"/>')


def arrow(x1, y, x2, color, dashed=False):
    dash = ' stroke-dasharray="6 5"' if dashed else ""
    head = (f'<polygon points="{x2},{y} {x2+9},{y-4} {x2+9},{y+4}" fill="{color}"/>'
            if x2 < x1 else
            f'<polygon points="{x2},{y} {x2-9},{y-4} {x2-9},{y+4}" fill="{color}"/>')
    return (f'<line x1="{x1}" y1="{y}" x2="{x2 + (9 if x2 < x1 else -9)}" y2="{y}" '
            f'stroke="{color}" stroke-width="2.4"{dash}/>' + head)


EXTRA = "".join([
    # benign channel: two safe look-alikes fly in from the left and enter
    pill(216, 180, "#A9C08F", G), arrow(232, 180, 404, G),
    pill(216, 240, "#A9C08F", G), arrow(232, 240, 404, G),
    # attack channel: one disguised-unsafe is stopped at the shield...
    pill(744, 190, R, RD), arrow(728, 190, 596, R),
    f'<text x="620" y="176" font-size="12" font-weight="600" fill="{R}">blocked</text>',
    # ...and one slips under it into the cell: the ASR event
    pill(744, 252, R, RD), arrow(728, 252, 556, R, dashed=True),
    f'<text x="606" y="270" font-size="12" font-weight="600" fill="{R}">slips through → ASR</text>',
])


def main():
    lines = list(open(SRC))
    drop = cycled_label_positions(lines)
    out = []
    for line in lines:
        if "animateMotion" in line or any(p in line for p in drop):
            continue
        line = freeze_line(line)
        if line.startswith("</svg>"):
            out.append(EXTRA + "\n")
        out.append(line)
    open(OUT_SVG, "w").write("".join(out))
    subprocess.run(["rsvg-convert", "--zoom", "2", "-o", OUT_PNG, OUT_SVG], check=True)
    print(f"wrote {OUT_PNG}")


if __name__ == "__main__":
    main()
