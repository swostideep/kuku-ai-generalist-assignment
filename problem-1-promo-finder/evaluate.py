"""Reference-free quality checks for a ranked promo list, recomputed from the screenplay.

Works on both the v1 (codex_promo_finder) and v2 output schemas, so the two can be
compared on the same yardstick. It does NOT trust the tool's own hook/cliffhanger
fields: every check re-reads the script at the promo's timestamps.

    python evaluate.py --show <folder> --promos outputs/ranked_promos.json [--label v2] [--top 20]

Caveat: the 'opening dependency' and 'soft ending' checks reuse v2's lexicons, so they
are independent of v1 but not fully independent of v2. Boundary, duration, overlap,
speech-timing and rationale checks are rule-free facts.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

from promo_finder import signals as sig
from promo_finder.candidates import EpisodeIndex
from promo_finder.parser import load_show

EPS = 0.05


def normalise(p: Dict[str, Any]) -> Dict[str, Any]:
    seg = p["segments"][0]
    start = seg.get("start_seconds", seg.get("start"))
    end = seg.get("end_seconds", seg.get("end"))
    return {"id": p.get("promo_id") or p.get("candidate_id"), "episode": p["episode"], "start": float(start),
            "end": float(end), "why": p.get("why_it_works", ""), "segments": len(p["segments"])}


def evaluate(show: Path, promos: List[Dict[str, Any]]) -> Dict[str, Any]:
    episodes = {e.number: EpisodeIndex(e) for e in load_show(show)}
    rows = []
    for raw in promos:
        p = normalise(raw)
        idx = episodes[p["episode"]]
        s, t = p["start"], p["end"]
        lines = [d for d in idx.dialogue if s - EPS <= d.start < t - EPS]
        first, last = (lines[0] if lines else None), (lines[-1] if lines else None)
        rows.append({
            "id": p["id"], "episode": p["episode"],
            "duration_ok": 20 - EPS <= t - s <= 60 + EPS,
            "opens_mid_line": not idx.is_clean_cut(s),
            "ends_mid_line": not idx.is_clean_cut(t),
            "speech_within_3s": first is not None and first.start - s <= 3.0,
            "opening_dependent": bool(first and sig.opening_dependency(first.text)),
            "ends_soft": bool(last and sig.SOFT_LINES.match(last.text.strip())),
            "ends_on_question_or_threat": bool(last and (last.text.rstrip().endswith("?") or sig.content_cues(last.text)
                                                         or last.text.rstrip().endswith(("—", "--")))),
            "start": s, "end": t, "why": p["why"],
        })
    n = len(rows) or 1

    def pct(key: str) -> float:
        return round(100.0 * sum(1 for r in rows if r[key]) / n, 1)

    overl = 0
    heavy = 0
    for i, a in enumerate(rows):
        for b in rows[i + 1:]:
            if a["episode"] != b["episode"]:
                continue
            inter = max(0.0, min(a["end"], b["end"]) - max(a["start"], b["start"]))
            ratio = inter / max(1.0, min(a["end"] - a["start"], b["end"] - b["start"]))
            overl += ratio > 0.3
            heavy += ratio > 0.6
    top10_eps = len({r["episode"] for r in rows[:10]})
    return {
        "promos": len(rows),
        "episodes_covered": len({r["episode"] for r in rows}),
        "duration_ok_%": pct("duration_ok"),
        "opens_mid_line_%": pct("opens_mid_line"),
        "ends_mid_line_%": pct("ends_mid_line"),
        "speech_within_3s_%": pct("speech_within_3s"),
        "opening_needs_unseen_context_%": pct("opening_dependent"),
        "ends_on_soft_line_%": pct("ends_soft"),
        "ends_on_question_threat_or_interruption_%": pct("ends_on_question_or_threat"),
        "same_episode_pairs_overlapping_>30%": overl,
        "same_episode_pairs_overlapping_>60%": heavy,
        "distinct_rationales_%": round(100.0 * len({r["why"] for r in rows}) / n, 1),
        "distinct_episodes_in_top10": top10_eps,
        "failing_ids": {k: [r["id"] for r in rows if r[k]] for k in ("opens_mid_line", "ends_mid_line", "opening_dependent", "ends_soft")},
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--show", type=Path, required=True)
    ap.add_argument("--promos", type=Path, action="append", required=True, help="ranked_promos.json (repeatable)")
    ap.add_argument("--label", action="append", help="label per --promos")
    ap.add_argument("--top", type=int, default=0, help="only evaluate the top N ranks (0 = all)")
    ap.add_argument("--json-out", type=Path)
    a = ap.parse_args(argv)
    labels = a.label or [str(p) for p in a.promos]
    results = {}
    for label, path in zip(labels, a.promos):
        promos = json.loads(path.read_text(encoding="utf-8"))["promos"]
        promos = sorted(promos, key=lambda p: p.get("rank", 0))
        if a.top:
            promos = promos[: a.top]
        results[label] = evaluate(a.show, promos)
    keys = [k for k in next(iter(results.values())) if k != "failing_ids"]
    width = max(len(k) for k in keys)
    print(f"{'metric':<{width}}  " + "  ".join(f"{l:>10}" for l in labels))
    for k in keys:
        print(f"{k:<{width}}  " + "  ".join(f"{results[l][k]!s:>10}" for l in labels))
    if a.json_out:
        a.json_out.write_text(json.dumps(results, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
