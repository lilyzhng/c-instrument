"""Draw the T11.2 human-audit sample: ~1% of the corpus, stratified by
(topic, label) so every family a human signs off on is represented. Deterministic
(seeded) so the sample is reproducible and re-drawable after a regenerate.

Usage: python3 -m src.datagen.audit_sample \
    --rows results/train_data.jsonl --n 21 --out results/audit_sample.jsonl
"""

import argparse
import json
import random
from collections import defaultdict


def stratified_sample(rows, n, seed=0):
    """Proportional allocation over (topic, label) strata, >=1 per stratum
    while budget allows; deterministic under a fixed seed."""
    strata = defaultdict(list)
    for r in rows:
        strata[(r.get("topic", "?"), r.get("constructed_label", "?"))].append(r)
    rng = random.Random(seed)
    keys = sorted(strata, key=lambda k: -len(strata[k]))
    picked = []
    # first pass: one from each stratum (largest first) until budget
    for k in keys[:n]:
        picked.append(rng.choice(strata[k]))
    # second pass: fill remaining budget proportionally
    total = sum(len(v) for v in strata.values())
    while len(picked) < n:
        k = rng.choices(keys, weights=[len(strata[k]) / total for k in keys])[0]
        cand = rng.choice(strata[k])
        if cand not in picked:
            picked.append(cand)
    return picked[:n]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", required=True)
    ap.add_argument("--n", type=int, default=21)
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    with open(args.rows) as f:
        rows = [json.loads(line) for line in f if line.strip()]
    picked = stratified_sample(rows, args.n, args.seed)
    with open(args.out, "w") as f:
        for r in picked:
            f.write(json.dumps({
                "prompt": r.get("prompt"),
                "constructed_label": r.get("constructed_label"),
                "judge_majority": r.get("majority"),
                "topic": r.get("topic", "?"),
                "human_verdict": "",   # human fills: ok / wrong-label / bad-prompt
            }, ensure_ascii=False) + "\n")
    by = defaultdict(int)
    for r in picked:
        by[(r.get("topic", "?"), r.get("constructed_label", "?"))] += 1
    print(f"wrote {len(picked)} rows -> {args.out}")
    for k in sorted(by):
        print(f"  {k[0]}/{k[1]}: {by[k]}")


if __name__ == "__main__":
    main()
