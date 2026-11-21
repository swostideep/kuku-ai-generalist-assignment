"""Generate legal promo windows and score them.

Pipeline per episode:
  1. Legal cut points: never inside a spoken line, never between the two halves
     of a split sentence. Starts/ends snap to a camera-shot boundary when one is
     within `snap` seconds, so the editor gets a cut on a shot change.
  2. Every legal (start, end) pair of 20-60 s is scored on hook, cliffhanger,
     standalone clarity, tension arc and pacing.
  3. Hard gates, not a weighted sum, decide eligibility: a great ending can no
     longer rescue a weak opening (a defect found in v1).
"""

from __future__ import annotations

import bisect
import re
from string import capwords
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from . import signals as sig
from .parser import Block, Episode, format_time

EPS = 0.05


@dataclass
class Settings:
    min_len: float = 20.0
    max_len: float = 60.0
    hook_window: float = 3.0
    snap: float = 1.5
    min_hook: float = 45.0
    min_cliff: float = 45.0
    min_standalone: float = 40.0
    min_dialogue_lines: int = 3
    weights: Dict[str, float] = field(default_factory=lambda: {
        "hook": 0.30, "cliffhanger": 0.30, "standalone": 0.20, "tension_arc": 0.12, "pacing": 0.08})


@dataclass
class ShowContext:
    """Show-level facts computed once (no hard-coded character names)."""
    lead_speakers: List[str]
    premise: str


HONORIFICS = re.compile(r"^(?:LADY|LORD|SIR|THE|DUKE|DUCHESS|MR\.?|MRS\.?|MISS|MS\.?|DR\.?)\s+")


def canon(name: str) -> str:
    """'LADY MARA' and 'MARA' are the same person for lead detection."""
    previous = None
    while previous != name:
        previous, name = name, HONORIFICS.sub("", name.strip().upper())
    return name


def show_context(episodes: List[Episode]) -> ShowContext:
    counts = Counter(canon(b.speaker) for e in episodes for b in e.blocks if b.kind == "dialogue" and b.speaker)
    leads = [name for name, _ in counts.most_common(2)]
    premise = episodes[0].logline if episodes else ""
    return ShowContext(lead_speakers=leads, premise=premise)


class EpisodeIndex:
    def __init__(self, episode: Episode):
        self.episode = episode
        self.beats = [b for b in episode.blocks if b.kind != "camera" and b.text]
        self.beat_starts = [b.start for b in self.beats]
        self.dialogue = [b for b in self.beats if b.kind == "dialogue"]
        self.shots = sorted((b for b in episode.blocks if b.kind == "camera"), key=lambda b: b.start)
        # Spoken spans a cut may not fall inside (split sentences merged into one span).
        spans: List[Tuple[float, float]] = []
        for i, line in enumerate(self.dialogue):
            end = line.end
            j = i
            while self.dialogue[j].continues and j + 1 < len(self.dialogue):
                j += 1
                end = self.dialogue[j].end
            spans.append((line.start, end))
        self.spans = spans
        self.last_dialogue_id = self.dialogue[-1].id if self.dialogue else ""

    def is_clean_cut(self, t: float) -> bool:
        return not any(s + EPS < t < e - EPS for s, e in self.spans)

    def dialogue_starts_between(self, a: float, b: float) -> bool:
        return any(a - EPS < d.start < b - EPS for d in self.dialogue)

    def snap_start(self, t: float, snap: float) -> float:
        best = t
        for shot in self.shots:
            if shot.start <= t + EPS and t - shot.start <= snap and shot.start < best:
                if self.is_clean_cut(shot.start) and not self.dialogue_starts_between(shot.start, t):
                    best = shot.start
        return best

    def snap_end(self, t: float, snap: float, limit: float) -> float:
        best = t
        for shot in self.shots:
            if shot.start < t - EPS < shot.end and shot.end - t <= snap and shot.end <= limit:
                if self.is_clean_cut(shot.end) and not self.dialogue_starts_between(t + EPS, shot.end):
                    best = max(best, shot.end)
        return best

    def window(self, start: float, end: float) -> List[Block]:
        lo = bisect.bisect_left(self.beat_starts, start - EPS)
        hi = bisect.bisect_left(self.beat_starts, end - EPS)
        return [b for b in self.beats[lo:hi] if b.end <= end + 0.3]


def _quote(text: str, limit: int = 90) -> str:
    text = text.strip()
    return "“" + (text if len(text) <= limit else text[: limit - 1].rstrip() + "…") + "”"


