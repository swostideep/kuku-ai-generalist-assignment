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
# Brittleness check: the same show with every acting direction "(Angry, ...)" removed from speaker labels.
TMP="$(mktemp -d)"
python3 - "$SHOW" "$TMP/show" <<'PY'
import re, sys
from pathlib import Path
src, dst = Path(sys.argv[1]), Path(sys.argv[2]); dst.mkdir(parents=True)
for p in sorted(src.glob("*.txt")):
    t = p.read_text(encoding="utf-8")
    (dst / p.name).write_text(re.sub(r"^(\*\*[^*(]+?)\s*\([^*]*\):\*\*", r"\1:**", t, flags=re.M), encoding="utf-8")
PY
python3 run.py --show "$TMP/show" --output "$TMP/out" > /dev/null
python3 - "$TMP/out/ranked_promos.json" <<'PY' | tee outputs/logs/no_directions_check.txt
import json, sys
r = json.load(open(sys.argv[1]))["run"]
print("Brittleness check: the same show with every acting direction removed from speaker labels.")
print(f"current code: promos={r['selected_count']} eligible_windows={r['eligible_windows']} "
      f"episodes_without_promo={len(r['episodes_without_promo'])} gates_applied={r['gates_applied']}")
print("reference (recorded in the 2026-11-21 audit, v2.0 code in _original_snapshot/): promos=41, "
      "eligible_windows=210, episodes_without_promo=23, gates fixed at 45/45")
PY
rm -rf "$TMP"
python3 -m unittest discover -s tests -v > outputs/logs/test_results.txt 2>&1 || true
tail -3 outputs/logs/test_results.txt
if [ -n "$V1" ]; then
  { python3 evaluate.py --show "$SHOW" --promos "$V1" --label v1_all --promos outputs/ranked_promos.json --label v2_all \
        --json-out outputs/logs/evaluation_all.json
    echo
    python3 evaluate.py --show "$SHOW" --promos "$V1" --label v1_top20 --promos outputs/ranked_promos.json --label v2_top20 \
        --top 20 --json-out outputs/logs/evaluation_top20.json; } | tee outputs/logs/evaluation.txt
fi
