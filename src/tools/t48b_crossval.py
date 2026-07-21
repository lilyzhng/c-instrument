#!/usr/bin/env python3
"""T48b (s5.7): retro-diagnosis cross-validation of the cell classifier.

Ground truth (fixed BEFORE seeing the classifier output, from the historical
record): the privacy region was manually diagnosed dead-weight — privacy
accuracy flat 0.72-0.73 across corpus v1->v3, the privacy_pack was discarded
(s5.5 leaderboard Group C), and the eventual fix required new sub-patterns
(it6 hardex), which are absent from both T24 corpora. Prediction: privacy
cells classify stuck/degrading ("needs intervention") on T24 runs.

Test: treat {stuck, degrading} as the automatic "needs intervention" flag and
{topic == privacy} as ground-truth positive. Report precision/recall +
the per-topic class table. An honest negative (privacy not flagged) is
reported, not hidden.

Usage: python3 src/tools/t48b_crossval.py --impact results/t48/impact_<exp>.json
"""

import argparse
import json
from collections import defaultdict

FLAG_CLASSES = {"stuck", "degrading"}
GT_TOPIC = "privacy"


def crossval(impact):
    per_topic = defaultdict(lambda: defaultdict(int))
    tp = fp = fn = tn = 0
    for c in impact["cells"]:
        topic = c["cell"].split("|")[0]
        per_topic[topic][c["class"]] += 1
        flagged = c["class"] in FLAG_CLASSES
        is_gt = topic == GT_TOPIC
        tp += flagged and is_gt
        fp += flagged and not is_gt
        fn += (not flagged) and is_gt
        tn += (not flagged) and not is_gt
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    return {
        "exp": impact["exp"],
        "flag_classes": sorted(FLAG_CLASSES), "gt_topic": GT_TOPIC,
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        "precision": None if precision is None else round(precision, 3),
        "recall": None if recall is None else round(recall, 3),
        "per_topic": {t: dict(v) for t, v in sorted(per_topic.items())},
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--impact", required=True)
    ap.add_argument("--out")
    args = ap.parse_args()
    impact = json.load(open(args.impact))
    result = crossval(impact)
    out = args.out or args.impact.replace("impact_", "crossval_")
    with open(out, "w") as f:
        json.dump(result, f, indent=1)
    print(f"{result['exp']}: flag={result['flag_classes']} vs gt topic={GT_TOPIC}")
    print(f"tp={result['tp']} fp={result['fp']} fn={result['fn']} tn={result['tn']}"
          f"  precision={result['precision']} recall={result['recall']}")
    print(f"{'topic':18} classes")
    for t, v in result["per_topic"].items():
        print(f"{t:18} {dict(v)}")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
