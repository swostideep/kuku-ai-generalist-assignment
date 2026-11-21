"""Choose a diverse shortlist and a posting order."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple


def overlap_ratio(a: Dict[str, Any], b: Dict[str, Any]) -> float:
    if a["episode"] != b["episode"]:
        return 0.0
    inter = max(0.0, min(a["end"], b["end"]) - max(a["start"], b["start"]))
    return inter / max(1.0, min(a["end"] - a["start"], b["end"] - b["start"]))


def _lines(c: Dict[str, Any]) -> set:
    return {b.text.lower() for b in c["beats"] if b.kind == "dialogue" and len(b.text) > 12}


def text_similarity(a: Dict[str, Any], b: Dict[str, Any]) -> float:
    la, lb = _lines(a), _lines(b)
    if not la or not lb:
        return 0.0
    return len(la & lb) / min(len(la), len(lb))


def score_key(c: Dict[str, Any]) -> Tuple[float, float, float]:
    return (c.get("final_score", c["heuristic_score"]), c["scores"]["hook"], c["scores"]["cliffhanger"])


def pick_per_episode(candidates: List[Dict[str, Any]], per_episode: int, max_overlap: float,
                     pool_size: int) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Return (picks, pool). Pool = top distinct windows incl. rejected ones, for audit and model review."""
    ordered = sorted(candidates, key=score_key, reverse=True)
    eligible = [c for c in ordered if not c["rejected"]]
    picks: List[Dict[str, Any]] = []
    for c in eligible:
        if all(overlap_ratio(c, p) < max_overlap for p in picks):
            picks.append(c)
        if len(picks) >= per_episode:
            break
    pool: List[Dict[str, Any]] = []
    for c in ordered:
        if all(overlap_ratio(c, p) < max_overlap for p in pool):
            pool.append(c)
        if len(pool) >= pool_size:
            break
    return picks, pool


def drop_cross_episode_duplicates(picks: List[Dict[str, Any]], threshold: float = 0.5) -> List[Dict[str, Any]]:
    """Recap openings repeat the previous episode's lines; keep only the better copy."""
    kept: List[Dict[str, Any]] = []
    for c in sorted(picks, key=score_key, reverse=True):
        dup = next((k for k in kept if k["episode"] != c["episode"] and text_similarity(c, k) >= threshold), None)
        if dup is None:
            kept.append(c)
        else:
            c.setdefault("dropped_as_duplicate_of", dup["candidate_id"])
    return kept


def posting_order(picks: List[Dict[str, Any]], first_wave: int = 10, premise_last_episode: int = 0,
                  premise_slots: int = 0) -> List[Dict[str, Any]]:
    """Rank by score, but the first wave uses at most one promo per episode so the
    first posts test different story hooks instead of two cuts of one scene.

    premise_slots: a promo sends a new viewer to episode 1, so the first wave is guaranteed to contain the best
    passing promos from the opening episodes (<= premise_last_episode), one per episode. They are then
    ordered with the rest by score. (Added because the v2 ranking put episodes 2-5 at ranks 56-80.)"""
    ordered = sorted(picks, key=score_key, reverse=True)
    wave, rest, used = [], [], set()
    for c in ordered:
        if len(wave) < premise_slots and c["episode"] <= premise_last_episode and c["episode"] not in used:
            wave.append(c)
            used.add(c["episode"])
            c["premise_slot"] = True
    for c in ordered:
        if any(c is w for w in wave):
            continue
        if len(wave) < first_wave and c["episode"] not in used:
            wave.append(c)
            used.add(c["episode"])
        else:
            rest.append(c)
    wave.sort(key=score_key, reverse=True)
    ranked = wave + rest
    for i, c in enumerate(ranked, 1):
        c["rank"] = i
        c["post_wave"] = "first wave" if i <= len(wave) else "backlog"
    return ranked
