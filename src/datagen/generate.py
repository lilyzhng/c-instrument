"""Grid-driven generation + inline labeling (T8).

For each grid cell (src/datagen/grid.py) the generator (GLM-5.2) writes a
few intent-flip pairs grounded in that topic's constitution and shaped by the
cell's stylistic axes; each side is then labeled inline by the judge ensemble
(DeepSeek + GPT-5.6-Sol + Grok) so contradictions surface as the corpus is
built, not in a separate pass. Labels are by construction; the ensemble only
flags rows it disagrees with. Rows stream to JSONL with a pollable progress
file, same speedup pattern as the bake-offs.

The first ~100 rows are the pilot gate: diversity, judge-agreement, length.
The offensive-by-construction topic (hate_discrimination) is excluded until
sign-off, so the pilot generates nothing offensive.

Pure logic (extract_section, build_cell_prompt, parse_pairs, assemble_rows,
pilot_metrics) is unit-tested in src/tests/test_generate.py; only run() and
label_rows touch the network.
"""

import argparse
import json
import os
import re
import sys
import time

sys.path.insert(0, os.getcwd())
from src.datagen.grid import build_grid, load_constitutions, TOPICS_DIR  # noqa: E402
from src.datagen.judge_bakeoff import SYS as JUDGE_SYS, parse_verdict  # noqa: E402
from src.datagen.label_gate import majority_vote  # noqa: E402
from src.datagen.generator_bakeoff import wc  # noqa: E402

GENERATOR = "z-ai/glm-5.2"
JUDGES = ["deepseek/deepseek-v4-pro", "openai/gpt-5.6-sol", "x-ai/grok-4.5"]
# offensive-by-construction unsafe side; excluded until explicit sign-off
HOLD_TOPICS = {"hate_discrimination"}
PROGRESS_PATH = "results/generate_progress.txt"
CHUNK = 24  # bigger batch saturates workers across the gen+label barrier (profiled: CHUNK=8 left ~40/48 workers idle in the gen phase)

GEN_SYS = (
    "You are a red-team data generator building a training set for a SAFETY "
    "CLASSIFIER. You write realistic short user PROMPTS (median ~13 words, "
    "like real chat), never answers. Keep any unsafe side mild and "
    "claim-shape, no operational detail, no slurs. Vary named entities and "
    "specifics; do not reuse famous or canonical examples (e.g. the White "
    "House), which would overlap with public benchmarks. Output ONLY a JSON "
    "array of objects, each {\"safe\": \"...\", \"unsafe\": \"...\"} (or "
    "{\"safe\": \"...\"} for a coverage-only task), no prose."
)

# per-topic sharpening folded in after the pilot (recipe tuning, not a filter)
TOPIC_HINTS = {
    "hate_discrimination": (
        " The unsafe side must seek clearly discriminatory treatment of a "
        "protected group in a concrete setting (hiring, housing, services, "
        "pay), not a debatable public-policy question. The safe side stays "
        "absurd (nonsensical or non-protected targets)."
    ),
}

_SHAPE = {
    "direct_request": "a direct request",
    "roleplay_frame": "framed as a roleplay or persona",
    "hypothetical": "framed as a hypothetical or 'what if'",
}
_DEPTH = {
    "overview": "asking for a high-level overview",
    "step_by_step": "asking for step-by-step detail",
    "technical_detail": "asking for technical specifics",
}
_FORM = {
    "prose": "phrased as a natural sentence",
    "list": "asking for a list",
    "qa": "phrased as a direct question",
}


# ---- pure logic (unit-tested, no network) ----

def extract_section(body, heading):
    """Text under '## <heading>' up to the next '## ' (or end), stripped.
    Empty string if the heading is absent."""
    m = re.search(rf"^##\s+{re.escape(heading)}\s*$(.*?)(?=^##\s|\Z)",
                  body, re.MULTILINE | re.DOTALL)
    return m.group(1).strip() if m else ""


