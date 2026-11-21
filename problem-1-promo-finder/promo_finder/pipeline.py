"""End-to-end run: parse -> generate -> gate -> (optional model review) -> select -> export."""

from __future__ import annotations

import time
from collections import Counter
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from . import judge as jd
from .candidates import Settings, apply_gates, calibrate_gates, generate_candidates, show_context, to_record
from .parser import load_show
from .report import write_csv, write_html, write_json, write_summary
from .select import drop_cross_episode_duplicates, pick_per_episode, posting_order

ENGINE_VERSION = "2.1"


def run(show: Path, output: Path, per_episode: int = 2, first_wave: int = 10, max_overlap: float = 0.3,
        pool_size: int = 12, settings: Optional[Settings] = None,
        model_complete: Optional[Callable[[str, str], str]] = None, model_name: str = "",
        model_finalists: int = 6, log: Callable[[str], None] = print, premise_slots: int = 2) -> Dict[str, Any]:
    t0 = time.time()
    cfg = settings or Settings()
    episodes = load_show(show)
    ctx = show_context(episodes)
    log(f"Parsed {len(episodes)} episode(s) from {show}; lead characters detected: {', '.join(ctx.lead_speakers) or 'none'}")

    totals: Counter = Counter()
    picks_all: List[Dict[str, Any]] = []
    pool_records: List[Dict[str, Any]] = []
    no_promo: List[int] = []
    model_errors: List[Dict[str, Any]] = []
    model_problems: List[str] = []
    model_applied = 0
    by_number = {e.number: e for e in episodes}

    generated = []
    for ep in episodes:
        cands, stats = generate_candidates(ep, ctx, cfg)
        totals.update(stats)
        generated.append((ep, cands, stats))
    gates = calibrate_gates([c for _, cs, _ in generated for c in cs], cfg)
    if gates["hook"] < cfg.min_hook or gates["cliffhanger"] < cfg.min_cliff:
        log(f"Gates calibrated to this show: hook {gates['hook']:.0f} (default {cfg.min_hook:.0f}), "
            f"cliffhanger {gates['cliffhanger']:.0f} (default {cfg.min_cliff:.0f})")
    totals["eligible"] = 0
    for ep, cands, stats in generated:
        for c in cands:
            apply_gates(c, gates, cfg)
        stats["eligible"] = sum(1 for c in cands if not c["rejected"])
        totals["eligible"] += stats["eligible"]
        if model_complete is not None:
            _, finalists = pick_per_episode([c for c in cands if not c["rejected"]], model_finalists, max_overlap, model_finalists)
            result = jd.review_episode(model_complete, model_name, ep.number, ctx.premise, ep.logline, finalists)
            model_applied += result["applied"]
            model_problems += [f"E{ep.number:02d} {p}" for p in result["problems"]]
            if result["error"]:
                model_errors.append({"episode": ep.number, "error": result["error"]})
            reviewed = [c for c in finalists if "llm_review" in c]
            # Compare like with like inside an episode: if the model reviewed any finalist,
            # only reviewed finalists compete for that episode's picks.
            pool_for_pick = reviewed or cands
        else:
            pool_for_pick = cands
        picks, pool = pick_per_episode(pool_for_pick, per_episode, max_overlap, pool_size)
        if not picks:
            no_promo.append(ep.number)
        picks_all.extend(picks)
        pool_records.extend(to_record(c, ep) for c in pool)
        log(f"  E{ep.number:02d}: {stats.get('windows', 0):5d} legal windows, {stats.get('eligible', 0):4d} pass gates -> "
            f"{len(picks)} pick(s)" + ("" if picks else "  [no window passed the quality gates]"))

    before = len(picks_all)
    picks_all = drop_cross_episode_duplicates(picks_all)
    premise_last = max(3, round(0.1 * len(episodes)))
    ranked = posting_order(picks_all, first_wave, premise_last_episode=premise_last, premise_slots=premise_slots)
    promos = []
    for c in ranked:
        rec = to_record(c, by_number[c["episode"]])
        rec["rank"], rec["post_wave"] = c["rank"], c["post_wave"]
        rec["premise_slot"] = bool(c.get("premise_slot"))
        promos.append(rec)

    kinds = Counter(b.kind for e in episodes for b in e.blocks)
    warnings = [{"episode": e.number, "file": e.file, "warning": w} for e in episodes for w in e.warnings]
    status = "disabled (rules only, fully offline)"
    if model_complete is not None:
        status = f"{model_name}: {model_applied} finalist reviews accepted, {len(model_errors)} episode call(s) failed"
    stats = {
        "show": Path(show).name, "engine_version": ENGINE_VERSION, "episode_count": len(episodes),
        "block_count": sum(len(e.blocks) for e in episodes), "block_kinds": dict(kinds),
        "total_script_minutes": round(sum(e.duration for e in episodes) / 60, 1),
        "parser_warning_count": len(warnings), "windows_scored": totals.get("windows", 0),
        "cuts_inside_lines_avoided": totals.get("start_inside_line", 0) + totals.get("end_inside_line", 0),
        "eligible_windows": totals.get("eligible", 0), "episodes_without_promo": no_promo,
        "cross_episode_duplicates": before - len(picks_all), "selected_count": len(promos),
        "per_episode": per_episode, "first_wave": first_wave, "max_overlap": max_overlap,
        "lead_speakers": ctx.lead_speakers, "gates_default": {"hook": cfg.min_hook, "cliffhanger": cfg.min_cliff,
                                                               "standalone": cfg.min_standalone},
        "gates_applied": gates, "premise_episodes": f"1-{premise_last}", "premise_slots": premise_slots,
        "direction_coverage": round(sum(1 for e in episodes for b in e.blocks if b.kind == "dialogue" and b.emotion)
                                    / max(1, sum(1 for e in episodes for b in e.blocks if b.kind == "dialogue")), 3),
        "weights": cfg.weights, "model_status": status, "model_errors": model_errors,
        "model_validation_rejects": model_problems[:200], "runtime_seconds": round(time.time() - t0, 1),
    }

    output.mkdir(parents=True, exist_ok=True)
    write_json(output / "ranked_promos.json", {"description": "Ranked promo picks. Timestamps are copied from "
               "screenplay blocks; every pick carries its script evidence.", "run": stats, "promos": promos})
    write_json(output / "candidate_pool.json", {"description": "Top distinct windows per episode by score, "
               "including ones rejected by the quality gates (see rejected_reasons).", "run": stats,
               "candidates": pool_records})
    write_json(output / "parse_report.json", {"warnings": warnings})
    write_csv(output / "ranked_promos.csv", promos)
    write_html(output / "review.html", promos, stats)
    write_summary(output / "run_summary.md", stats, promos)
    log(f"\nWrote {len(promos)} ranked promos ({len(no_promo)} episode(s) without a qualifying promo) to {output}")
    return {"stats": stats, "promos": promos}
