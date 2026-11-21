"""Deterministic screenplay parser.

Turns a timestamped episode script into a list of timed `Block`s. Nothing in
this module uses a model: timestamps must be copied exactly, never generated.
Every recoverable problem becomes a warning in `Episode.warnings` rather than a
silent drop, so a new show in a slightly different format fails loudly.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

# "Start: (00:13.50) | End: (00:14.30)"; also tolerates h:mm:ss, missing
# parentheses and comma decimals.
_TIME = r"\(?\s*((?:\d+:)?\d+:\d+(?:[.,]\d+)?)\s*\)?"
TIMESTAMP_RE = re.compile(r"^Start:\s*" + _TIME + r"\s*\|\s*End:\s*" + _TIME, re.I)
# "**LADY MARA (Confused, Breathless):**" (bold optional)
HEADER_RE = re.compile(r"^\*{0,2}\s*([A-Z][^*:]{0,80}?)\s*:\s*\*{0,2}\s*$")
SCENE_RE = re.compile(r"^Scene heading:\s*(.*)$", re.I)
META_RE = re.compile(r"^(EPISODE NUMBER|EPISODE LOGLINE|CONTINUITY NOTES):\s*(.*)$", re.I)
STRUCTURAL_LABELS = {"ACTIONS AND DIALOGUE", "SCRIPT START", "SCRIPT END"}

NON_DIALOGUE = {
    "CAMERA": "camera",
    "ACTION": "action",
    "SOUND FX": "sfx",
    "SFX": "sfx",
    "SOUND": "sfx",
    "MUSIC": "sfx",
    "TEXT": "action",
    "ON-SCREEN TEXT": "action",
    "TRANSITION": "camera",
}

CONTINUATION_END = re.compile(r"(?:\.\.\.|…)\s*[\"”]?$")
CONTINUATION_START = re.compile(r"^[\"“]?\s*(?:\.\.\.|…)")


@dataclass
class Block:
    id: str
    kind: str  # dialogue | action | sfx | camera
    start: float
    end: float
    text: str
    speaker: str = ""
    emotion: str = ""
    scene: str = ""
    # True when this dialogue line is the first half of a sentence that the
    # same speaker finishes in the next dialogue block ("...the poison exists" /
    # "...is the maid"). A clip must never be cut between the two halves.
    continues: bool = False

    @property
    def duration(self) -> float:
        return self.end - self.start


@dataclass
class Episode:
    number: int
    file: str
    logline: str
    continuity: str
    blocks: List[Block] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @property
    def duration(self) -> float:
        return max((b.end for b in self.blocks), default=0.0)


def to_seconds(stamp: str) -> float:
    parts = stamp.replace(",", ".").split(":")
    seconds = float(parts[-1])
    minutes = int(parts[-2]) if len(parts) >= 2 else 0
    hours = int(parts[-3]) if len(parts) >= 3 else 0
    return hours * 3600 + minutes * 60 + seconds


def format_time(value: float) -> str:
    minutes = int(value // 60)
    seconds = value - minutes * 60
    return f"{minutes:02d}:{seconds:05.2f}"


def _split_label(label: str) -> tuple:
    """'LADY MARA (Confused, Breathless)' -> ('LADY MARA', 'Confused, Breathless').

    Handles stacked parentheticals such as 'MATRIARCH (O.S.) (Firm)'.
    """
    parens = re.findall(r"\(([^)]*)\)", label)
    name = re.sub(r"\([^)]*\)", "", label).strip().upper()
    emotion = ", ".join(p.strip() for p in parens if p.strip().upper() not in {"O.S.", "V.O.", "CONT'D", "OS", "VO"})
    return name, emotion


def parse_text(text: str, file_name: str = "<memory>") -> Episode:
    lines = text.splitlines()
    metadata = {}
    for line in lines[:15]:
        match = META_RE.match(line.strip())
        if match:
            metadata[match.group(1).upper()] = match.group(2).strip()

    number_match = re.search(r"\d+", metadata.get("EPISODE NUMBER", "")) or re.search(r"(\d+)", file_name)
    if not number_match:
        raise ValueError(f"{file_name}: could not determine episode number (no 'EPISODE NUMBER:' line or digits in file name)")
    episode = Episode(number=int(number_match.group()), file=file_name,
                      logline=metadata.get("EPISODE LOGLINE", ""), continuity=metadata.get("CONTINUITY NOTES", ""))
    if not episode.logline:
        episode.warnings.append("no EPISODE LOGLINE found")

    scene = ""
    current: Optional[Block] = None
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        scene_match = SCENE_RE.match(line)
        if scene_match:
            scene = scene_match.group(1).strip()
            current = None
            i += 1
            continue

        header = HEADER_RE.match(line)
        if header and header.group(1).strip().upper() not in STRUCTURAL_LABELS:
            # Look ahead past blank lines for the timestamp line.
            j = i + 1
            while j < len(lines) and not lines[j].strip() and j - i <= 2:
                j += 1
            stamp = TIMESTAMP_RE.match(lines[j].strip()) if j < len(lines) else None
            if stamp:
                label = header.group(1).strip()
                kind = NON_DIALOGUE.get(label.upper(), "dialogue")
                speaker, emotion = ("", "")
                if kind == "dialogue":
                    speaker, emotion = _split_label(label)
                start, end = to_seconds(stamp.group(1)), to_seconds(stamp.group(2))
                if end <= start:
                    episode.warnings.append(f"line {j + 1}: end {stamp.group(2)} is not after start {stamp.group(1)}; block skipped")
                    current = None
                    i = j + 1
                    continue
                current = Block(id=f"B{len(episode.blocks) + 1}", kind=kind, start=start, end=end, text="",
                                speaker=speaker, emotion=emotion, scene=scene)
                episode.blocks.append(current)
                i = j + 1
                continue
            if label_looks_like_cue(header.group(1)):
                episode.warnings.append(f"line {i + 1}: cue '{header.group(1).strip()}' has no Start/End timestamp; ignored")
        elif line.lower().startswith("start:") and not TIMESTAMP_RE.match(line):
            episode.warnings.append(f"line {i + 1}: malformed timestamp '{line[:60]}'; following text ignored")
            current = None

        if line.startswith("---") or re.match(r"^SCENE\s+\d+", line, re.I):
            current = None
        elif current is not None and line and not META_RE.match(line) and not re.match(r"^Scene (start|end):", line, re.I):
            current.text = (current.text + " " + line).strip()
        i += 1

    for block in episode.blocks:
        block.text = block.text.strip().strip('"').strip("“”").strip()
        if not block.text:
            episode.warnings.append(f"{block.id}: empty text")
    episode.blocks.sort(key=lambda b: (b.start, b.end))
    _mark_continuations(episode.blocks)
    # NOTE: unlike the promo finder, the continuity checker must NOT normalise "LADY MARA" to "MARA":
    # label inconsistency is exactly what it reports.
    return episode


def label_looks_like_cue(label: str) -> bool:
    label = label.strip()
    return label.isupper() and label.upper() not in STRUCTURAL_LABELS and not label.upper().startswith("SCENE")


def _mark_continuations(blocks: List[Block]) -> None:
    dialogue = [b for b in blocks if b.kind == "dialogue" and b.text]
    for first, second in zip(dialogue, dialogue[1:]):
        if (first.speaker == second.speaker and CONTINUATION_END.search(first.text)
                and CONTINUATION_START.search(second.text) and second.start - first.end < 2.5):
            first.continues = True


def _normalize_speakers(blocks: List[Block]) -> None:
    names = {b.speaker for b in blocks if b.speaker}
    for block in blocks:
        for prefix in ("LADY ", "LORD ", "SIR ", "THE "):
            if block.speaker.startswith(prefix) and block.speaker[len(prefix):] in names:
                block.speaker = block.speaker[len(prefix):]


def parse_episode(path: Path) -> Episode:
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("utf-8", errors="replace")
    episode = parse_text(text, path.name)
    if "�" in text:
        episode.warnings.append("file is not valid UTF-8; undecodable bytes replaced")
    return episode


def load_show(folder: Path) -> List[Episode]:
    folder = Path(folder)
    if folder.is_file():
        paths = [folder]
    elif folder.is_dir():
        paths = sorted(p for p in folder.glob("*.txt") if not p.name.startswith("."))
    else:
        raise ValueError(f"Input path does not exist: {folder}")
    if not paths:
        raise ValueError(f"No .txt episode files found in {folder}")
    episodes = []
    for path in paths:
        episode = parse_episode(path)
        if not episode.blocks:
            raise ValueError(f"{path.name}: no timed blocks found. Expected '**LABEL:**' followed by "
                             "'Start: (mm:ss.xx) | End: (mm:ss.xx)'.")
        episodes.append(episode)
    numbers = [e.number for e in episodes]
    duplicates = sorted({n for n in numbers if numbers.count(n) > 1})
    if duplicates:
        raise ValueError(f"Duplicate episode numbers {duplicates}; check file names / EPISODE NUMBER lines")
    episodes.sort(key=lambda e: e.number)
    return episodes
