"""Measure recall by planting known continuity errors into a real show, one at a time.

For each trial: copy the scripts in memory, apply ONE mutation with a known location, run the checker,
and see whether a finding points at the planted error. New findings that are not the planted error
are counted as false alarms caused by the change. Deterministic (fixed random seed).

    python3 evaluate_seeded.py --show <folder> [--per-type 20] [--json-out outputs/logs/seeded_eval.json]
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
from collections import defaultdict
from pathlib import Path

from continuity.checker import CONT_REF, load_texts, run_checks

LEADS: list = []          # filled from the show itself (most frequent names), so no show content is hard-coded
LEAD_LABELS: list = []    # most frequent single-word speaker labels


def detect_leads(texts):
    from collections import Counter
    from continuity.checker import proper_nouns
    scripts = load_texts(texts)
    occ = proper_nouns(scripts)
    names = [w for w, hits in sorted(occ.items(), key=lambda kv: (-len(kv[1]), kv[0])) if len(w) >= 5][:6]
    labels = Counter(b.speaker for s in scripts for b in s.episode.blocks if b.kind == "dialogue" and b.speaker
                     and " " not in b.speaker and len(b.speaker) >= 4)
    return names, [l for l, _ in sorted(labels.items(), key=lambda kv: (-kv[1], kv[0]))][1:6]
CUE_RE = re.compile(r"^Start:\s*\((\d+):(\d+(?:\.\d+)?)\)\s*\|\s*End:\s*\((\d+):(\d+(?:\.\d+)?)\)", re.M)


def misspell(name: str, rng: random.Random) -> str:
    ops = [
        lambda n: n[:2] + n[2] + n[2:],                                   # double a letter: Julliana
        lambda n: n[:-3] + n[-2] + n[-3] + n[-1],                         # swap two letters: Juliaan
        lambda n: re.sub(r"[aeiou](?=[^aeiou]*$)", lambda m: "e" if m.group(0) != "e" else "a", n, count=1),  # vowel
        lambda n: {"C": "K", "K": "C", "J": "G", "G": "J", "R": "Ro", "A": "E"}.get(n[0], n[0]) + n[1:],      # first letter
    ]
    out = rng.choice(ops)(name)
    return out if out != name else name + "e"


def fmt(t: float) -> str:
    m = int(t // 60)
    return f"{m:02d}:{t - 60 * m:05.2f}"


def cue_lines(text: str):
    return list(CUE_RE.finditer(text))


def mutate(kind: str, texts, rng):
    """Return (new_texts, truth) where truth describes what a correct finding must point at."""
    names = sorted(texts)
    for _ in range(200):
        fname = rng.choice(names)
        text = texts[fname]
        if kind == "name_variant":
            lead = rng.choice(LEADS)
            hits = [m for m in re.finditer(r"\b" + lead + r"\b", text)]
            if not hits:
                continue
            m = rng.choice(hits)
            bad = misspell(lead, rng)
            new = text[:m.start()] + bad + text[m.end():]
            return {**texts, fname: new}, {"type": "NAME_DRIFT", "form": bad, "op": f"{lead}->{bad}"}
        if kind == "label_variant":
            lead = rng.choice(LEAD_LABELS)
            hits = list(re.finditer(r"^\*\*" + lead + r"(?= \(|:)", text, re.M))
            if not hits:
                continue
            m = rng.choice(hits)
            bad = rng.choice(["LORD ", "SIR ", "LADY ", "THE "]) + lead
            new = text[:m.start()] + "**" + bad + text[m.end():]
            return {**texts, fname: new}, {"type": "LABEL_ALIAS", "form": bad, "op": f"{lead}->{bad}"}
        if kind == "compress_line":
            # pick a dialogue cue with >= 6 words and make its slot impossibly short (8 words/s)
            blocks = re.finditer(r"^\*\*([A-Z][^*(:]+?)(?: \([^)]*\))*:\*\*\n(Start: [^\n]+)\n\"?([^\n]+)", text, re.M)
            cands = [b for b in blocks if b.group(1).strip() not in ("CAMERA", "ACTION", "SOUND FX")
                     and len(b.group(3).split()) >= 6]
            if not cands:
                continue
            b = rng.choice(cands)
            cue = CUE_RE.match(b.group(2))
            start = int(cue.group(1)) * 60 + float(cue.group(2))
            end = start + max(0.3, len(b.group(3).split()) / 8.0)
            new_line = f"Start: ({fmt(start)}) | End: ({fmt(end)})"
            new = text[:b.start(2)] + new_line + text[b.end(2):]
            return {**texts, fname: new}, {"type": "SPEECH_RATE", "file": fname, "text": b.group(3)[:40].strip('"')}
        if kind == "self_overlap":
            blocks = list(re.finditer(r"^\*\*([A-Z][^*(:]+?)(?: \([^)]*\))*:\*\*\n(Start: [^\n]+)", text, re.M))
            pairs = []
            for i, b in enumerate(blocks):
                if b.group(1).strip() in ("CAMERA", "ACTION", "SOUND FX"):
                    continue
                for c in blocks[i + 1:i + 6]:
                    if c.group(1).strip() == b.group(1).strip():
                        pairs.append((b, c))
                        break
            if not pairs:
                continue
            b, c = rng.choice(pairs)
            cb, cc = CUE_RE.match(b.group(2)), CUE_RE.match(c.group(2))
            b_end = int(cb.group(3)) * 60 + float(cb.group(4))
            c_start = int(cc.group(1)) * 60 + float(cc.group(2))
            c_end = int(cc.group(3)) * 60 + float(cc.group(4))
            new_start = max(0.0, b_end - 0.6)
            if new_start >= c_start:
                continue
            new_line = f"Start: ({fmt(new_start)}) | End: ({fmt(c_end)})"
            new = text[:c.start(2)] + new_line + text[c.end(2):]
            return {**texts, fname: new}, {"type": "SELF_OVERLAP", "file": fname, "speaker": c.group(1).strip()}
        if kind == "continuity_ref":
            line = next((l for l in text.split("\n") if l.startswith("CONTINUITY NOTES")), "")
            m = CONT_REF.search(line)
            if not m:
                continue
            wrong = int(m.group(1)) + rng.choice([2, 3, -2]) if int(m.group(1)) > 2 else int(m.group(1)) + 2
            new_line = line[:m.start(1)] + str(wrong) + line[m.end(1):]
            return {**texts, fname: text.replace(line, new_line, 1)}, {"type": "CONTINUITY_REF", "file": fname}
    raise RuntimeError(f"could not plant {kind}")


def episode_of(fname: str) -> int:
    return int(re.search(r"(\d+)", fname).group(1))


def detected(truth, findings) -> bool:
    """A finding counts only if it is the right type AND points at the planted spot."""
    for f in findings:
        if f.type != truth["type"]:
            continue
        if truth["type"] in ("NAME_DRIFT", "LABEL_ALIAS") and re.search(r"(?<![A-Za-z])" + re.escape(truth["form"]) + r" \(", f.title):
            return True
        if truth["type"] == "SPEECH_RATE" and any(truth["text"][:25] in l["text"] for l in f.locations):
            return True
        if truth["type"] == "SELF_OVERLAP" and truth["speaker"] in f.title and episode_of(truth["file"]) in f.episodes:
            return True
        if truth["type"] == "CONTINUITY_REF" and episode_of(truth["file"]) in f.episodes:
            return True
    return False


def key(f):
    return (f.type, f.title)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--show", type=Path, required=True)
    ap.add_argument("--per-type", type=int, default=20)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--json-out", type=Path)
    a = ap.parse_args(argv)
    texts = {p.name: p.read_text(encoding="utf-8") for p in sorted(a.show.glob("*.txt"))}
    LEADS[:], LEAD_LABELS[:] = detect_leads(texts)
    print(f"names used for planted errors: {LEADS}; labels: {LEAD_LABELS}")
    baseline = {key(f) for f in run_checks(load_texts(texts))}
    rng = random.Random(a.seed)
    results = defaultdict(lambda: {"planted": 0, "caught": 0, "new_false_alarms": 0, "missed": []})
    for kind in ["name_variant", "label_variant", "compress_line", "self_overlap", "continuity_ref"]:
        for _ in range(a.per_type):
            mutated, truth = mutate(kind, texts, rng)
            findings = run_checks(load_texts(mutated))
            r = results[kind]
            r["planted"] += 1
            hit = detected(truth, findings)
            r["caught"] += hit
            if not hit:
                r["missed"].append(truth.get("op") or truth.get("text") or truth.get("file"))
            new = [f for f in findings if key(f) not in baseline and f.type != truth["type"]]
            r["new_false_alarms"] += len(new)
    total_p = sum(r["planted"] for r in results.values())
    total_c = sum(r["caught"] for r in results.values())
    print(f"{'error type':<16} planted caught recall  extra-findings")
    for kind, r in results.items():
        print(f"{kind:<16} {r['planted']:>7} {r['caught']:>6} {100 * r['caught'] / r['planted']:>5.0f}%  {r['new_false_alarms']:>6}")
    print(f"{'TOTAL':<16} {total_p:>7} {total_c:>6} {100 * total_c / total_p:>5.0f}%")
    for kind, r in results.items():
        if r["missed"]:
            print(f"  missed {kind}: {r['missed'][:8]}")
    if a.json_out:
        a.json_out.parent.mkdir(parents=True, exist_ok=True)
        a.json_out.write_text(json.dumps({"seed": a.seed, "per_type": a.per_type, "results": results}, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
