# C-Instrument: Automating RL Data Generation and Hillclimbing with a Constitution-Grid Instrument

Code and constitution for *"C-Instrument: Automating RL Data Generation and Hillclimbing with a Constitution-Grid Instrument"*, published at the COLM 2026 Workshop on Efficient Reasoning.

[Paper (arXiv)](https://arxiv.org/abs/2608.00180) · [Blog](https://lilyzh.ng/writing/c-instrument/)

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
