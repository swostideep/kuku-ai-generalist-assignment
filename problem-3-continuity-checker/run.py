"""Script continuity checker for AI-generated microdramas.

  python3 run.py --show "<folder of episode .txt files>" [--output outputs]
  python3 run.py --show <folder> --llm-base-url http://localhost:11434/v1 --llm-model llama3.1   # optional model review
Exit code 0 = no errors found, 1 = errors found (usable as a gate in a pipeline), 2 = bad input.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

from continuity.checker import load, run_checks
from continuity.llm import OpenAICompatible
from continuity.report import write_all
from continuity.review import review


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--show", type=Path, required=True)
    p.add_argument("--output", type=Path, default=Path(__file__).resolve().parent / "outputs")
    p.add_argument("--llm-base-url")
    p.add_argument("--llm-model")
    a = p.parse_args(argv)
    if bool(a.llm_base_url) != bool(a.llm_model):
        print("error: pass both --llm-base-url and --llm-model, or neither", file=sys.stderr)
        return 2
    t0 = time.time()
    try:
        scripts = load(a.show)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    findings = run_checks(scripts)
    model = "disabled (rules only, offline)"
    if a.llm_base_url:
        stats = review(findings, OpenAICompatible(a.llm_base_url, a.llm_model, os.environ.get("LLM_API_KEY", "")), a.llm_model)
        model = f"{a.llm_model}: {stats}"
    meta = {"show": a.show.name, "episodes": len(scripts), "blocks": sum(len(s.episode.blocks) for s in scripts),
            "model": model, "runtime_seconds": round(time.time() - t0, 2),
            "parser_warnings": [w for s in scripts for w in s.episode.warnings]}
    write_all(a.output, findings, meta)
    errors = sum(1 for f in findings if f.severity == "error")
    print(f"{len(scripts)} episodes, {len(findings)} findings ({errors} errors) -> {a.output}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
