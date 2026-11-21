"""Write the editor's report: JSON (machines), Markdown (repo / doc), HTML (review page), CSV (triage)."""

from __future__ import annotations

import csv
import html
import json
from collections import Counter
from pathlib import Path
from typing import Dict, List

from .checker import Finding, to_dict


def write_all(out: Path, findings: List[Finding], meta: Dict[str, object]) -> None:
    out.mkdir(parents=True, exist_ok=True)
    (out / "findings.json").write_text(json.dumps({"run": meta, "findings": [to_dict(f) for f in findings]},
                                                  ensure_ascii=False, indent=2), encoding="utf-8")
    with (out / "findings.csv").open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(["n", "severity", "type", "episodes", "title", "first_location", "suggestion", "editor_verdict", "editor_notes"])
        for i, f in enumerate(findings, 1):
            first = f.locations[0] if f.locations else {}
            w.writerow([i, f.severity, f.type, " ".join(map(str, f.episodes[:12])), f.title,
                        f"E{first.get('episode', '')} {first.get('block', '')} {first.get('time', '')}".strip(),
                        f.suggestion, "", ""])
    counts = Counter((f.type, f.severity) for f in findings)
    md = [f"# Continuity report: {meta['show']}", "",
          f"{meta['episodes']} episodes, {meta['blocks']} timed cues, {len(findings)} findings "
          f"({sum(1 for f in findings if f.severity == 'error')} errors, "
          f"{sum(1 for f in findings if f.severity == 'warning')} warnings). Model review: {meta['model']}.", "",
          "| Check | Errors | Warnings |", "|---|---|---|"]
    for t in sorted({f.type for f in findings}):
        md.append(f"| {t} | {counts[(t, 'error')]} | {counts[(t, 'warning')]} |")
    md += ["", "## Findings (errors first)", ""]
    for i, f in enumerate(findings, 1):
        md.append(f"{i}. **[{f.severity}] {f.type}**: {f.title}")
        for l in f.locations[:3]:
            md.append(f"   - E{l['episode']} {l['block']} {l['time']}: \"{l['text'][:100]}\"")
        if f.suggestion:
            md.append(f"   - Fix: {f.suggestion}")
        if f.model_review and f.model_review.get("used"):
            md.append(f"   - Model ({f.model_review['model']}): canonical '{f.model_review['canonical']}', {f.model_review['forms']}")
    (out / "report.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    e = html.escape
    cards = []
    for i, f in enumerate(findings, 1):
        locs = "".join(f"<li><b>E{e(l['episode'])} {e(l['block'])}</b> {e(l['time'])}: “{e(l['text'][:140])}”</li>" for l in f.locations[:5])
        cards.append(f'<section class="c {f.severity}"><div class="h"><span class="sev">{f.severity}</span> <b>{e(f.type)}</b>'
                     f' · episodes {e(", ".join(map(str, f.episodes[:15])))}</div><p>{e(f.title)}</p><ul>{locs}</ul>'
                     f'<p class="fix">Fix: {e(f.suggestion)}</p></section>')
    page = f"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Continuity Report</title><style>
:root{{--bg:#f7f6f2;--fg:#1c2230;--muted:#5d6675;--card:#fff;--line:#e2e0d8;--err:#b3261e;--warn:#9a6700}}
@media (prefers-color-scheme: dark){{:root{{--bg:#14171c;--fg:#e8eaee;--muted:#9aa3b2;--card:#1c2027;--line:#2c313a;--err:#ff8a80;--warn:#f2c14e}}}}
body{{margin:0 auto;max-width:900px;padding:16px;background:var(--bg);color:var(--fg);font:15px/1.45 system-ui,sans-serif}}
.c{{background:var(--card);border:1px solid var(--line);border-left:4px solid var(--warn);border-radius:8px;padding:10px 12px;margin:10px 0}}
.c.error{{border-left-color:var(--err)}} .sev{{text-transform:uppercase;font-size:12px;font-weight:700;color:var(--muted)}}
.fix{{color:var(--muted)}} ul{{margin:4px 0 4px 18px;padding:0}} p{{margin:6px 0}}
</style></head><body><h1>Continuity report: {e(str(meta['show']))}</h1>
<p>{meta['episodes']} episodes · {len(findings)} findings · errors first. Every finding links to an episode, cue ID and time.</p>
{''.join(cards)}</body></html>"""
    (out / "report.html").write_text(page, encoding="utf-8")
