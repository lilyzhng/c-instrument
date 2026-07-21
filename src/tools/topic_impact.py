#!/usr/bin/env python3
"""T51 (s5.7 Move 6): measure a new topic's GLOBAL impact + apply the benefit gate.

Topic expansion adds a new board row. The risk is negative transfer: the new
topic could help itself but hurt topics already learned (cross-task transfer is
counterintuitive, arXiv:2509.13624). This is the leave-one-out / data-valuation
measurement (MobileLLM-Pro LOO 2511.06719, DataInf 2310.00902) made concrete on
our per-family scores.

Inputs:
  --baseline  loop-run XSTest json (no new topic), e.g. grpo-t24-loop-r1_step_150
  --topic     topic-run XSTest json (with new topic)
  --new-probe (optional) the new topic's fresh-probe pass rate (its own learning)

Benefit gate (keep the topic only if all hold):
  G1 new topic learns          new-probe pass >= --learn-floor (default 0.70)
  G2 global does not regress    mean per-family delta >= --global-floor (-0.01)
  G3 no negative transfer       no existing family drops more than --nt-floor (0.05)

Usage: python3 src/tools/topic_impact.py --baseline <b.json> --topic <t.json>
"""

import argparse
import json


def per_family(path):
    d = json.load(open(path))
    m = d.get("metrics", d)
    return m["per_family_acc"], m


def measure(baseline_path, topic_path, new_probe, learn_floor, global_floor, nt_floor):
    base_fam, base_m = per_family(baseline_path)
    topic_fam, topic_m = per_family(topic_path)
    fams = sorted(set(base_fam) & set(topic_fam))
    deltas = {f: round(topic_fam[f] - base_fam[f], 3) for f in fams}
    mean_delta = round(sum(deltas.values()) / len(deltas), 4) if deltas else 0.0
    worst = min(deltas.items(), key=lambda kv: kv[1]) if deltas else (None, 0.0)

    g1 = new_probe is None or new_probe >= learn_floor
    g2 = mean_delta >= global_floor
    g3 = worst[1] >= -nt_floor
    keep = g1 and g2 and g3
    return {
        "per_family_delta": deltas,
        "mean_family_delta": mean_delta,
        "worst_family": {"family": worst[0], "delta": worst[1]},
        "new_topic_probe": new_probe,
        "global_balanced": {"baseline": round(base_m["balanced_acc"], 4),
                            "topic": round(topic_m["balanced_acc"], 4)},
        "gate": {
            "G1_new_topic_learns": bool(g1),
            "G2_global_no_regress": bool(g2),
            "G3_no_negative_transfer": bool(g3),
            "KEEP": bool(keep),
        },
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--topic", required=True)
    ap.add_argument("--new-probe", type=float)
    ap.add_argument("--learn-floor", type=float, default=0.70)
    ap.add_argument("--global-floor", type=float, default=-0.01)
    ap.add_argument("--nt-floor", type=float, default=0.05)
    ap.add_argument("--out")
    args = ap.parse_args()
    r = measure(args.baseline, args.topic, args.new_probe,
                args.learn_floor, args.global_floor, args.nt_floor)
    if args.out:
        json.dump(r, open(args.out, "w"), indent=1)
    print(f"mean family delta {r['mean_family_delta']:+}  "
          f"worst {r['worst_family']['family']} {r['worst_family']['delta']:+}")
    print(f"global balanced {r['global_balanced']['baseline']} -> "
          f"{r['global_balanced']['topic']}")
    print(f"gate: {r['gate']}")
    for f, d in sorted(r["per_family_delta"].items(), key=lambda kv: kv[1]):
        print(f"  {f:22} {d:+}")


if __name__ == "__main__":
    main()
