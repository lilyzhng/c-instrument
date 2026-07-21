# C-Guard: A Constitution-Grid Instrument for Data-Efficient RL Alignment

Code and constitution for *"A Constitution-Grid Instrument for Data-Efficient RL Alignment (C-Guard)"* (under review, COLM 2026 Efficient Reasoning Workshop).

Guards run **inline on every LLM turn**, so the job is high-volume, short-prompt, and latency-bound. This project asks: given a fixed 4B base model and a read-only XSTest eval, can **targeted synthetic data + GRPO** shrink over-refusal without opening disguise holes?

## Method in one paragraph

We write a constitution, one policy per harm topic, and cross its topics with the ways a user can ask. C-LIM, a per-cell learnability score computed on unseen rows, reads the board and routes each cell to a move: prune a mastered cell, densify a still-learning one, amend a cell whose rule is wrong, expand the board with a new topic. Every generation feeds RL training with GRPO, and every gain is measured on the trained model.

## Repository layout

| Path | Contents |
| :--- | :--- |
| `src/constitutions/` | The constitution: one charter per harm topic, plus interaction-style mechanisms |
| `src/datagen/` | Twin-pair generator, judge ensemble, label gates, decontamination |
| `src/harness/` | Evaluation harness (XSTest scoreboard, WildGuardTest, ToxicChat) |
| `src/train/` | GRPO training (verl) and launch scripts |
| `src/tools/` | Figure builders and analysis tools |
| `data/` | XSTest eval assets |

## License

Released for research use.
