#!/usr/bin/env bash
# Post-eval triage trigger (the notification loop). Run after every eval:
#   eval -> lineage_diagnose (verdict) -> propose_experiment (spec).
# If a PRUNE CANDIDATE surfaces, it prints a runnable experiment for the agent
# to execute. This is how a frontend/human flag becomes an automated action.
set -u; cd "$(dirname "$0")/../.."
PYTHONPATH=. python3 -m src.datagen.lineage_diagnose >/dev/null 2>&1
PYTHONPATH=. python3 -m src.datagen.propose_experiment
n=$(python3 -c "import json;print(len(json.load(open('results/proposed_experiments.json'))))" 2>/dev/null || echo 0)
[ "$n" -gt 0 ] && echo ">>> $n experiment(s) PROPOSED - agent should run the ablation (results/proposed_experiments.json)"