def score_window(idx: EpisodeIndex, ctx: ShowContext, start: float, end: float, cfg: Settings) -> Optional[Dict[str, Any]]:
    beats = idx.window(start, end)
    lines = [b for b in beats if b.kind == "dialogue"]
    if not beats:
        return None
    duration = end - start

    # ---- Hook: strongest beat that starts inside the first 3 seconds.
    # A strong line at 2.5 s is worth less than the same line at 0 s: the viewer
    # has already heard whatever came first.
    opening = [b for b in beats if b.start < start + cfg.hook_window]
    hook_block, hook, hook_reasons = None, 0.0, []
    prev = next((d for d in reversed(idx.dialogue) if d.end <= start + EPS), None)
    for b in opening:
        s, r = sig.hook_strength(b)
        s -= 5.0 * max(0.0, b.start - start)
        if b.kind == "dialogue" and prev is not None and start - prev.end < 4.0 and sig.echoes(b.text, prev.text):
            s -= 22
            r = r + ["echoes a line cut off before the clip"]
        if hook_block is None or s > hook:
            hook_block, hook, hook_reasons = b, s, r

    # ---- Cliffhanger: what the viewer is left with at the cut.
    last_line = lines[-1] if lines and lines[-1].end > end - 6.0 else None
    tail_beats = [b for b in beats if b.kind != "dialogue" and b.end > end - 3.0]
    cliff_block, cliff, cliff_reasons = None, 0.0, []
    for b in ([last_line] if last_line else []) + tail_beats:
        s, r = sig.cliff_strength(b)
        if cliff_block is None or s > cliff:
            cliff_block, cliff, cliff_reasons = b, s, list(r)
    if cliff_block is not None:
        sting = [b for b in idx.episode.blocks if sig.is_writer_cliff_cue(b) and end - 3.0 < b.start < end + 2.0]
        if sting:
            cliff += 12
            cliff_reasons.append("script marks a sting/cliffhanger cue here")
        if last_line is not None and last_line.id == idx.last_dialogue_id:
            cliff += 10
            cliff_reasons.append("episode's own closing line")
        nxt = next((d for d in idx.dialogue if d.start >= end - EPS), None)
        if (last_line is not None and nxt is not None and nxt.speaker != last_line.speaker
                and nxt.start - end < 4.0 and ("?" in last_line.text or sig.content_cues(last_line.text))):
            cliff += 8
            cliff_reasons.append("cuts right before the reply")
        tensions = [sig.tension(b) for b in beats]
        quarter = tensions[int(len(tensions) * 0.75):] or tensions[-1:]
        if sum(quarter) / len(quarter) < 0.35:
            cliff -= 20
            cliff_reasons.append("tension already resolved before the cut")
    cliff = max(0.0, min(100.0, cliff))
    hook = max(0.0, hook)

    # ---- Standalone clarity for a cold viewer.
    standalone = 60.0
    clarity_notes: List[str] = []
    first_lines = [d for d in lines if d.start < start + 6.0][:2]
    penalty = 0.0
    for d in first_lines:
        for problem in sig.opening_dependency(d.text):
            penalty += 18
            clarity_notes.append(f"{problem}: {_quote(d.text, 50)}")
    standalone -= min(30.0, penalty)
    early_text = " ".join(d.text for d in lines if d.start < start + 12.0).lower()
    if any(re.search(r"(?<![a-z])" + w + r"(?![a-z])", early_text) for w in sig.RELATIONSHIP_WORDS) or \
            re.search(r"\b[A-Z][a-z]{2,}\b", " ".join(d.text[1:] for d in lines if d.start < start + 12.0)):
        standalone += 10
        clarity_notes.append("names who is involved early")
    speakers = {d.speaker for d in lines}
    if 2 <= len(speakers) <= 3:
        standalone += 8
    elif len(speakers) >= 5:
        standalone -= 12
        clarity_notes.append(f"{len(speakers)} speakers")
    scenes = {b.scene for b in beats if b.scene}
    if len(scenes) <= 1:
        standalone += 10
    else:
        standalone -= 15 * (len(scenes) - 1)
        clarity_notes.append(f"crosses {len(scenes)} scenes")
    if {canon(x) for x in speakers} & set(ctx.lead_speakers):
        standalone += 8
    else:
        clarity_notes.append("no lead character speaks")
    if len(lines) < 4:
        standalone -= 12
        clarity_notes.append("little dialogue")
    standalone = max(0.0, min(100.0, standalone))

    # ---- Tension arc: does it build (or stay high) rather than deflate?
    tensions = [sig.tension(b) for b in beats]
    half = max(1, len(tensions) // 2)
    first_half = sum(tensions[:half]) / half
    second_half = sum(tensions[half:]) / max(1, len(tensions) - half)
    mean_t = sum(tensions) / len(tensions)
    arc = 30 + 50 * mean_t + 60 * max(-0.4, min(0.4, second_half - first_half))
    conflict_lines = sum(1 for d in lines if sig.content_cues(d.text))
    arc += min(12, 4 * conflict_lines)
    arc = max(0.0, min(100.0, arc))

    # ---- Pacing: dialogue density and dead air.
    density = len(lines) / max(1.0, duration / 10.0)
    pacing = 45 + min(35.0, density * 9)
    cursor, max_gap = start, 0.0
    for b in beats:
        max_gap = max(max_gap, b.start - cursor)
        cursor = max(cursor, b.end)
    max_gap = max(max_gap, end - cursor)
    if max_gap > 4.0:
        pacing -= 15
    if 25.0 <= duration <= 50.0:
        pacing += 10
    pacing = max(0.0, min(100.0, pacing))

    scores = {"hook": round(hook, 1), "cliffhanger": round(cliff, 1), "standalone": round(standalone, 1),
              "tension_arc": round(arc, 1), "pacing": round(pacing, 1)}
    total = round(sum(cfg.weights[k] * scores[k] for k in cfg.weights), 1)

    rejected = []
    if hook < cfg.min_hook:
        rejected.append(f"hook {hook:.0f} < {cfg.min_hook:.0f}")
    if cliff < cfg.min_cliff:
        rejected.append(f"cliffhanger {cliff:.0f} < {cfg.min_cliff:.0f}")
    if standalone < cfg.min_standalone:
        rejected.append(f"standalone {standalone:.0f} < {cfg.min_standalone:.0f}")
    if len(lines) < cfg.min_dialogue_lines:
        rejected.append("fewer than 3 dialogue lines")

    return {
        "start": start, "end": end, "duration": round(duration, 2), "scores": scores, "heuristic_score": total,
        "hook_block": hook_block, "hook_reasons": hook_reasons, "cliff_block": cliff_block,
        "cliff_reasons": cliff_reasons, "clarity_notes": clarity_notes, "rejected": rejected,
        "beats": beats, "speakers": sorted(speakers), "scenes": sorted(scenes),
    }


READABLE = {"threat/danger": "danger", "accusation": "an accusation", "reveal": "a reveal",
            "physical action": "physical action", "loud sound event": "a loud sound", "pointed question": "a pointed question"}


def rationale(c: Dict[str, Any]) -> str:
    """One specific line built only from evidence in the clip."""
    hb, cb = c["hook_block"], c["cliff_block"]
    hook_what = [READABLE[r] for r in c["hook_reasons"] if r in READABLE]
    hook_tone = next((r.split("'")[1] for r in c["hook_reasons"] if r.startswith("delivered")), "")
    if hb.kind == "dialogue":
        opener = f"Opens on {capwords(hb.speaker.lower())}'s {hook_tone + ' ' if hook_tone else ''}line {_quote(hb.text, 60)}"
    else:
        opener = f"Opens on {READABLE.get(hook_what[0], hb.kind) if hook_what else hb.kind} {_quote(hb.text, 60)}"
    if hook_what and hb.kind == "dialogue":
        opener += f" ({', '.join(hook_what[:2])})"
    cliff_what = [READABLE.get(r, r) for r in c["cliff_reasons"] if not r.startswith("delivered")]
    closer = f"cuts on {_quote(cb.text, 70)}"
    if cliff_what:
        closer += " (" + ", ".join(cliff_what[:2]) + ")"
    return f"{opener}; {closer}."


def calibrate_gates(cands: List[Dict[str, Any]], cfg: Settings, quantile: float = 0.8) -> Dict[str, float]:
    """Per-show gates: min(absolute gate, this show's 80th percentile).

    The absolute gates were set on a script with rich performance directions. A show written without them
    scores lower across the board (measured: hook p80 54 -> 32), and fixed gates then rejected 23 of 50
    episodes. Using min(...) leaves a direction-rich show unchanged and lets a sparser one still surface
    its own top ~20% of windows. The applied gates are reported in the run summary.
    """
    def q(values: List[float]) -> float:
        values = sorted(values)
        return values[int(quantile * (len(values) - 1))] if values else 0.0
    return {"hook": min(cfg.min_hook, q([c["scores"]["hook"] for c in cands])),
            "cliffhanger": min(cfg.min_cliff, q([c["scores"]["cliffhanger"] for c in cands])),
            "standalone": cfg.min_standalone}


def apply_gates(c: Dict[str, Any], gates: Dict[str, float], cfg: Settings) -> None:
    s = c["scores"]
    c["rejected"] = []
    if s["hook"] < gates["hook"]:
        c["rejected"].append(f"hook {s['hook']:.0f} < {gates['hook']:.0f}")
    if s["cliffhanger"] < gates["cliffhanger"]:
        c["rejected"].append(f"cliffhanger {s['cliffhanger']:.0f} < {gates['cliffhanger']:.0f}")
    if s["standalone"] < gates["standalone"]:
        c["rejected"].append(f"standalone {s['standalone']:.0f} < {gates['standalone']:.0f}")
    if sum(1 for b in c["beats"] if b.kind == "dialogue") < cfg.min_dialogue_lines:
        c["rejected"].append("fewer than 3 dialogue lines")


def generate_candidates(episode: Episode, ctx: ShowContext, cfg: Settings) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    idx = EpisodeIndex(episode)
    stats = Counter()
    seen = set()
    out = []
    for start_beat in idx.beats:
        if not idx.is_clean_cut(start_beat.start):
            stats["start_inside_line"] += 1
            continue
        start = idx.snap_start(start_beat.start, cfg.snap)
        for end_beat in idx.beats:
            raw_end = end_beat.end
            if raw_end - start < cfg.min_len - EPS or raw_end - start > cfg.max_len + EPS:
                continue
            if not idx.is_clean_cut(raw_end):
                stats["end_inside_line"] += 1
                continue
            end = idx.snap_end(raw_end, cfg.snap, start + cfg.max_len)
            key = (round(start, 2), round(end, 2))
            if key in seen:
                continue
            seen.add(key)
            stats["windows"] += 1
            scored = score_window(idx, ctx, start, end, cfg)
            if scored is None or scored["hook_block"] is None or scored["cliff_block"] is None:
                stats["no_hook_or_cliff_beat"] += 1
                continue
            out.append(scored)
    for i, c in enumerate(sorted(out, key=lambda c: (c["start"], c["end"])), 1):
        c["candidate_id"] = f"E{episode.number:02d}-W{i:04d}"
        c["episode"] = episode.number
    stats["eligible"] = sum(1 for c in out if not c["rejected"])
    return out, dict(stats)


def to_record(c: Dict[str, Any], episode: Episode) -> Dict[str, Any]:
    """JSON-safe view of a candidate with block-level evidence."""
    def block_ref(b: Block) -> Dict[str, Any]:
        return {"block_id": b.id, "kind": b.kind, "speaker": b.speaker, "emotion": b.emotion,
                "time": format_time(b.start), "text": b.text}
    seg_beats = c["beats"]
    return {
        "promo_id": c["candidate_id"],
        "episode": episode.number,
        "episode_file": episode.file,
        "segments": [{
            "episode": episode.number, "start_seconds": round(c["start"], 2), "end_seconds": round(c["end"], 2),
            "start_time": format_time(c["start"]), "end_time": format_time(c["end"]),
            "first_block": seg_beats[0].id, "last_block": seg_beats[-1].id,
        }],
        "duration_seconds": c["duration"],
        "hook": block_ref(c["hook_block"]),
        "hook_reasons": c["hook_reasons"],
        "cliffhanger": block_ref(c["cliff_block"]),
        "cliffhanger_reasons": c["cliff_reasons"],
        "why_it_works": c.get("why") or rationale(c),
        "why_source": c.get("why_source", "rules"),
        "scores": c["scores"],
        "heuristic_score": c["heuristic_score"],
        "final_score": c.get("final_score", c["heuristic_score"]),
        "score_source": c.get("score_source", "heuristic"),
        "llm_review": c.get("llm_review"),
        "clarity_notes": c["clarity_notes"],
        "rejected_reasons": c["rejected"],
        "speakers": c["speakers"],
        "scenes": c["scenes"],
        "transcript": [block_ref(b) for b in seg_beats],
    }
