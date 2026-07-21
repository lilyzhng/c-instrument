"""One command evaluates any model or checkpoint on XSTest (T3).

Baseline:  python -m src.harness.evaluate --model wildguard \
               --base-url http://localhost:8000
Probe:     add --n 8 --temperature 0.7
Checkpoint hook: point --served-model at the checkpoint vLLM is serving.

Serve first on the GPU node, e.g.:
  vllm serve allenai/wildguard --port 8000
"""

import argparse
import datetime
import json
import pathlib
import subprocess

from .adapters import get_adapter
from .client import VLLMClient
from .metrics import pass_rate, route, summarize
from .xstest import load_xstest


def _git_rev():
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5,
        ).stdout.strip() or None
    except Exception:  # noqa: BLE001 - provenance is best-effort
        return None


def _load_rows(args):
    if args.dataset == "toxicchat":
        from .ood import load_toxicchat
        return load_toxicchat()
    if args.dataset == "wildguardtest":
        from .ood import load_wildguardtest
        return load_wildguardtest()
    return load_xstest(args.data)


def run(args):
    adapter = get_adapter(args.model)
    served = args.served_model or adapter.hf_id
    rows = _load_rows(args)
    if args.limit:
        rows = rows[: args.limit]

    client = VLLMClient(args.base_url, served)
    builts = [adapter.build(r["prompt"]) for r in rows]
    texts = client.generate_batch(
        adapter.endpoint, builts, args.n, args.temperature,
        adapter.max_tokens, workers=args.workers,
    )

    records = []
    for row, outs in zip(rows, texts):
        labels = [adapter.parse(t)["label"] for t in outs]
        records.append({
            "row": row,
            "labels": labels,
            "pass_rate": pass_rate(labels, row["label"]),
            "route": route(labels, row["label"]),
            "raw": outs if args.save_raw else None,
        })

    result = {
        "config": {
            "model": args.model, "served_model": served,
            "dataset": args.dataset, "data": args.data,
            "n": args.n, "temperature": args.temperature,
            "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
            "harness_commit": _git_rev(),
        },
        "metrics": summarize(records),
        "prompts": [
            {k: v for k, v in rec.items() if k != "row"}
            | {"id": rec["row"]["id"], "family": rec["row"]["family"],
               "gold": rec["row"]["label"]}
            for rec in records
        ],
    }

    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    out = pathlib.Path(
        args.out
        or f"results/{stamp}_{args.model}_{args.dataset}"
           f"_n{args.n}_t{args.temperature}.json"
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2))
    print(json.dumps(result["metrics"], indent=2))
    print(f"\nwrote {out}")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--model", required=True,
                   choices=["wildguard", "nemotron-safety", "nemotron-reasoning"])
    p.add_argument("--base-url", default="http://localhost:8000")
    p.add_argument("--served-model",
                   help="model name vLLM serves under (default: adapter HF id)")
    p.add_argument("--dataset", default="xstest",
                   choices=["xstest", "toxicchat", "wildguardtest"],
                   help="eval set; OOD battery rationale in src/harness/ood.py")
    p.add_argument("--data", default="data/xstest_prompts.csv",
                   help="xstest CSV path (ignored for OOD datasets)")
    p.add_argument("--n", type=int, default=1, help="rollouts per prompt")
    p.add_argument("--temperature", type=float, default=0.0)
    p.add_argument("--limit", type=int, help="first N prompts only (smoke test)")
    p.add_argument("--workers", type=int, default=16)
    p.add_argument("--out", help="results JSON path")
    p.add_argument("--save-raw", action="store_true",
                   help="keep raw completions in the JSON")
    run(p.parse_args())


if __name__ == "__main__":
    main()
