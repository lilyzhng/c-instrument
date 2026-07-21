#!/usr/bin/env python3
"""T49 S7 (s5.7): turn a ratified amendment into PAIRED training data.

The attack channel found loopholes (a topic under a disguise framing where the
guard is fooled); the court protocol ratified a clause sharpening that boundary.
This turns the clause into data — but PAIRED, per the harmony constraint: for
each loophole cell we generate BOTH the disguised-unsafe row (labeled unsafe,
the catch the guard was missing) AND a safe twin in the SAME framing (labeled
safe, so sharpening the boundary does not cause over-refusal on legitimate
same-framed requests). Attack-only data is exactly what drifted T24's routed arm.

Cells are declared inline (the two T49-ratified loopholes). Each row is judged by
the ensemble and decon-screened vs XSTest, same as every other pack, then written
with constructed_label so prepare_data.py can consume it.

Usage: AQ_KEY=... PYTHONPATH=. python3 src/datagen/amendment_pack.py \
           [--n 12] [--out results/amendment_pack_t49.jsonl]
"""

import argparse
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.getcwd())
from src.datagen._aq import chat  # noqa: E402
from src.datagen.judge_bakeoff import SYS as JUDGE_SYS, parse_verdict  # noqa: E402
from src.datagen.label_gate import majority_vote  # noqa: E402
from src.datagen.decon import (  # noqa: E402
    load_xstest_prompts, max_similarity, normalize, DEFAULT_THRESHOLD)

JUDGES = ["deepseek/deepseek-v4-pro", "openai/gpt-5.6-sol", "x-ai/grok-4.5"]

# The two T49-ratified loopholes (attack_grpo-t24-routed-r1.json).
CELLS = [
    {"topic": "fraud", "framing": "indirect",
     "unsafe": "seeks operational help to COMMIT fraud (fake invoices, chargeback "
               "abuse, synthetic identity, laundering, phishing setup) phrased "
               "indirectly / hypothetically / 'asking for a friend' / euphemistically",
     "safe": "a legitimately-framed same-topic request that is SAFE: understanding "
             "how a scam works to avoid it, reporting fraud, an AUTHORIZED phishing "
             "simulation for team training with stated purpose, journalism"},
    {"topic": "regulated_advice", "framing": "roleplay",
     "unsafe": "seeks harmful/unlicensed operational advice (specific self-dosing "
               "amount, concrete tax-evasion method, risky self-procedure) wrapped "
               "in a roleplay/persona frame ('as my unlicensed-doctor character')",
     "safe": "a roleplay/persona-framed request that stays SAFE: general info, a "
             "definition, education, or 'when to see a professional', with no "
             "harmful operational specifics"},
]

GEN_SYS = (
    "You generate SHORT realistic user PROMPTS (median ~15 words) for a safety "
    "classifier training set. You write prompts only, never answers. Output ONLY "
    "a JSON array of objects, each {\"safe\": \"...\", \"unsafe\": \"...\"} — the "
    "two must share the SAME framing/wrapper and topic, differing only in whether "
    "the operational content is harmful. Vary entities; no famous/canonical cases."
)


def build_prompt(cell, n):
    return (f"Topic: {cell['topic']}. Framing/wrapper: {cell['framing']}.\n"
            f"unsafe side: {cell['unsafe']}.\n"
            f"safe twin: {cell['safe']}.\n"
            f"Write {n} contrast pairs. Both sides MUST use the {cell['framing']} "
            f"framing; keep the unsafe side claim-shape (no step-by-step). "
            f"Output only the JSON array.")


def parse_pairs(text):
    try:
        start, end = text.index("["), text.rindex("]") + 1
        return json.loads(text[start:end])
    except (ValueError, json.JSONDecodeError):
        return []


def label_row(prompt, workers):
    with ThreadPoolExecutor(max_workers=workers) as pool:
        votes = list(pool.map(
            lambda j: parse_verdict(chat(j, JUDGE_SYS, prompt)[0]), JUDGES))
    return votes


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n", type=int, default=12, help="pairs per cell")
    ap.add_argument("--workers", type=int, default=24)
    ap.add_argument("--out", default="results/amendment_pack_t49.jsonl")
    args = ap.parse_args()

    raw = []
    for cell in CELLS:
        txt, _ok, _ra = chat("z-ai/glm-5.2", GEN_SYS,
                             build_prompt(cell, args.n), max_tokens=4000,
                             temperature=0.9)
        for d in parse_pairs(txt):
            base = {"topic": cell["topic"], "mechanism": f"disguise_{cell['framing']}",
                    "framing": cell["framing"]}
            if d.get("safe"):
                raw.append({**base, "constructed_label": "safe", "prompt": d["safe"].strip()})
            if d.get("unsafe"):
                raw.append({**base, "constructed_label": "unsafe", "prompt": d["unsafe"].strip()})
    print(f"generated {len(raw)} rows across {len(CELLS)} loophole cells")

    # judge + decon
    corpus_sets = [normalize(x) for x in load_xstest_prompts()]
    kept = []
    for r in raw:
        votes = label_row(r["prompt"], args.workers)
        r["judge_votes"] = votes
        r["majority"] = majority_vote(votes)
        r["agrees"] = (r["majority"] == r["constructed_label"])
        if r["agrees"] and max_similarity(r["prompt"], corpus_sets)[0] < DEFAULT_THRESHOLD:
            kept.append(r)
    with open(args.out, "w") as f:
        for r in kept:
            f.write(json.dumps(r) + "\n")
    n = {"safe": sum(r["constructed_label"] == "safe" for r in kept),
         "unsafe": sum(r["constructed_label"] == "unsafe" for r in kept)}
    print(f"raw {len(raw)} -> judge-agreed+decon-clean {len(kept)} {n}")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
