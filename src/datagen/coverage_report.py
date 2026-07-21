"""Coverage / diversity report per corpus version (T27, §4.4.5 check #3).

"Diverse" as a measured claim, not an assertion. For each corpus version:
  - grid coverage: distinct (topic x mechanism x shape x depth x form) cells
    with >=1 row, and the fraction of the buildable grid they fill
  - per-topic row distribution
  - distinct-prompt ratio (exact-dup rate)
  - lexical diversity: distinct token trigrams / total trigrams ($0, no
    embedding deps; a cheap Vendi-style spread proxy)

Run across versions to show coverage GROWING (the loop's promise):
    python3 -m src.datagen.coverage_report \
        --corpora results/train_data.jsonl:v1 \
                   results/train_data_v2.jsonl:v2 \
                   results/train_data_v3.jsonl:v3 \
        --out results/coverage_report.json
"""

import argparse
import json
import re
from collections import Counter

CELL_KEYS = ("topic", "mechanism", "interaction_shape",
             "information_depth", "content_form")
_TOK = re.compile(r"[a-z0-9]+")


def trigrams(text):
    toks = _TOK.findall(text.lower())
    return {tuple(toks[i:i + 3]) for i in range(len(toks) - 2)}


def report(rows):
    prompts = [r.get("prompt", "") for r in rows]
    cells = {tuple(str(r.get(k, "-")) for k in CELL_KEYS) for r in rows}
    topics = Counter(r.get("topic") for r in rows)
    all_tri, seen_tri = 0, set()
    for p in prompts:
        toks = _TOK.findall(p.lower())
        for i in range(len(toks) - 2):
            all_tri += 1
            seen_tri.add(tuple(toks[i:i + 3]))
    return {
        "n_rows": len(rows),
        "n_cells_covered": len(cells),
        "distinct_prompt_ratio": round(len(set(prompts)) / len(prompts), 4) if prompts else 0,
        "lexical_diversity_trigram": round(len(seen_tri) / all_tri, 4) if all_tri else 0,
        "topics": dict(topics.most_common()),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpora", nargs="+", required=True,
                    help="path:label pairs")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    out = {}
    for spec in args.corpora:
        path, _, label = spec.partition(":")
        label = label or path
        rows = [json.loads(l) for l in open(path) if l.strip()]
        out[label] = report(rows)

    with open(args.out, "w") as f:
        json.dump(out, f, indent=1)
    print(f"{'ver':5} {'rows':>6} {'cells':>6} {'distinct':>9} {'lex-div':>8}")
    for label, r in out.items():
        print(f"{label:5} {r['n_rows']:>6} {r['n_cells_covered']:>6} "
              f"{r['distinct_prompt_ratio']:>9} {r['lexical_diversity_trigram']:>8}")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
