#!/usr/bin/env python3
"""Regenerate the auto-generated leaderboard block in deliverables/results/s5.5_results.md
from pathfinder/pathfinder-data.js (the canonical trace store).

Usage:  python3 src/tools/build_results_leaderboard_md.py
Run after any pathfinder-data.js update; the block between the AUTOGEN markers
is replaced wholesale, everything else in the MD is left untouched.
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_JS = ROOT / "pathfinder" / "pathfinder-data.js"
TARGET_MD = ROOT / "deliverables" / "results" / "s5.5_results.md"
START = "<!-- AUTOGEN:LEADERBOARD START (src/tools/build_results_leaderboard_md.py) -->"
END = "<!-- AUTOGEN:LEADERBOARD END -->"


def load_data():
    raw = DATA_JS.read_text()
    return json.loads(raw.split("=", 1)[1].strip().rstrip(";"))


def fmt(v, pct=False):
    if v is None:
        return "—"
    return f"{v:.3f}".rstrip("0").rstrip(".") if not pct else f"{v:.1%}"


def render(d):
    base = d["baseline"]
    ship = next(e for e in d["experiments"] if e.get("ship"))
    lines = [
        START,
        "",
        "## Leaderboard (auto-generated from PathFinder)",
        "",
        f"> Source: [`pathfinder/pathfinder-data.js`](../../pathfinder/pathfinder-data.js) · "
        f"veto rule: {d['metrics_def']['veto']} · baseline safe {fmt(base['safe_acc'])} / "
        f"unsafe {fmt(base['unsafe_acc'])} / ASR {fmt(base['asr'])}",
        "",
        f"**🏆 Ship: exp{ship['exp']}** — `{ship['name']}` s{ship['step']}: "
        f"safe {fmt(ship['safe_acc'])}, unsafe {fmt(ship['unsafe_acc'])}, "
        f"balanced {fmt(ship['balanced'])}, ASR {fmt(ship['asr'])}, veto {ship['veto']}.",
        "",
        "| Exp | Group | Run | Step | safe_acc | unsafe_acc | balanced | veto | ASR | Note |",
        "| :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- | :-- |",
    ]
    for e in d["experiments"]:
        tag = " 🏆" if e.get("ship") else ""
        step = f"s{e['step']}" if e["step"] is not None else "—"
        lines.append(
            f"| {e['exp']}{tag} | {e['group']} | {e['name']} | {step} "
            f"| {fmt(e['safe_acc'])} | {fmt(e['unsafe_acc'])} | {fmt(e['balanced'])} "
            f"| {e['veto']} | {fmt(e['asr'])} | {e['note']} |"
        )
    lines += ["", "**Groups:**", ""]
    for g, info in d["groups"].items():
        lines.append(f"- **{g} · {info['label']}** — {info['desc']}")
    lines += ["", END]
    return "\n".join(lines)


def main():
    d = load_data()
    block = render(d)
    md = TARGET_MD.read_text()
    if START in md:
        md = re.sub(re.escape(START) + r".*?" + re.escape(END), block, md, flags=re.S)
    else:
        raise SystemExit(f"AUTOGEN markers not found in {TARGET_MD}; add them once, then rerun.")
    TARGET_MD.write_text(md)
    print(f"Updated {TARGET_MD.relative_to(ROOT)} with {len(d['experiments'])} experiments.")


if __name__ == "__main__":
    main()
