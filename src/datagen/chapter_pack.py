#!/usr/bin/env python3
"""T50 (s5.7): generate a sub-constitution CHAPTER pack.

A stuck single-mechanism region (privacy|public-vs-private, flagged by C-LIM,
unmoved by flat volume) is promoted to a chapter: a deeper local sub-grid with
its own contrast axes (subject x info-type x framing), spec in
src/constitutions/chapters/privacy_chapter.md.

For each (info_type, framing) we generate a contrast pair that holds the info
type fixed and flips only the SUBJECT (safe public/fictional subject vs unsafe
private subject), so the model learns the subject axis is what flips the label.
This is the distinction flat expansion could not teach. Judged + decon as usual.

Usage: AQ_KEY=... PYTHONPATH=. python3 src/datagen/chapter_pack.py \
           [--n 3] [--out results/chapter_pack_privacy.jsonl]
"""

import argparse
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.getcwd())
from src.datagen._aq import chat  # noqa: E402
from src.datagen.judge_bakeoff import SYS as JUDGE_SYS, parse_verdict  # noqa: E402
from src.datagen.label_gate import majority_vote  # noqa: E402
from src.datagen.decon import (  # noqa: E402
    load_xstest_prompts, max_similarity, normalize, DEFAULT_THRESHOLD)

JUDGES = ["deepseek/deepseek-v4-pro", "openai/gpt-5.6-sol", "x-ai/grok-4.5"]

SAFE_SUBJECTS = ["a head of state", "a well-known CEO", "a sitting senator",
                 "a famous actor in their public role", "a comic-book superhero",
                 "an anime protagonist", "a video-game character",
                 "the White House", "a public university"]
UNSAFE_SUBJECTS = ["a named private neighbour", "my gardener", "my coworker",
                   "my child's teacher", "a specific private individual named "
                   "in a leaked list", "my landlord", "my employee"]
INFO = {
    "contact": "home address, phone, or whereabouts",
    "identifier": "SSN, date of birth, or credit-card number",
    "records": "financial, medical, or browsing-history records",
    "protected_attribute": "immigration status, religion, political affiliation, "
                           "union membership, or health condition",
}
FRAMING = {
    "direct": "Ask directly for the info.",
    "conversational": "Ask in first person, 'my X's Y' style, casual tone.",
    "aggregation": "Ask to combine public fragments to locate/track the person "
                   "(unsafe side only; safe side asks a general topic question).",
}

GEN_SYS = (
    "You write SHORT realistic user PROMPTS (median ~14 words) for a privacy "
    "safety classifier. Prompts only, never answers. Output ONLY a JSON array of "
    "{\"safe\": \"...\", \"unsafe\": \"...\"} objects. The two prompts must ask "
    "for the SAME info type in the SAME framing, differing only in the SUBJECT "
    "(safe = public figure / fictional / institution, unsafe = a real private "
    "individual). Vary entities, no canonical examples like the White House twice."
)


def build_prompt(info_key, info_desc, framing_key, framing_desc, n):
    return (f"Info type: {info_desc}. Framing: {framing_desc}\n"
            f"safe subject examples: {', '.join(SAFE_SUBJECTS[:5])}.\n"
            f"unsafe subject examples: {', '.join(UNSAFE_SUBJECTS[:5])}.\n"
            f"Write {n} contrast pairs for the '{framing_key}' framing about "
            f"'{info_key}'. Output only the JSON array.")


def parse_pairs(text):
    try:
        s, e = text.index("["), text.rindex("]") + 1
        return json.loads(text[s:e])
    except (ValueError, json.JSONDecodeError):
        return []


def label_row(prompt, workers):
    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(
            lambda j: parse_verdict(chat(j, JUDGE_SYS, prompt)[0]), JUDGES))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n", type=int, default=3, help="pairs per sub-cell")
    ap.add_argument("--workers", type=int, default=24)
    ap.add_argument("--out", default="results/chapter_pack_privacy.jsonl")
    args = ap.parse_args()

    cells = [(ik, idesc, fk, fdesc) for ik, idesc in INFO.items()
             for fk, fdesc in FRAMING.items()]
    def gen_cell(c):
        ik, idesc, fk, fdesc = c
        txt, _ok, _ra = chat("z-ai/glm-5.2", GEN_SYS,
                             build_prompt(ik, idesc, fk, fdesc, args.n),
                             max_tokens=3000, temperature=0.9)
        out=[]
        for d in parse_pairs(txt):
            base = {"topic": "privacy", "mechanism": "public-vs-private",
                    "info_type": ik, "framing": fk}
            if d.get("safe"): out.append({**base,"constructed_label":"safe","prompt":d["safe"].strip()})
            if d.get("unsafe"): out.append({**base,"constructed_label":"unsafe","prompt":d["unsafe"].strip()})
        return out
    with ThreadPoolExecutor(max_workers=12) as pool:
        raw = [r for rows in pool.map(gen_cell, cells) for r in rows]
    print(f"generated {len(raw)} rows over {len(INFO)}x{len(FRAMING)} sub-cells", flush=True)

    with open(args.out.replace(".jsonl","_raw.jsonl"),"w") as f:
        for r in raw: f.write(json.dumps(r)+"\n")
    corpus_sets = [normalize(x) for x in load_xstest_prompts()]
    def judge(r):
        votes = label_row(r["prompt"], 3)
        r["judge_votes"]=votes; r["majority"]=majority_vote(votes)
        r["agrees"]=(r["majority"]==r["constructed_label"]); return r
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        judged=list(pool.map(judge, raw))
    kept=[r for r in judged if r["agrees"] and
          max_similarity(r["prompt"], corpus_sets)[0] < DEFAULT_THRESHOLD]
    with open(args.out, "w") as f:
        for r in kept:
            f.write(json.dumps(r) + "\n")
    n = {"safe": sum(r["constructed_label"] == "safe" for r in kept),
         "unsafe": sum(r["constructed_label"] == "unsafe" for r in kept)}
    print(f"raw {len(raw)} -> judge-agreed+decon-clean {len(kept)} {n}")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
