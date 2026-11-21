"""Continuity checks for AI-generated microdrama screenplays.

One user (the script/story editor), one step (QA of generated episodes before they go to
voice and video generation), one output (a ranked list of continuity defects with locations).

Checks, all deterministic:
  NAME_DRIFT      one person/place spelled several ways across episodes (Ashford / Ashforde / Ashferd)
  LABEL_ALIAS     one character under two speaker labels (LADY MARA vs MARA)
  UNNAMED_RECURRING  a recurring speaker known only by a description (e.g. "TALL STRANGER" across 10 episodes),
                  so voice and character-reference assets can't be keyed to a stable identity
  SPEECH_RATE     a line has more words than can be spoken in its time slot (> 4.5 words/s warn, > 5.0 error; 4.0-4.5 was mostly sayable in a spot check)
  SELF_OVERLAP    a speaker starts a line before their previous line ends
  SCENE_BOUNDS    a cue falls outside its scene's start/end, or scenes overlap/leave gaps
  CONTINUITY_REF  continuity notes point to the wrong previous episode
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from difflib import SequenceMatcher
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .parser import Block, Episode, format_time, parse_text, to_seconds

GENERIC_LABEL_WORDS = {"MAN", "WOMAN", "LADY", "LORD", "NOBLEMAN", "NOBLEWOMAN", "GUARD", "STRANGER", "MATRIARCH",
                       "GROOM", "BRIDE", "THUG", "MAID", "CONSTABLE", "OFFICIAL", "PRIEST", "SERVANT", "SOLDIER",
                       "OFFICER", "VOICE", "GIRL", "BOY", "OLD", "YOUNG", "MYSTERIOUS", "BLOND", "BEARDED", "TALL",
                       "BALD", "ELDER", "FORMER", "INFORMANT", "PEASANT", "VILLAGER", "DOCTOR", "WITNESS", "JUDGE",
                       "HOUSEKEEPER", "BUTLER", "NURSE", "MERCHANT", "CLERK", "MESSENGER", "OFF-SCREEN"}
HONORIFICS = re.compile(r"^(?:LADY|LORD|SIR|THE|DUKE|DUCHESS|DOWAGER|MR\.?|MRS\.?|MISS|MS\.?|DR\.?|FATHER|MOTHER)\s+")
COMMON_CAPS = {"The", "This", "That", "Then", "There", "They", "What", "When", "Where", "Your", "Grace", "Lord", "Lady",
               "Father", "Mother", "Sister", "Brother", "Close", "Medium", "Wide", "Over", "Tight", "Extreme", "High",
               "Low", "Slow", "Push", "Full", "Cut", "God", "Duke", "Duchess", "Sir", "Madam", "Please", "Yes",
               "Every", "Because", "Into", "From", "With", "Without", "Behind", "Inside", "Outside", "Under", "Above",
               "Before", "After", "Until", "While", "Even", "Only", "Just", "Still", "Never", "Always", "Here",
               "Something", "Someone", "Nothing", "Everyone", "Gothic", "Profile", "Side", "Angle",
               "Shot", "Insert", "Tracking", "Panning", "Overhead", "Reverse", "Two", "Three", "Point", "View"}
# Capitalised words that are descriptions, not names ("Tall Stranger", "Old Servant")
DESCRIPTIVE = {w.title() for w in GENERIC_LABEL_WORDS} | {"Noble", "Gown", "Gold", "Cap", "Royal", "Crown", "High",
               "Former", "Dowager", "Matriarch", "Nobleman", "Noblewoman"}
CONT_REF = re.compile(r"(?:picks up|follows|continues|continuing)(?:\s+(?:directly|immediately|straight))?"
                      r"(?:\s+(?:from|after))?(?:\s+the\s+end\s+of)?\s+Episode\s+(\d+)", re.I)
SCENE_RE = re.compile(r"^Scene heading:\s*(.*)$", re.I)
SCENE_TIME_RE = re.compile(r"^Scene (start|end):\s*((?:\d+:)?\d+:\d+(?:[.,]\d+)?)", re.I)

SEVERITY_ORDER = {"error": 0, "warning": 1, "info": 2}


@dataclass
class Finding:
    type: str
    severity: str  # error | warning | info
    title: str
    episodes: List[int]
    locations: List[Dict[str, str]] = field(default_factory=list)  # [{episode, block, time, text}]
    suggestion: str = ""
    evidence: Dict[str, object] = field(default_factory=dict)
    model_review: Optional[Dict[str, object]] = None


@dataclass
class Script:
    episode: Episode
    scenes: List[Tuple[str, Optional[float], Optional[float]]]


def load(folder: Path) -> List[Script]:
    folder = Path(folder)
    paths = [folder] if folder.is_file() else sorted(p for p in folder.glob("*.txt") if not p.name.startswith("."))
    if not folder.exists():
        raise ValueError(f"Input path does not exist: {folder}")
    if not paths:
        raise ValueError(f"No .txt episode files found in {folder}")
    return load_texts({p.name: p.read_bytes().decode("utf-8", errors="replace") for p in paths})


def load_texts(texts: Dict[str, str]) -> List[Script]:
    """Parse episodes from {file name: text}; used by load() and by the seeded-error evaluation."""
    out = []
    for name, raw in sorted(texts.items()):
        ep = parse_text(raw, name)
        if not ep.blocks:
            raise ValueError(f"{name}: no timed blocks found")
        scenes: List[List] = []
        for line in raw.splitlines():
            line = line.strip()
            m = SCENE_RE.match(line)
            if m:
                scenes.append([m.group(1).strip(), None, None])
                continue
            t = SCENE_TIME_RE.match(line)
            if t and scenes:
                scenes[-1][1 if t.group(1).lower() == "start" else 2] = to_seconds(t.group(2))
        out.append(Script(ep, [tuple(s) for s in scenes]))
    nums = [s.episode.number for s in out]
    dup = sorted({n for n in nums if nums.count(n) > 1})
    if dup:
        raise ValueError(f"Duplicate episode numbers {dup}")
    return sorted(out, key=lambda s: s.episode.number)


def loc(ep: Episode, b) -> Dict[str, str]:
    return {"episode": str(ep.number), "block": b.id, "time": format_time(b.start), "text": b.text[:140]}


FEMALE = {"LADY", "MRS", "MRS.", "MISS", "MS", "MS.", "DUCHESS", "MOTHER", "QUEEN"}
MALE = {"LORD", "SIR", "MR", "MR.", "DUKE", "FATHER", "KING"}


def label_gender(label: str) -> str:
    first = label.strip().upper().split(" ")[0]
    return "f" if first in FEMALE else ("m" if first in MALE else "")


def canon_label(label: str) -> str:
    prev = None
    while prev != label:
        prev, label = label, HONORIFICS.sub("", label.strip().upper())
    return label


# --------------------------------------------------------------------------------------------- names

def proper_nouns(scripts: List[Script]) -> Dict[str, List[Tuple[Episode, object]]]:
    occ: Dict[str, List[Tuple[Episode, object]]] = defaultdict(list)
    initial: Dict[str, List[Tuple[Episode, object]]] = defaultdict(list)
    for s in scripts:
        ep = s.episode
        # Loglines and continuity notes feed the generator too, so names there are checked as well.
        meta = [Block("LOGLINE", "meta", 0.0, 0.0, ep.logline), Block("CONTINUITY NOTES", "meta", 0.0, 0.0, ep.continuity)]
        for b in ep.blocks + meta:
            for m in re.finditer(r"\b([A-Z][a-z]{3,}(?:'s)?)\b", b.text):
                word = m.group(1)
                word = word[:-2] if word.endswith("'s") else word
                if word in COMMON_CAPS or word in DESCRIPTIVE:
                    continue
                before = b.text[:m.start()].rstrip()
                sentence_start = not before or before[-1] in ".!?\"“…—-"
                (initial if sentence_start else occ)[word].append((s.episode, b))
    # A capitalised word at the start of a sentence ("Look", "General", "Ruppert") counts only if it is a name
    # seen mid-sentence elsewhere, or a very close spelling (>= 0.8) of a frequent name.
    frequent = [w for w in occ if len(occ[w]) >= 3]
    for word, hits in initial.items():
        if word in occ or any(similar(word, n) >= 0.8 and word[1:3].lower() == n[1:3].lower() for n in frequent):
            occ[word].extend(hits)
    # fold plurals ("Ashcombes" -> "Ashcombe") when the singular exists
    for word in list(occ):
        if word.endswith("s") and word[:-1] in occ:
            occ[word[:-1]].extend(occ.pop(word))
    return occ


def similar(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def name_drift(scripts: List[Script], threshold: float = 0.72) -> List[Finding]:
    occ = proper_nouns(scripts)
    words = sorted(occ, key=lambda w: -len(occ[w]))
    # Cluster by spelling similarity + same first 3 letters (single linkage).
    parent = {w: w for w in words}

    def find(w):
        while parent[w] != w:
            parent[w] = parent[parent[w]]
            w = parent[w]
        return w
    for i, a in enumerate(words):
        for b in words[i + 1:]:
            same_start = a[:3].lower() == b[:3].lower() and similar(a, b) >= threshold
            # Korinna / Corinna, Jerard / Gerard: only the first letter differs
            first_letter = min(len(a), len(b)) >= 5 and similar(a[1:], b[1:]) >= 0.85
            if same_start or first_letter:
                parent[find(b)] = find(a)
    clusters: Dict[str, List[str]] = defaultdict(list)
    for w in words:
        clusters[find(w)].append(w)
    findings = []
    for members in clusters.values():
        if len(members) < 2:
            continue
        members.sort(key=lambda w: -len(occ[w]))
        dominant = members[0]
        variants = members[1:]
        eps = sorted({e.number for w in members for e, _ in occ[w]})
        sev = "error" if len(members) >= 3 or any(len({e.number for e, _ in occ[v]}) >= 2 for v in variants) else "warning"
        locs = [loc(e, b) for v in variants for e, b in occ[v][:3]]
        findings.append(Finding(
            "NAME_DRIFT", sev, f"'{dominant}' appears in {len(members)} spellings: " + ", ".join(
                f"{w} ({len(occ[w])}x)" for w in members),
            eps, locs[:12],
            f"Confirm which spelling is canonical, add it to the show bible, and correct the others. "
            f"Some forms may be genuinely different names (check before replacing).",
            {"forms": {w: {"count": len(occ[w]), "episodes": sorted({e.number for e, _ in occ[w]})} for w in members},
             "examples": {w: [b.text[:120] for _, b in occ[w][:2]] for w in members}}))
    return findings


# --------------------------------------------------------------------------------------------- labels

def label_checks(scripts: List[Script], recurring_eps: int = 3, recurring_lines: int = 10) -> List[Finding]:
    lines: Dict[str, List[Tuple[Episode, object]]] = defaultdict(list)
    for s in scripts:
        for b in s.episode.blocks:
            if b.kind == "dialogue" and b.speaker:
                lines[b.speaker].append((s.episode, b))
    findings = []
    by_canon: Dict[str, List[str]] = defaultdict(list)
    for label in lines:
        by_canon[canon_label(label)].append(label)
    for c, labels in by_canon.items():
        genders = {label_gender(l) for l in labels}
        if "" not in genders and len(genders) > 1:
            continue  # LORD ASHFORD and LADY ASHFORD (no plain ASHFORD) are a couple, not one mislabelled person
        if len(labels) > 1:
            labels.sort(key=lambda l: -len(lines[l]))
            eps = sorted({e.number for l in labels for e, _ in lines[l]})
            findings.append(Finding(
                "LABEL_ALIAS", "warning", f"One character, {len(labels)} speaker labels: " + ", ".join(
                    f"{l} ({len(lines[l])} lines, {len({e.number for e, _ in lines[l]})} eps)" for l in labels),
                eps, [loc(e, b) for l in labels[1:] for e, b in lines[l][:2]],
                f"Use one label ('{labels[0]}') everywhere so voice and character references map to one identity.",
                {"labels": {l: len(lines[l]) for l in labels}}))
    name_counts = Counter(w for s in scripts for b in s.episode.blocks if b.kind in ("camera", "action")
                          for w in re.findall(r"\b([A-Z][a-z]{3,})\b", b.text) if w not in COMMON_CAPS)
    for label, occ in lines.items():
        words = set(label.replace("'S", "").split())
        if not words or not words <= GENERIC_LABEL_WORDS:
            continue
        eps = sorted({e.number for e, _ in occ})
        if len(eps) < 2 or (len(eps) < recurring_eps and len(occ) < recurring_lines):
            continue  # one-off extras ("JUDGE" in a single trial episode) are fine
        guesses = guess_identity(scripts, label, name_counts)
        findings.append(Finding(
            "UNNAMED_RECURRING", "error" if len(eps) >= 5 else "warning",
            f"Recurring speaker '{label}' has no name ({len(occ)} lines across {len(eps)} episodes)",
            eps, [loc(e, b) for e, b in occ[:3]],
            "Give this character a stable name/ID in the show bible and use it as the speaker label."
            + (f" Likely the same person as: {', '.join(f'{n} ({c})' for n, c in guesses)} (check)." if guesses else ""),
            {"likely_identity": guesses}))
    return findings


def guess_identity(scripts: List[Script], label: str, name_counts: Counter) -> List[Tuple[str, int]]:
    """Names that camera/action text uses while this label is speaking (within +/-1.5 s)."""
    votes: Counter = Counter()
    for s in scripts:
        blocks = s.episode.blocks
        speaking = [b for b in blocks if b.kind == "dialogue" and b.speaker == label]
        other_speakers = {canon_label(b.speaker).title() for b in blocks if b.kind == "dialogue" and b.speaker != label}
        for line in speaking:
            for b in blocks:
                if b.kind in ("camera", "action") and b.start - 1.5 <= line.start <= b.end + 1.5:
                    for name in re.findall(r"\b([A-Z][a-z]{3,})\b", b.text):
                        if (name not in COMMON_CAPS and name not in DESCRIPTIVE and name.upper() not in label
                                and name not in other_speakers and name_counts[name] >= 3):
                            votes[name] += 1
    total = sum(votes.values())
    return [(n, c) for n, c in votes.most_common(2) if total and c / total >= 0.25 and c >= 2]


# --------------------------------------------------------------------------------------------- timing

def timing_checks(scripts: List[Script], warn_wps: float = 4.5, error_wps: float = 5.0) -> List[Finding]:
    findings = []
    for s in scripts:
        ep = s.episode
        for b in ep.blocks:
            if b.kind != "dialogue" or b.duration <= 0:
                continue
            words = len(re.findall(r"[A-Za-z']+|[ऀ-ॿ]+", b.text))
            rate = words / b.duration
            if rate > warn_wps and words >= 4:
                need = words / 2.5
                findings.append(Finding(
                    "SPEECH_RATE", "error" if rate > error_wps else "warning",
                    f"E{ep.number:02d} {b.id}: {words} words in {b.duration:.1f}s ({rate:.1f} words/s)",
                    [ep.number], [loc(ep, b)],
                    f"Give the line about {need:.1f}s (at ~2.5 words/s, this show's median pace) or shorten it.",
                    {"words": words, "seconds": round(b.duration, 2), "words_per_second": round(rate, 2)}))
        last: Dict[str, object] = {}
        for b in sorted((b for b in ep.blocks if b.kind == "dialogue"), key=lambda b: b.start):
            prev = last.get(b.speaker)
            if prev is not None and b.start < prev.end - 0.05:
                findings.append(Finding(
                    "SELF_OVERLAP", "error", f"E{ep.number:02d}: {b.speaker} starts {b.id} before finishing {prev.id}",
                    [ep.number], [loc(ep, prev), loc(ep, b)],
                    f"Move {b.id} to start at or after {format_time(prev.end)}, or merge the two lines."))
            last[b.speaker] = b
        scenes = [sc for sc in s.scenes if sc[1] is not None and sc[2] is not None]
        for i, (head, start, end) in enumerate(scenes):
            if end <= start:
                findings.append(Finding("SCENE_BOUNDS", "error", f"E{ep.number:02d}: scene '{head}' ends before it starts",
                                        [ep.number], [], "Fix the scene start/end times."))
            if i + 1 < len(scenes) and abs(scenes[i + 1][1] - end) > 0.05:
                kind = "gap" if scenes[i + 1][1] > end else "overlap"
                findings.append(Finding("SCENE_BOUNDS", "warning",
                                        f"E{ep.number:02d}: {kind} of {abs(scenes[i + 1][1] - end):.2f}s between scenes {i + 1} and {i + 2}",
                                        [ep.number], [], "Scene end should equal the next scene's start."))
            same_head = [sc for sc in scenes if sc[0] == head]  # headings repeat ("INT. CELL - NIGHT" twice)
            inside = [b for b in ep.blocks if b.scene == head and start - 0.05 <= b.start <= end + 0.05]
            outside = [b for b in inside if b.end > end + 0.05]
            outside += [b for b in ep.blocks if b.scene == head and len(same_head) == 1
                        and not (start - 0.05 <= b.start <= end + 0.05)]
            for b in outside[:3]:
                findings.append(Finding("SCENE_BOUNDS", "warning",
                                        f"E{ep.number:02d} {b.id}: cue {format_time(b.start)}-{format_time(b.end)} is outside "
                                        f"its scene ({format_time(start)}-{format_time(end)})", [ep.number], [loc(ep, b)],
                                        "Align the cue with its scene or fix the scene times."))
    return findings


def continuity_refs(scripts: List[Script]) -> List[Finding]:
    findings = []
    numbers = {s.episode.number for s in scripts}
    for s in scripts:
        ep = s.episode
        for m in CONT_REF.finditer(ep.continuity):
            ref = int(m.group(1))
            if ref != ep.number - 1 and (ep.number - 1) in numbers | {0}:
                findings.append(Finding(
                    "CONTINUITY_REF", "error",
                    f"E{ep.number:02d} continuity notes say '{m.group(0)}' but the previous episode is {ep.number - 1}",
                    [ep.number], [{"episode": str(ep.number), "block": "CONTINUITY NOTES", "time": "", "text": ep.continuity[:140]}],
                    f"Check whether the episode order is wrong or the note should reference Episode {ep.number - 1}."))
    return findings


def run_checks(scripts: List[Script]) -> List[Finding]:
    findings = name_drift(scripts) + label_checks(scripts) + timing_checks(scripts) + continuity_refs(scripts)
    findings.sort(key=lambda f: (SEVERITY_ORDER[f.severity], f.type, min(f.episodes) if f.episodes else 0, f.title))
    return findings


def to_dict(f: Finding) -> Dict[str, object]:
    return asdict(f)
