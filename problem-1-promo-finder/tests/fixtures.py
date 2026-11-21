"""Synthetic screenplays for tests. Invented text only; no Kuku content."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Tuple

Beat = Tuple[str, float, float, str]  # (label, start, end, text)


def stamp(t: float) -> str:
    m = int(t // 60)
    return f"{m:02d}:{t - 60 * m:05.2f}"


def screenplay(number: int, beats: Iterable[Beat], logline: str = "A test episode.", scene: str = "INT. HALL - DAY") -> str:
    out: List[str] = [f"EPISODE NUMBER: Episode {number}", f"EPISODE LOGLINE: {logline}",
                      "CONTINUITY NOTES: none", "", "--- SCRIPT START ---", "", "SCENE 01",
                      f"Scene heading: {scene}", "", "Actions and dialogue:", ""]
    for label, start, end, text in beats:
        out += [f"**{label}:**", f"Start: ({stamp(start)}) | End: ({stamp(end)})",
                text if label.split(" (")[0] in ("CAMERA", "ACTION", "SOUND FX") else f'"{text}"', ""]
    out.append("--- SCRIPT END ---")
    return "\n".join(out)


def drama_beats(offset: float = 0.0, names=("MARA", "VIKTOR")) -> List[Beat]:
    """~75 s: calm intro, accusation hook at 10 s, escalation, unanswered threat at ~52 s, then calm resolution."""
    a, b = names
    lines = [
        ("CAMERA", 0.0, 4.0, "Wide shot of a candle-lit hall."),
        (f"{a} (Soft, Warm)", 1.0, 3.0, "The tea is ready."),
        (f"{b} (Calm)", 4.0, 6.0, "Thank you."),
        (f"{a} (Gentle)", 6.5, 9.0, "It is a quiet evening."),
        ("CAMERA", 9.5, 12.0, "Close-up on Mara's face hardening."),
        (f"{a} (Outraged, Accusing)", 10.0, 12.0, "You poisoned my sister!"),
        (f"{b} (Cold)", 12.5, 15.0, "Prove it, Mara."),
        (f"{a} (Desperate)", 15.5, 18.5, "I found the vial in your coat, Viktor!"),
        ("ACTION", 19.0, 21.0, "Viktor grabs Mara by the wrist."),
        (f"{b} (Menacing)", 21.0, 24.0, "Say that again and you will hang."),
        (f"{a} (Defiant)", 24.5, 27.0, "Then the whole town will hear the truth!"),
        (f"{b} (Sinister)", 27.5, 31.0, "The town believes whatever I tell them."),
        (f"{a} (Trembling)", 31.5, 34.0, "Why would you hurt her?"),
        (f"{b} (Cruel)", 34.5, 38.0, "Because she knew who I really was."),
        (f"{a} (Horrified)", 38.5, 41.0, "Who are you?"),
        (f"{b} (Chilling)", 41.5, 45.0, "Ask your mother's grave."),
        ("SOUND FX", 45.0, 47.0, "A thunder crack shakes the windows."),
        (f"{a} (Furious)", 47.0, 50.0, "I will tell the magistrate everything!"),
        (f"{b} (Threatening)", 50.5, 54.0, "If you do, your son will be dead by morning."),
        ("SOUND FX", 54.0, 56.0, "Ominous string sting."),
        (f"{a} (Gentle)", 58.0, 60.0, "Please, let us be calm."),
        (f"{b} (Warm, Reassuring)", 60.5, 63.0, "All is well, Mara."),
        (f"{a} (Soft, Relieved)", 63.5, 66.0, "Thank you."),
        (f"{b} (Tender)", 66.5, 69.0, "Rest now."),
        (f"{a} (Calm)", 69.5, 72.0, "Good night."),
    ]
    return [(lab, s + offset, e + offset, t) for lab, s, e, t in lines]


def write_show(folder: Path, episodes: List[str]) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    for i, text in enumerate(episodes, 1):
        (folder / f"episode-{i:03d}.txt").write_text(text, encoding="utf-8")
    return folder
