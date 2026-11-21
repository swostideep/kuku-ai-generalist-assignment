#!/usr/bin/env bash
# Regenerates every raw output in ./outputs from the input pack. Usage: ./reproduce.sh "<show folder>" [v1 ranked_promos.json]
set -euo pipefail
SHOW="${1:?usage: ./reproduce.sh <show folder> [v1_ranked_promos.json]}"
V1="${2:-}"
cd "$(dirname "$0")"
rm -rf outputs && mkdir -p outputs/logs
python3 run.py --show "$SHOW" --output outputs | tee outputs/logs/run_log.txt
PYTHONHASHSEED=12345 python3 run.py --show "$SHOW" --output outputs/logs/_rerun > /dev/null
python3 - outputs/ranked_promos.json outputs/logs/_rerun/ranked_promos.json <<'PY' | tee outputs/logs/determinism_check.txt
import json, sys
a, b = (json.load(open(p))["promos"] for p in sys.argv[1:3])
print("Second full run in a separate process (PYTHONHASHSEED=12345): promos byte-identical =",
      json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True))
PY
rm -rf outputs/logs/_rerun
python3 -m unittest discover -s tests -v > outputs/logs/test_results.txt 2>&1 || true
tail -3 outputs/logs/test_results.txt
if [ -n "$V1" ]; then
  { python3 evaluate.py --show "$SHOW" --promos "$V1" --label v1_all --promos outputs/ranked_promos.json --label v2_all \
        --json-out outputs/logs/evaluation_all.json
    echo
    python3 evaluate.py --show "$SHOW" --promos "$V1" --label v1_top20 --promos outputs/ranked_promos.json --label v2_top20 \
        --top 20 --json-out outputs/logs/evaluation_top20.json; } | tee outputs/logs/evaluation.txt
fi
