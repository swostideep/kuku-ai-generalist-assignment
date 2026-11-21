"""Write machine- and editor-friendly outputs."""

from __future__ import annotations

import csv
import html
import json
from pathlib import Path
from typing import Any, Dict, List


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_csv(path: Path, promos: List[Dict[str, Any]]) -> None:
    cols = ["rank", "post_wave", "promo_id", "episode", "start_time", "end_time", "duration_seconds", "final_score",
            "score_source", "hook_score", "cliffhanger_score", "standalone_score", "hook", "cliffhanger",
            "why_it_works", "clarity_notes", "editor_verdict", "editor_notes"]
    with path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=cols)
        writer.writeheader()
        for p in promos:
            seg = p["segments"][0]
            writer.writerow({
                "rank": p["rank"], "post_wave": p["post_wave"], "promo_id": p["promo_id"], "episode": p["episode"],
                "start_time": seg["start_time"], "end_time": seg["end_time"], "duration_seconds": p["duration_seconds"],
                "final_score": p["final_score"], "score_source": p["score_source"],
                "hook_score": p["scores"]["hook"], "cliffhanger_score": p["scores"]["cliffhanger"],
                "standalone_score": p["scores"]["standalone"],
                "hook": f'{p["hook"]["speaker"] or p["hook"]["kind"].upper()}: {p["hook"]["text"]}',
                "cliffhanger": f'{p["cliffhanger"]["speaker"] or p["cliffhanger"]["kind"].upper()}: {p["cliffhanger"]["text"]}',
                "why_it_works": p["why_it_works"], "clarity_notes": "; ".join(p["clarity_notes"]),
                "editor_verdict": "", "editor_notes": "",
            })


def write_html(path: Path, promos: List[Dict[str, Any]], stats: Dict[str, Any]) -> None:
    """A single self-contained review page for the editor (local file; contains confidential script text)."""
    esc = html.escape
    cards = []
    for p in promos:
        seg = p["segments"][0]
        rows = []
        for b in p["transcript"]:
            cls = "hook" if b["block_id"] == p["hook"]["block_id"] else ("cliff" if b["block_id"] == p["cliffhanger"]["block_id"] else "")
            who = esc(b["speaker"] or b["kind"].upper())
            emo = f' <span class="emo">({esc(b["emotion"])})</span>' if b["emotion"] else ""
            rows.append(f'<tr class="{cls}"><td class="t">{esc(b["time"])}</td><td class="who">{who}{emo}</td>'
                        f'<td>{esc(b["text"])}</td></tr>')
        s = p["scores"]
        notes = "; ".join(p["clarity_notes"]) or "none"
        cards.append(f"""
<section class="card"><header><span class="rank">#{p['rank']}</span>
<b>Episode {p['episode']}</b> · {esc(seg['start_time'])} → {esc(seg['end_time'])} · {p['duration_seconds']:.1f}s
<span class="score">{p['final_score']}</span><span class="wave">{esc(p['post_wave'])}</span></header>
<p class="why">{esc(p['why_it_works'])}</p>
<p class="meta">hook {s['hook']} · cliffhanger {s['cliffhanger']} · standalone {s['standalone']} · arc {s['tension_arc']} · pacing {s['pacing']} · source {esc(p['score_source'])}<br>
clarity notes: {esc(notes)}</p>
<details><summary>Script excerpt ({len(p['transcript'])} beats; hook and cut highlighted)</summary>
<table>{''.join(rows)}</table></details></section>""")
    page = f"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Promo Review</title><style>
