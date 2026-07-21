"""Triage actuator: turn auto-verdicts into concrete, runnable experiments.

lineage_diagnose.py flags WHAT is suspect (a prune-candidate pack). This turns
that flag into HOW to confirm it: a disambiguating experiment spec the agent
can execute. It closes the loop the human keeps closing by hand ("this data
doesn't help, but C-vs-D is confounded, so run the clean ablation").

Rule: a PRUNE CANDIDATE pack cannot be judged from the existing runs (they
changed several things at once). The only clean test is a same-everything-else
ablation: build the latest corpus WITH and WITHOUT the pack, train both, compare
on the pack's target metric. This function emits exactly that spec.

    python3 -m src.datagen.propose_experiment --traces results/lineage_traces.json --manifest results/corpus_manifest.json
"""

import argparse
import json


def latest_version_with(pack, man):
    hits = [v for v, spec in man["versions"].items() if pack in spec["packs"]]
    return hits[-1] if hits else None


def propose(traces, man):
    props = []
    for tr in traces:
        if "PRUNE CANDIDATE" not in tr["action"] and "PRUNE CANDIDATE" not in tr["verdict"]:
            continue
        # which pack is suspect: the newly-added pack matching the verdict
        suspects = [p for p in tr["packs_added"] if "privacy" in p] or tr["packs_added"]
        for pack in suspects:
            latest = latest_version_with(pack, man)
            if not latest:
                continue
            target = "privacy_family" if "privacy" in pack else "safe_acc"
            props.append({
                "trigger": f"{tr['version']} verdict: {tr['verdict']}",
                "suspect_pack": pack,
                "why_cant_conclude": "existing runs changed multiple packs at once (confounded); no isolated with/without exists",
                "experiment": "ablation: build latest corpus WITH vs WITHOUT the pack, same lr/n/steps, compare",
                "commands": [
                    f"python3 -m src.datagen.build_corpus --version {latest} --out results/train_data_{latest}.jsonl",
                    f"python3 -m src.datagen.build_corpus --version {latest} --drop {pack} --out results/train_data_{latest}_no_{pack}.jsonl",
                    f"# train both, eval, compare {target} + aggregate safe_acc",
                ],
                "decision_rule": f"if WITHOUT >= WITH on {target} and aggregate -> PRUNE {pack} from the manifest (all versions); else keep",
            })
    return props


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--traces", default="results/lineage_traces.json")
    ap.add_argument("--manifest", default="results/corpus_manifest.json")
    ap.add_argument("--out", default="results/proposed_experiments.json")
    args = ap.parse_args()
    props = propose(json.load(open(args.traces)), json.load(open(args.manifest)))
    json.dump(props, open(args.out, "w"), indent=1)
    if not props:
        print("no prune candidates -> no experiment proposed")
    for p in props:
        print(f"PROPOSED: ablate '{p['suspect_pack']}' (trigger: {p['trigger']})")
        print(f"  why: {p['why_cant_conclude']}")
        print(f"  rule: {p['decision_rule']}")
    print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
