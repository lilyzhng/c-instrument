"""Decontamination vs XSTest (pilot spot-check + T9 corpus filter).

The decontamination rule is strict: no XSTest prompt may seed our data, and no
generated row may be a near-duplicate of an eval prompt (that would inflate
the score by memorization). We measure each generated prompt's maximum
similarity to the 450 XSTest prompts and flag anything above a threshold.

Similarity is token-Jaccard on normalized word sets: cheap, dependency-free,
and conservative (it catches lexical overlap, the failure we care about;
paraphrase-level leakage is caught later by the eval being held out). In the
pilot it is a *check* on the recipe; on the full corpus (T9) it is the
*filter* that drops flagged rows before training.

Pure logic (normalize, jaccard, max_similarity, decon_report) is unit-tested
in src/tests/test_decon.py; only load_xstest_prompts touches disk.
"""

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.getcwd())

WORD = re.compile(r"[a-z0-9']+")
DEFAULT_THRESHOLD = 0.6  # max token-Jaccard allowed vs any XSTest prompt


# ---- pure logic (unit-tested, no disk) ----

def normalize(text):
    """Lowercased word-token set (punctuation dropped). The unit of overlap."""
    return set(WORD.findall((text or "").lower()))


def jaccard(a, b):
    """|A∩B| / |A∪B| for two token sets; 0 when both empty."""
    if not a and not b:
        return 0.0
    return len(a & b) / len(a | b)


def max_similarity(prompt, corpus_sets):
    """Highest token-Jaccard between a prompt and any XSTest prompt (as
    pre-normalized token sets). Returns (score, index_of_closest)."""
    pset = normalize(prompt)
    best, best_i = 0.0, -1
    for i, cset in enumerate(corpus_sets):
        s = jaccard(pset, cset)
        if s > best:
            best, best_i = s, i
    return best, best_i


def decon_report(prompts, xstest_prompts, threshold=DEFAULT_THRESHOLD):
    """Max-similarity for every prompt vs the XSTest set, plus the flagged
    (>= threshold) rows and summary stats. flagged rows are what T9 drops."""
    corpus = [normalize(x) for x in xstest_prompts]
    sims = []
    for p in prompts:
        score, idx = max_similarity(p, corpus)
        sims.append({"prompt": p, "max_sim": round(score, 3),
                     "closest_xstest": xstest_prompts[idx] if idx >= 0 else None})
    flagged = [s for s in sims if s["max_sim"] >= threshold]
    overall_max = max((s["max_sim"] for s in sims), default=0.0)
    mean = round(sum(s["max_sim"] for s in sims) / len(sims), 3) if sims else 0.0
    return {
        "n": len(prompts),
        "threshold": threshold,
        "overall_max_sim": overall_max,
        "mean_max_sim": mean,
        "n_flagged": len(flagged),
        "flagged": flagged,
    }


# ---- disk IO (not in the pure path) ----

def load_xstest_prompts():
    from src.harness.xstest import load_xstest
    return [r["prompt"] for r in load_xstest()]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--rows", default="results/pilot.jsonl",
                   help="JSONL with a 'prompt' field per row")
    p.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
    p.add_argument("--out", default="results/decon_report.json")
    args = p.parse_args()

    prompts = [json.loads(l)["prompt"] for l in open(args.rows)]
    rep = decon_report(prompts, load_xstest_prompts(), args.threshold)
    with open(args.out, "w") as f:
        json.dump(rep, f, indent=2)
    print(f"n={rep['n']}  overall_max_sim={rep['overall_max_sim']}  "
          f"mean={rep['mean_max_sim']}  flagged(>={args.threshold})={rep['n_flagged']}")
    for s in rep["flagged"][:10]:
        print(f"  [{s['max_sim']}] {s['prompt']}")
        print(f"        ~ {s['closest_xstest']}")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
