"""OOD benchmark loaders: ToxicChat + WildGuardTest (real-world usefulness).

Rows are normalized to the harness's XSTest row shape (id, prompt, label,
family; empty focus -> match_pairs finds no pairs -> pair_consistency is
None), so src.harness.evaluate and metrics.summarize work unchanged.

Why these two (design Q0/Q5; s5.4 T14b): ToxicChat = 10,165 real LMSYS user
queries — the production-traffic proxy (refusal rate on real, mostly-benign
traffic is the metric Anthropic grades constitutional classifiers on).
WildGuardTest = ~5k human-annotated prompts incl. an adversarial slice — the
red-team proxy. With XSTest that triangulates boundary precision +
adversarial breadth + realism; a gain that holds on all three is boundary
learning, not benchmark memorization.

Access:
  pip install datasets
  WildGuardTest (allenai/wildguardmix) is gated — accept the AI2 ImpACT
  license on HF and export HF_TOKEN before loading.

Label policy: ToxicChat is scored with its own human labels (>=3/4 annotator
majority) and we keep only human_annotation rows. Do NOT relabel it with the
judge cascade — RSafe trained on ToxicChat, so its votes are contaminated
here. The student never trained on either set, so both are clean student
evals (run the reverse decon spot-check vs the training corpus once, T14b).
"""

from collections import Counter

# ---- pure normalizers (unit-tested offline in src/tests/test_ood.py) ----


def _norm_toxicchat(records):
    """ToxicChat records -> harness rows.

    Families: tc_benign / tc_toxic / tc_jailbreak (jailbreak flag wins).
    safe_acc over tc_benign is the production refusal-rate proxy.
    """
    rows = []
    for i, r in enumerate(records):
        if not r.get("human_annotation"):
            continue
        prompt = (r.get("user_input") or "").strip()
        if not prompt:
            continue
        toxic = int(r.get("toxicity") or 0) == 1
        jailbreak = int(r.get("jailbreaking") or 0) == 1
        label = "unsafe" if (toxic or jailbreak) else "safe"
        family = ("tc_jailbreak" if jailbreak
                  else "tc_toxic" if toxic else "tc_benign")
        rows.append({"id": f"toxicchat-{i}", "prompt": prompt, "label": label,
                     "family": family, "type": family, "focus": "", "note": ""})
    if not rows:
        raise ValueError("no usable ToxicChat rows (human_annotation filter)")
    return rows


def _norm_wildguard(records):
    """WildGuardTest records -> harness rows (prompt-harm task only).

    Families: wg_adversarial / wg_vanilla, per the dataset's adversarial flag.
    """
    rows = []
    for i, r in enumerate(records):
        prompt = (r.get("prompt") or "").strip()
        harm = (r.get("prompt_harm_label") or "").strip().lower()
        if not prompt or harm not in ("harmful", "unharmful"):
            continue
        label = "unsafe" if harm == "harmful" else "safe"
        family = "wg_adversarial" if r.get("adversarial") else "wg_vanilla"
        rows.append({"id": f"wildguard-{i}", "prompt": prompt, "label": label,
                     "family": family, "type": family, "focus": "", "note": ""})
    if not rows:
        raise ValueError("no usable WildGuardTest rows (prompt_harm_label)")
    return rows


# ---- loaders (network; need `pip install datasets`) ----


def load_toxicchat(split="test"):
    from datasets import load_dataset
    ds = load_dataset("lmsys/toxic-chat", "toxicchat0124", split=split)
    return _norm_toxicchat(ds)


def load_wildguardtest(split="test"):
    from datasets import load_dataset  # gated: HF_TOKEN + accepted license
    ds = load_dataset("allenai/wildguardmix", "wildguardtest", split=split)
    return _norm_wildguard(ds)


def main():
    """Smoke check: verify access + print sizes/label/family counts."""
    for name, fn in (("toxicchat", load_toxicchat),
                     ("wildguardtest", load_wildguardtest)):
        try:
            rows = fn()
            labs = Counter(r["label"] for r in rows)
            fams = Counter(r["family"] for r in rows)
            print(f"{name}: {len(rows)} rows | {dict(labs)} | {dict(fams)}")
        except Exception as e:  # noqa: BLE001 - smoke check reports, not raises
            print(f"{name}: FAILED - {e}")


if __name__ == "__main__":
    main()
