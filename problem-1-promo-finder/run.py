"""Kuku Promo Finder v2: find and rank 20-60 s promo clips in timestamped microdrama screenplays.

Examples
  python run.py --show "path/to/show_folder"                      # rules only, offline
  python run.py --show "path/to/show_folder" --llm-base-url http://localhost:11434/v1 --llm-model llama3.1
  python run.py --show "path/to/episode-007.txt" --output out_ep7  # a single episode file also works
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from promo_finder.candidates import Settings
from promo_finder.judge import OpenAICompatibleClient
from promo_finder.pipeline import run

HERE = Path(__file__).resolve().parent


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--show", type=Path, required=True, help="Folder of episode .txt files, or one .txt file")
    p.add_argument("--output", type=Path, default=HERE / "outputs", help="Output folder (default: ./outputs)")
    p.add_argument("--per-episode", type=int, default=2, help="Max promos kept per episode (default 2)")
    p.add_argument("--first-wave", type=int, default=10, help="Top N ranks limited to one promo per episode (default 10)")
    p.add_argument("--premise-slots", type=int, default=2,
                   help="First-wave slots reserved for the best promos from the opening episodes (default 2; 0 = off)")
    p.add_argument("--min-hook", type=float, default=45, help="Quality gate: minimum hook score (default 45)")
    p.add_argument("--min-cliff", type=float, default=45, help="Quality gate: minimum cliffhanger score (default 45)")
    p.add_argument("--min-standalone", type=float, default=40, help="Quality gate: minimum standalone score (default 40)")
    p.add_argument("--llm-base-url", help="OpenAI-compatible base URL, e.g. http://localhost:11434/v1 (Ollama)")
    p.add_argument("--llm-model", help="Model name for --llm-base-url")
    p.add_argument("--llm-api-key-env", default="LLM_API_KEY", help="Env var holding the API key (default LLM_API_KEY)")
    p.add_argument("--llm-finalists", type=int, default=6, help="Finalists per episode sent to the model (default 6)")
    p.add_argument("--llm-timeout", type=int, default=90)
    p.add_argument("--no-cache", action="store_true", help="Do not reuse cached model replies")
    a = p.parse_args(argv)

    if min(a.per_episode, a.first_wave, a.llm_finalists) < 1:
        print("error: --per-episode, --first-wave and --llm-finalists must be >= 1", file=sys.stderr)
        return 2
    if bool(a.llm_base_url) != bool(a.llm_model):
        print("error: pass both --llm-base-url and --llm-model, or neither", file=sys.stderr)
        return 2

    complete, name = None, ""
    if a.llm_base_url:
        client = OpenAICompatibleClient(a.llm_base_url, a.llm_model, os.environ.get(a.llm_api_key_env, ""),
                                        a.llm_timeout, retries=1,
                                        cache_dir=None if a.no_cache else a.output / ".model_cache")
        complete, name = client.complete, a.llm_model
        print(f"Model review enabled: {a.llm_model} at {client.url}. Script excerpts of finalists will be sent there.")

    settings = Settings(min_hook=a.min_hook, min_cliff=a.min_cliff, min_standalone=a.min_standalone)
    try:
        run(a.show, a.output, per_episode=a.per_episode, first_wave=a.first_wave, settings=settings,
            premise_slots=max(0, a.premise_slots),
            model_complete=complete, model_name=name, model_finalists=a.llm_finalists)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
