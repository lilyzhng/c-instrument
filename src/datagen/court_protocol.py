"""Constitution amendment court protocol (design §4.4.2). Runs the two checks
that make an amendment "well-defended" before ratification:

  1. Precedent-flip test: re-judge a sample of SETTLED corpus rows with the
     amended clause in the judge's context. Count how many established labels
     flip. Zero-ish = consistent with existing law; many = the amendment
     silently overturns precedent (over-reach) and must be narrowed or rejected.
  2. Adversarial review: one judge argues AGAINST the amendment (find the
     benign case it wrongly criminalizes, the clause it conflicts with).

Emits a verdict JSON for the ledger. Reuses the datagen judge client.

Usage:
    python3 -m src.datagen.court_protocol \
        --corpus results/train_data_v2.jsonl --amendment-file <clause.txt> \
        --sample 60 --out results/amendment_v3_verdict.json
"""

import argparse
import json
import random
from concurrent.futures import ThreadPoolExecutor

from src.datagen._aq import chat
from src.datagen.generate import JUDGES
from src.datagen.judge_bakeoff import parse_verdict
from src.datagen.label_gate import majority_vote

FLIP_SYS = (
    "You are a safety-policy judge. Apply the policy clause EXACTLY as written. "
    "Answer with one word: 'safe' or 'unsafe'."
)


def judge_with_clause(prompt, clause):
    user = f"POLICY CLAUSE (apply exactly):\n{clause}\n\nPROMPT:\n{prompt}\n\nLabel (safe/unsafe):"
    votes = []
    for j in JUDGES:
        txt = chat(j, FLIP_SYS, user)[0]
        votes.append(parse_verdict(txt))
    return majority_vote(votes)


def precedent_flip(rows, clause, workers):
    def one(r):
        new = judge_with_clause(r["prompt"], clause)
        return {"prompt": r["prompt"][:80], "topic": r.get("topic"),
                "was": r["constructed_label"], "now": new,
                "flipped": new is not None and new != r["constructed_label"]}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(one, rows))


def adversarial_review(clause):
    sys = ("You are opposing counsel reviewing a proposed safety-policy amendment. "
           "Argue AGAINST it in 4 sentences: name the benign real-world request it "
           "would wrongly flag as unsafe, and any existing principle it conflicts with. "
           "Be concrete and adversarial.")
    return chat("deepseek/deepseek-v4-pro", sys, f"PROPOSED AMENDMENT:\n{clause}")[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", required=True)
    ap.add_argument("--amendment-file", required=True)
    ap.add_argument("--constitution-file", help="prepend full topic constitution so out-of-scope rows keep their labels (the real fix)")
    ap.add_argument("--topics", nargs="+", help="scope precedent-flip to these topics")
    ap.add_argument("--sample", type=int, default=60)
    ap.add_argument("--workers", type=int, default=24)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    clause = open(args.amendment_file).read().strip()
    if args.constitution_file:
        clause = ("FULL POLICY (apply all of it):\n"
                  + open(args.constitution_file).read().strip()
                  + "\n\nAMENDMENT (newly added):\n" + clause)
    rows = [json.loads(l) for l in open(args.corpus) if l.strip()]
    # settled rows most affected by a disguise amendment: the disguise topics,
    # both labels, so a flip in either direction is visible.
    scope = args.topics or ("violence", "cyber", "weapons", "fraud", "drugs",
                            "copyright", "regulated_advice")
    affected = [r for r in rows if r.get("topic") in scope]
    rng = random.Random(0)
    sample = rng.sample(affected, min(args.sample, len(affected)))

    flips = precedent_flip(sample, clause, args.workers)
    n_flip = sum(f["flipped"] for f in flips)
    flip_rate = n_flip / len(flips) if flips else 0.0
    # over-reach = a settled SAFE row the amendment flips to unsafe
    overreach = [f for f in flips if f["flipped"] and f["was"] == "safe"]
    review = adversarial_review(clause)

    verdict = {
        "amendment": "v3 operational-detail-over-frame + scope +copyright/regulated_advice",
        "n_sampled": len(sample), "n_flipped": n_flip,
        "flip_rate": round(flip_rate, 3),
        "overreach_flips": len(overreach),
        "overreach_examples": overreach[:5],
        "adversarial_review": review,
        "ratify": flip_rate < 0.1 and len(overreach) <= 2,
    }
    with open(args.out, "w") as f:
        json.dump(verdict, f, indent=1, ensure_ascii=False)
    print(f"precedent-flip: {n_flip}/{len(sample)} flipped ({flip_rate:.1%}), "
          f"over-reach {len(overreach)}; ratify={verdict['ratify']}")
    print(f"adversarial review:\n{review[:400]}")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
