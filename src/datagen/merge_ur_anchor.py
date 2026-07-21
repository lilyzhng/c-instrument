"""Merge the T8c judge-verified disguised-unsafe rows (the under-refusal
anchor) into the training corpus, fixing the privacy-family unsafe regression
seen at grpo-2k step 25 (s5.4 T13 finding #2).

Pilot rows carry judge_votes/majority but not the corpus fields; a row whose
majority is 'unsafe' was constructed as unsafe and verified by the ensemble,
so constructed_label='unsafe', agrees=True, mechanism=framing.

Usage: python3 -m src.datagen.merge_ur_anchor \
    --corpus results/train_data.jsonl --pilot results/underrefusal_pilot.jsonl \
    --out results/train_data_ur.jsonl
"""

import argparse
import json


def anchor_rows(pilot_rows):
    for r in pilot_rows:
        if r.get("majority") != "unsafe":
            continue
        yield {
            "topic": r["topic"],
            "mechanism": f"disguise_{r['framing']}",
            "constructed_label": "unsafe",
            "prompt": r["prompt"],
            "judge_votes": r["judge_votes"],
            "majority": r["majority"],
            "agrees": True,
        }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", required=True)
    ap.add_argument("--pilot", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    corpus = [json.loads(l) for l in open(args.corpus) if l.strip()]
    pilot = [json.loads(l) for l in open(args.pilot) if l.strip()]
    anchors = list(anchor_rows(pilot))
    with open(args.out, "w") as f:
        for r in corpus + anchors:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    topics = {}
    for a in anchors:
        topics[a["topic"]] = topics.get(a["topic"], 0) + 1
    print(f"corpus {len(corpus)} + anchors {len(anchors)} -> {args.out}; anchor topics: {topics}")


if __name__ == "__main__":
    main()