def build_cell_prompt(body, cell, n_pairs):
    """User prompt for one grid cell: the topic's boundary + benign-confusion
    guidance, the mechanism, and the three stylistic axes, asking for n pairs
    (or n safe-only prompts when the cell is unpaired/baseline)."""
    boundary = extract_section(body, "Boundary")
    style = (f"{_SHAPE.get(cell['interaction_shape'], cell['interaction_shape'])}, "
             f"{_DEPTH.get(cell['information_depth'], cell['information_depth'])}, "
             f"{_FORM.get(cell['content_form'], cell['content_form'])}")
    head = f"Topic: {cell['topic']}. Boundary:\n{boundary}\n\n"
    hint = TOPIC_HINTS.get(cell["topic"], "")
    if cell["paired"]:
        return (head + f"Mechanism: {cell['mechanism']} (hold a content word "
                f"fixed, flip only the intent). Produce {n_pairs} intent-flip "
                f"pairs where each prompt is {style}. The safe and unsafe side "
                f"of a pair must share the trigger word.{hint} JSON array of "
                f"{{\"safe\", \"unsafe\"}} only.")
    return (head + f"Produce {n_pairs} clearly-safe prompts (no unsafe twin), "
            f"each {style}.{hint} JSON array of {{\"safe\"}} only.")


def parse_pairs(text):
    """Extract the JSON array from a generation and return a list of
    {safe, unsafe?} dicts. Empty list on refusal / unparseable output."""
    if not text:
        return []
    m = re.search(r"\[.*\]", text, re.DOTALL)
    if not m:
        return []
    try:
        arr = json.loads(m.group(0))
    except json.JSONDecodeError:
        return []
    out = []
    for d in arr:
        if isinstance(d, dict) and d.get("safe"):
            out.append(d)
    return out


def assemble_rows(cell, pairs):
    """Flatten a cell's generated pairs into labeled-by-construction rows: a
    safe row per pair, plus an unsafe row when the cell is paired and the
    unsafe side is present. Degenerate (safe==unsafe) pairs are dropped."""
    rows = []
    base = {k: cell[k] for k in ("topic", "tier", "mechanism",
                                 "interaction_shape", "information_depth",
                                 "content_form")}
    for i, d in enumerate(pairs):
        safe = (d.get("safe") or "").strip()
        unsafe = (d.get("unsafe") or "").strip()
        if not safe:
            continue
        if cell["paired"] and unsafe and unsafe == safe:
            continue  # degenerate, not a real contrast
        rows.append({**base, "constructed_label": "safe", "prompt": safe})
        if cell["paired"] and unsafe:
            rows.append({**base, "constructed_label": "unsafe", "prompt": unsafe})
    return rows


def pilot_metrics(rows):
    """Gate numbers over labeled rows: label-agreement (majority matches the
    constructed label), diversity (distinct prompts), length-band, undecided.
    Split by constructed label so the safe side (the mission axis) is visible."""
    n = len(rows)
    if n == 0:
        return {"n": 0}
    labeled = [r for r in rows if "majority" in r]

    def agree(group):
        g = [r for r in group if "majority" in r]
        return (round(sum(r["majority"] == r["constructed_label"] for r in g)
                      / len(g), 3) if g else None)

    prompts = [r["prompt"] for r in rows]
    lens = [wc(p) for p in prompts]
    return {
        "n": n,
        "label_agreement": agree(rows),
        "safe_agreement": agree([r for r in rows if r["constructed_label"] == "safe"]),
        "unsafe_agreement": agree([r for r in rows if r["constructed_label"] == "unsafe"]),
        "diversity": round(len(set(prompts)) / n, 3),
        "length_ok": round(sum(3 <= x <= 17 for x in lens) / n, 3),
        "undecided": sum(r.get("majority") is None for r in labeled),
        "labeled": len(labeled),
    }


# ---- orchestration (network) ----

def _pool_map(fn, items, workers):
    if workers == 1:
        return [fn(x) for x in items]
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(fn, items))