:root{{--bg:#fafaf7;--fg:#1d2330;--muted:#5d6675;--card:#fff;--line:#e4e4de;--hook:#fff4d6;--cliff:#e3f0ff;--accent:#0f6e7a}}
@media (prefers-color-scheme: dark){{:root{{--bg:#14171c;--fg:#e8eaee;--muted:#9aa3b2;--card:#1c2027;--line:#2c313a;--hook:#3a3218;--cliff:#18304a;--accent:#5cc3cf}}}}
body{{background:var(--bg);color:var(--fg);font:15px/1.45 system-ui,sans-serif;margin:0 auto;max-width:980px;padding:16px}}
h1{{font-size:22px;margin:8px 0}} .sub{{color:var(--muted);margin-bottom:16px}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 14px;margin:12px 0}}
header{{display:flex;gap:10px;align-items:baseline;flex-wrap:wrap}} .rank{{font-weight:700;color:var(--accent)}}
.score{{margin-left:auto;font-weight:700}} .wave{{font-size:12px;color:var(--muted)}}
.why{{margin:6px 0}} .meta{{color:var(--muted);font-size:13px;margin:4px 0}}
table{{border-collapse:collapse;width:100%;font-size:13px;margin-top:6px}} td{{border-top:1px solid var(--line);padding:3px 6px;vertical-align:top}}
.t{{white-space:nowrap;color:var(--muted)}} .who{{white-space:nowrap;font-weight:600}} .emo{{font-weight:400;color:var(--muted)}}
tr.hook{{background:var(--hook)}} tr.cliff{{background:var(--cliff)}}
@media (max-width:600px){{.who{{white-space:normal}}}}
</style></head><body><h1>Promo shortlist: {esc(stats['show'])}</h1>
<div class="sub">{stats['selected_count']} promos from {stats['episode_count']} episodes · scoring: {esc(stats['model_status'])}.
Yellow = hook line, blue = final beat before the cut. Scores rank candidates; they are not predictions of ad performance.</div>
{''.join(cards)}</body></html>"""
    path.write_text(page, encoding="utf-8")


def write_summary(path: Path, stats: Dict[str, Any], promos: List[Dict[str, Any]]) -> None:
    lines = [
        f"# Run summary: {stats['show']}", "",
        f"- Engine version: {stats['engine_version']}",
        f"- Episodes parsed: {stats['episode_count']} ({stats['total_script_minutes']} script minutes)",
        f"- Timed blocks: {stats['block_count']} (dialogue {stats['block_kinds'].get('dialogue', 0)}, "
        f"action {stats['block_kinds'].get('action', 0)}, sfx {stats['block_kinds'].get('sfx', 0)}, "
        f"camera {stats['block_kinds'].get('camera', 0)})",
        f"- Parser warnings: {stats['parser_warning_count']}",
        f"- Legal windows scored (20-60 s, clean cuts): {stats['windows_scored']}",
        f"- Windows rejected because a start/end fell inside a spoken line: {stats['cuts_inside_lines_avoided']}",
        f"- Windows passing quality gates: {stats['eligible_windows']}",
        f"- Episodes with no window passing gates: {stats['episodes_without_promo'] or 'none'}",
        f"- Cross-episode duplicates dropped: {stats['cross_episode_duplicates']}",
        f"- Ranked promos: {stats['selected_count']} (max {stats['per_episode']} per episode; first wave = top {stats['first_wave']} with one per episode)",
        f"- Model reviewer: {stats['model_status']}",
        f"- Runtime: {stats['runtime_seconds']} s", "",
        "## Top 10 to post first", "",
        "| # | Ep | Start-End | Score | Hook | Cliffhanger |", "|---|---|---|---|---|---|",
    ]
    for p in promos[:10]:
        seg = p["segments"][0]
        lines.append(f"| {p['rank']} | {p['episode']} | {seg['start_time']}-{seg['end_time']} | {p['final_score']} | "
                     f"{p['hook']['text'][:60].replace('|', '/')} | {p['cliffhanger']['text'][:60].replace('|', '/')} |")
    lines += ["", "Scores are a transparent prioritisation aid built from script text only; they are not "
              "measured ad performance. Every pick still needs an editor to watch the footage.", ""]
    if stats.get("model_errors"):
        lines += ["## Model errors (those episodes fell back to rules)", ""]
        lines += [f"- E{e['episode']:02d}: {e['error']}" for e in stats["model_errors"]] + [""]
    path.write_text("\n".join(lines), encoding="utf-8")
