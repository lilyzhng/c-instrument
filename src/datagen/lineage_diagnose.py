"""Auto-verdict engine: turn the data->model lineage into agent traces that
flag dead-weight packs EARLY, instead of a human noticing three iterations later.

For each corpus version in the manifest, it emits a trace record:
  { version, packs_added, hypothesis (each pack's purpose), measured outcome
    (the model's metrics + delta vs prior), verdict (helped/neutral/hurt),
    action (keep / prune-candidate / ablate) }

The core rule: a pack that ADDS rows to a target family but does NOT move that
family's metric is a PRUNE CANDIDATE. This is exactly the privacy_pack case
(v1->v2: +187 privacy rows, privacy 0.733->0.733) — the verdict fires
automatically from the numbers, no conversation required.

    python3 -m src.datagen.lineage_diagnose --manifest results/corpus_manifest.json
"""

import argparse
import json

NEUTRAL_EPS = 0.005  # a family delta within +/- this is "no move"


def diagnose(man):
    versions = list(man["versions"].items())
    traces = []
    for i, (vname, v) in enumerate(versions):
        prior = versions[i - 1][1] if i > 0 else None
        added = [] if not prior else [p for p in v["packs"] if p not in prior["packs"]]
        m, pm = v.get("metrics", {}), (prior or {}).get("metrics", {})
        d_safe = None if not (m.get("safe_acc") and pm.get("safe_acc")) else round(m["safe_acc"] - pm["safe_acc"], 3)
        d_priv = None if not (m.get("privacy_family") and pm.get("privacy_family")) else round(m["privacy_family"] - pm["privacy_family"], 3)
        d_asr = None if (m.get("asr") is None or pm.get("asr") is None) else round(m["asr"] - pm["asr"], 3)

        # verdict logic
        verdict, action = "pending", "wait for metrics"
        if m:
            helped = (d_safe and d_safe > NEUTRAL_EPS) or (d_asr and d_asr < -NEUTRAL_EPS)
            hurt = (d_safe and d_safe < -NEUTRAL_EPS)
            # dead-weight rule: a privacy-targeting pack that didn't move privacy
            priv_pack_added = any("privacy" in p for p in added)
            priv_flat = d_priv is not None and abs(d_priv) <= NEUTRAL_EPS
            if priv_pack_added and priv_flat:
                verdict = "NEUTRAL-TO-NEGATIVE (dead-weight privacy pack)"
                action = "PRUNE CANDIDATE -> run with/without ablation"
            elif helped:
                verdict = "HELPED"; action = "keep"
            elif hurt:
                verdict = "HURT"; action = "PRUNE CANDIDATE"
            else:
                verdict = "NEUTRAL"; action = "keep, low priority to prune"

        traces.append({
            "version": vname, "packs_added": added,
            "hypothesis": {p: man["packs"][p]["purpose"] for p in added},
            "outcome": {"safe_acc_delta": d_safe, "privacy_delta": d_priv, "asr_delta": d_asr},
            "verdict": verdict, "action": action,
        })
    return traces


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default="results/corpus_manifest.json")
    ap.add_argument("--out", default="results/lineage_traces.json")
    args = ap.parse_args()
    man = json.load(open(args.manifest))
    traces = diagnose(man)
    json.dump(traces, open(args.out, "w"), indent=1)
    print(f"{'version':6} {'added packs':40} {'Δsafe':>6} {'Δpriv':>6} {'Δasr':>6}  verdict")
    for tr in traces:
        o = tr["outcome"]
        print(f"{tr['version']:6} {','.join(tr['packs_added'])[:40]:40} "
              f"{str(o['safe_acc_delta']):>6} {str(o['privacy_delta']):>6} {str(o['asr_delta']):>6}  "
              f"{tr['verdict']} -> {tr['action']}")
    print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
