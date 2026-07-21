"""Manifest-driven corpus assembly with rollback (data lineage).

A corpus version is a named list of packs in results/corpus_manifest.json.
This builds a version by concatenating its packs, applying each pack's filter
(e.g. majority==unsafe for anchor packs), decontaminating vs XSTest, and
deduping. Because the corpus is *declared* (not accumulated ad-hoc), rollback
is one edit: drop a pack from the version's list and rebuild.

    # build a version as declared
    python3 -m src.datagen.build_corpus --version it6 --out results/train_data_it6.jsonl
    # rollback experiment: same version minus one pack
    python3 -m src.datagen.build_corpus --version it6 --drop privacy_pack --out results/train_data_it6_noprivpack.jsonl
"""

import argparse
import json

from src.datagen.decon import load_xstest_prompts, max_similarity, normalize


def load_pack(spec):
    rows = [json.loads(l) for l in open(spec["file"]) if l.strip()]
    filt = spec.get("filter")
    if filt == "majority==unsafe":
        rows = [r for r in rows if r.get("majority") == "unsafe"]
        for r in rows:  # anchor packs carry construction label via majority
            r.setdefault("constructed_label", r.get("majority"))
    return [r for r in rows if r.get("prompt") and r.get("constructed_label") in ("safe", "unsafe")]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default="results/corpus_manifest.json")
    ap.add_argument("--version", required=True)
    ap.add_argument("--drop", nargs="*", default=[], help="pack names to exclude (rollback)")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    man = json.load(open(args.manifest))
    packs = man["versions"][args.version]["packs"]
    use = [p for p in packs if p not in args.drop]
    print(f"version {args.version}: packs {use}" + (f"  (dropped {args.drop})" if args.drop else ""))

    rows = []
    for name in use:
        pr = load_pack(man["packs"][name])
        rows += pr
        print(f"  {name}: +{len(pr)}")

    xs = [normalize(p) for p in load_xstest_prompts()]
    seen, out = set(), []
    n_decon = 0
    for r in rows:
        if max_similarity(r["prompt"], xs)[0] >= 0.6:
            n_decon += 1
            continue
        if r["prompt"] in seen:
            continue
        seen.add(r["prompt"])
        out.append(r)

    with open(args.out, "w") as f:
        f.write("\n".join(json.dumps(r) for r in out) + "\n")
    from collections import Counter
    lab = Counter(r["constructed_label"] for r in out)
    print(f"-> {args.out}: {len(out)} rows (dropped {n_decon} decon, {len(rows)-len(out)-n_decon} dup); "
          f"safe {lab['safe']} unsafe {lab['unsafe']}")


if __name__ == "__main__":
    main()
