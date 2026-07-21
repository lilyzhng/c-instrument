"""T20 data-gen latency profile (design §5.5). Measured on OpenRouter direct,
2026-07-19. Renders a speedup waterfall as inline SVG (house style).
Numbers are measured, not modeled: single-call timings + parallel benchmark +
observed run rate; the fix rates are the profile-derived projections."""
stages = [
    ("CHUNK=8 (as shipped)", 4.7, "#C4633F", "gen-phase barrier: 8 of 48 workers used"),
    ("CHUNK=64", 30, "#8a8a3a", "batch saturates the ~300 calls/min ceiling"),
    ("fast-probe (no judges)", 180, "#245F2B", "7.5 of 8.5 calls/cell are judging; skip them"),
]
W, H = 760, 340
BAR_X = 220
BAR_MAX_W = 460
maxv = max(rate for _, rate, _, _ in stages)
bars = ""
for i, (name, rate, color, note) in enumerate(stages):
    y = 70 + i * 80
    w = 40 + (rate / maxv) * BAR_MAX_W
    inside = w >= 130
    bars += f'<rect x="{BAR_X}" y="{y}" width="{w:.0f}" height="42" rx="6" fill="{color}"/>'
    bars += f'<text x="{BAR_X - 8}" y="{y + 26}" font-size="13" fill="#1c1c1c" text-anchor="end" font-weight="600">{name}</text>'
    if inside:
        tx = BAR_X + w - 14
        bars += f'<text x="{tx:.0f}" y="{y + 20}" font-size="15" fill="#fff" font-weight="700" text-anchor="end">{rate:.0f} cells/min</text>'
        bars += f'<text x="{tx:.0f}" y="{y + 37}" font-size="10.5" fill="rgba(255,255,255,0.88)" text-anchor="end">{note}</text>'
    else:
        tx = BAR_X + w + 10
        bars += f'<text x="{tx:.0f}" y="{y + 20}" font-size="15" fill="#1c1c1c" font-weight="700">{rate:.0f} cells/min</text>'
        bars += f'<text x="{tx:.0f}" y="{y + 37}" font-size="10.5" fill="#666">{note}</text>'
svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" font-family="Inter, system-ui, sans-serif">
<rect width="{W}" height="{H}" fill="#F4F4F4"/>
<text x="24" y="34" font-size="17" font-weight="700" fill="#1c1c1c">Data-generation speedup: the bottleneck was self-throttling, not the API</text>
<text x="24" y="54" font-size="12" fill="#555">measured: single calls are fast (gen 3.8s, judge 3.2s); OpenRouter sustains ~300 calls/min at 48 workers. The loop wasted it.</text>
{bars}
<text x="24" y="322" font-size="11" fill="#666">~38x from two recipes: (1) size the batch to the API's real concurrency ceiling, (2) drop judging on by-construction-labeled probe rows.</text>
</svg>'''
open("notes/figures/datagen-speedup-v1.svg", "w").write(svg)
print("wrote notes/figures/datagen-speedup-v1.svg")