def run(n_pairs, max_cells, out_path, workers=6, topics=None, include_hold=False,
        cell_ids=None):
    from src.datagen._aq import chat

    def log(msg):
        with open(PROGRESS_PATH, "a") as f:
            f.write(msg + "\n")
        print(msg, flush=True)

    cons = load_constitutions(TOPICS_DIR)
    body_by_topic = {}
    for path in sorted(TOPICS_DIR.glob("*.md")):
        body_by_topic[path.stem] = path.read_text()

    grid = build_grid(cons)
    cells = grid["cells"]
    if topics:
        cells = [c for c in cells if c["topic"] in set(topics)]
    if cell_ids:  # T48 expand packs target exact frontier cells (s5.7 R1)
        wanted = set(cell_ids)
        cells = [c for c in cells
                 if "|".join(str(c.get(k, "-")) for k in
                             ("topic", "mechanism", "interaction_shape",
                              "information_depth", "content_form")) in wanted]
    if not include_hold:
        cells = [c for c in cells if c["topic"] not in HOLD_TOPICS]
    # cap cells per topic so a pilot samples across topics, not all of one
    if max_cells:
        seen, capped = {}, []
        for c in cells:
            seen[c["topic"]] = seen.get(c["topic"], 0) + 1
            if seen[c["topic"]] <= max_cells:
                capped.append(c)
        cells = capped

    os.makedirs("results", exist_ok=True)
    open(PROGRESS_PATH, "w").close()
    held = sorted(HOLD_TOPICS) if not include_hold else []
    log(f"cells: {len(cells)}  generator: {GENERATOR}  judges: {len(JUDGES)}  "
        f"n_pairs/cell: {n_pairs}  held-back topics: {held}")

    def gen_cell(cell):
        body = body_by_topic.get(cell["topic"], "")
        txt, _ok, _ra = chat(GENERATOR, GEN_SYS,
                             build_cell_prompt(body, cell, n_pairs),
                             max_tokens=2000, temperature=0.9)
        return assemble_rows(cell, parse_pairs(txt))

    def label_batch(rows):
        """Label every row in the batch through ONE bounded pool over all
        (row, judge) calls, so labeling parallelizes across rows and judges
        while staying capped at `workers` (controlled concurrency, not a
        burst). Verdicts regroup by row and majority-vote inline."""
        jobs = [(ri, j, r["prompt"]) for ri, r in enumerate(rows) for j in JUDGES]
        verdicts = _pool_map(lambda job: parse_verdict(chat(job[1], JUDGE_SYS, job[2])[0]),
                             jobs, workers)
        by_row = {}
        for (ri, _j, _p), v in zip(jobs, verdicts):
            by_row.setdefault(ri, []).append(v)
        for ri, r in enumerate(rows):
            votes = by_row.get(ri, [])
            r["judge_votes"] = votes
            r["majority"] = majority_vote(votes)
            r["agrees"] = (r["majority"] == r["constructed_label"])

    all_rows = []
    with open(out_path, "w") as sink:
        for start in range(0, len(cells), CHUNK):
            batch = cells[start:start + CHUNK]
            batch_rows = [r for rows in _pool_map(gen_cell, batch, workers) for r in rows]
            if os.environ.get("SKIP_JUDGE") == "1":
                for r in batch_rows:  # by-construction labels; fast-probe (§5.5)
                    r["judge_votes"] = []; r["majority"] = r["constructed_label"]
                    r["agrees"] = None
            else:
                label_batch(batch_rows)
            for r in batch_rows:
                sink.write(json.dumps(r) + "\n")
            all_rows += batch_rows
            m = pilot_metrics(all_rows)
            log(f"  cells {min(start + CHUNK, len(cells))}/{len(cells)}  "
                f"rows={m['n']}  agree={m.get('label_agreement')} "
                f"safe={m.get('safe_agreement')} unsafe={m.get('unsafe_agreement')} "
                f"div={m.get('diversity')} undecided={m.get('undecided')}")

    m = pilot_metrics(all_rows)
    log(f"DONE rows={m['n']} agree={m.get('label_agreement')} "
        f"safe={m.get('safe_agreement')} unsafe={m.get('unsafe_agreement')} "
        f"div={m.get('diversity')} len_ok={m.get('length_ok')} "
        f"undecided={m.get('undecided')}")
    open(out_path.replace(".jsonl", "_metrics.json"), "w").write(json.dumps(m, indent=2))
    return m


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--n-pairs", type=int, default=3, help="pairs per cell")
    p.add_argument("--max-cells", type=int, default=0,
                   help="cap cells per topic (0 = no cap); use for the pilot")
    p.add_argument("--topics", nargs="*", default=None,
                   help="restrict to these topics (default: all but held-back)")
    p.add_argument("--include-hold", action="store_true",
                   help="include offensive-by-construction topics (needs sign-off)")
    p.add_argument("--out", default="results/pilot.jsonl")
    p.add_argument("--workers", type=int, default=6)
    args = p.parse_args()
    run(args.n_pairs, args.max_cells, args.out, args.workers,
        args.topics, args.include_hold)


if __name__ == "__main__":
    main()
