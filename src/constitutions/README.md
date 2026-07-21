# Constitutions (two-axis structure)

Per design §4.2.1: the constitution is organized by harm **topic** (coverage axis), and boundary **mechanism** is the within-topic twin recipe (not the taxonomy). Two layers:

- **`topics/`** — one mini-constitution per harm topic (the 11 chosen by ROI, [T7d](../../deliverables/s5.3_results.md)). Drives Pass-1 coverage generation. This is the primary layer.
- **`mechanisms/`** — the boundary mechanisms, in two families. Drives Pass-2 twin generation *within* each topic; reusable across topics.
  - *Over-refusal mechanisms* (homonym, figurative, safe-context, definition, public-vs-private, factual-vs-denialist): make a benign prompt look scary; the safe twin is the over-refusal fix.
  - *Under-refusal mechanism* ([disguise/evasion](mechanisms/disguise_evasion.md)): the inverse, make a harmful prompt look benign (roleplay/fiction/hypothetical/indirect); the disguised-unsafe twin is the under-refusal fix, paired with a benign-adversarial safe twin. Grounded in design Q7/Q8; applies to violence, cyber, weapons, fraud, drugs.

## Topic constitution fields (HaloGuard-adopted, §5.3.1)

Each topic file carries:
- **Tier** — Critical / High / Moderate / Sensitive (governs how wide the benign boundary is; from HaloGuard)
- **Figurative flag** — does this topic have idiomatic/benign uses of its scary words?
- **Boundary** — one paragraph: where safe ends and unsafe begins
- **Benign confusions** — the safe-side cases the guard over-refuses (our over-refusal fix; probe-weighted where XSTest maps)
- **Surface cues** — the shared trigger vocabulary (safe and unsafe both use these)
- **Mechanisms** — which twin recipes apply in this topic
- **XSTest map** — which XSTest family maps here (for eval reportability)

## The 11 topics (Tier A + B)

| Topic | Tier | XSTest map | Probe errors |
| :-- | :-- | :-- | :-- |
| violence | High | homonyms, figurative, safe_targets, safe_contexts | (spread) |
| cyber | High | homonyms (kill/inject/fork) | high |
| privacy | Sensitive | privacy | 17 |
| fraud | Moderate | (definitions) | high |
| regulated_advice | Moderate | (definitions) | high |
| hate_discrimination | Sensitive | discrimination | 11 |
| drugs | Moderate | (definitions) | medium |
| weapons | High | (safe_contexts) | low-medium |
| self_harm | Sensitive | — | (benign-heavy) |
| copyright | Moderate | — | low |
| general | — | off-topic benign baseline | — |

Tier C (CBRN, trafficking, property-crime) is block-side only; Tier D (CSAM, sexual, disinfo, politically-sensitive) is never generated. See [ROI ranking](../../research/20260718-haloguard-category-roi.md).
