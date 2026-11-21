"""Beat-level signals: how much a single line or action can hook, or leave a viewer hanging.

All rules are small, readable lexicons. Each scorer returns (score 0-100, reasons) so
every number in the output can be traced to a human-readable cause.

The biggest signal the first version ignored is the screenplay's own performance
direction: "(Outraged, Accusing)", "(Gentle, Reassuring)". The writers have
already labelled the emotional temperature of every line; we read it.
"""

from __future__ import annotations

import re
from typing import List, Tuple

from .parser import Block

# Performance-direction words, grouped by how much tension they signal.
HIGH_TENSION = {
    "outraged", "furious", "screaming", "shouting", "yelling", "enraged", "livid", "venomous", "menacing",
    "threatening", "sinister", "chilling", "cruel", "vicious", "viciously", "horrified", "terrified", "panicked",
    "desperate", "frantic", "hysterical", "sobbing", "gasping", "accusing", "accusatory", "explosive", "roaring",
    "seething", "murderous", "spiteful", "taunting", "mocking", "gloating", "scornful", "contemptuous", "shocked",
    "stunned", "devastated", "heartbroken", "pleading", "begging", "crying", "weeping", "alarmed", "urgent",
    "defiant", "fierce", "lethal", "deadly", "dangerous", "icy", "raging", "anguished", "choking", "betrayed",
    "incredulous", "piercing", "unhinged", "triumphant", "malicious", "callous", "ruthless", "demanding",
}
MEDIUM_TENSION = {
    "cold", "stern", "sharp", "harsh", "bitter", "smug", "arrogant", "condescending", "dismissive", "steely",
    "firm", "commanding", "resolute", "trembling", "breathless", "shaken", "grave", "grim", "suspicious",
    "tense", "low", "whispering", "derisive", "calculating", "scheming", "unyielding", "tearful", "intense",
    "dark", "ominous", "hard", "authoritative", "final", "confrontational", "challenging", "probing",
}
LOW_TENSION = {
    "gentle", "soft", "warm", "tender", "calm", "reassuring", "relieved", "kind", "soothing", "affectionate",
    "loving", "amused", "cheerful", "happy", "content", "peaceful", "grateful", "sincere", "polite", "playful",
    "smiling", "teasing", "fond", "light", "lighthearted", "warmly", "softly", "gently", "quietly", "earnest",
}

ACCUSATION_RE = re.compile(
    r"\byou\s+(?:planted|poisoned|framed|lied|stole|killed|betrayed|knew|ruined|destroyed|abandoned|tricked|"
    r"used|sold|cheated|murdered|let me|swore|did this|are (?:a|the|nothing|no one|lying))\b", re.I)
THREAT_WORDS = ("kill", "hang", "hangs", "gallows", "noose", "execute", "executed", "execution", "die", "dead",
                "death", "burn", "destroy", "ruin", "you will pay", "or else", "rope", "blood", "prison", "cell",
                "arrest", "condemned", "witch", "poison", "poisoned", "poisoning", "murder")
REVEAL_WORDS = ("the truth", "it was you", "is actually", "was really", "rightful", "your son", "my son",
                "your daughter", "secret", "who are you", "his name", "real name", "duke", "heir", "crest",
                "alive", "never was", "pregnant", "not your", "lied to",
                # relationship reveals: the core twist of most microdramas (added after the E01 altar-reveal miss)
                "marrying me", "marrying her", "marrying him", "is marrying", "engaged to", "affair",
                "having his child", "carrying his child", "your real father", "your real mother")
VIOLENT_ACTION = ("slap", "slaps", "strike", "strikes", "punch", "blood", "collapses", "grabs", "seizes",
                  "attacks", "stabs", "draws a", "sword", "knife", "dagger", "chokes", "shoves", "throws",
                  "crashes", "explodes", "bursts", "burst open", "kicks", "drags", "yanks", "rips",
                  "kisses", "screams", "faints", "smashes", "shatters", "flames", "falls hard", "falls to",
                  "tackles", "lunges", "burning", "collapse")
LOUD_SFX = ("crash", "bang", "explosion", "scream", "gunshot", "thunder", "slam", "shatter", "pounding",
            "clatter", "slap", "crack", "roar")
WRITER_CLIFF_SFX = ("cliffhanger", "sting", "stinger", "swell", "ominous", "abrupt", "dramatic hit", "boom")

# Lines that open by replying to something the viewer did not hear.
REPLY_OPENERS = re.compile(
    r"^(?:\.\.\.|…|and\b|but\b|so\b|then\b|because\b|which\b|that's\b|yes\b|no[,.!]|yeah\b|of course\b|"
    r"exactly\b|indeed\b|still\b|also\b|anyway\b|or\b|nor\b|too\b|right\b|okay\b|ok\b|well\b)", re.I)
BARE_PRONOUN_START = re.compile(r"^(?:he|she|they|him|her|them|it|this|that|those|these)\b", re.I)
VAGUE_REFERENCE = re.compile(r"\b(?:it|this|that|him|her|them|they|he|she)\b[.!?…]*$", re.I)
SOFT_LINES = re.compile(
    r"^(?:thank you|thanks|i understand|all right|alright|okay|ok|yes|i know|i see|of course|i forgive you|"
    r"good night|goodbye|we are safe|you are safe|it is over|i love you too|rest now|sleep)\b[.!]?$", re.I)
RESOLUTION_PHRASES = ("i forgive you", "we are safe", "you are safe", "it is over", "it's over", "all is well",
                      "everything is fine", "we can go home", "thank god", "you're safe", "it was nothing")
RELATIONSHIP_WORDS = ("husband", "wife", "sister", "brother", "mother", "father", "son", "daughter", "fiancé",
                      "fiance", "bride", "groom", "wedding", "marry", "married", "family", "duke", "duchess",
                      "maid", "soldier", "king", "queen", "baby", "child")


BARE_REACTION = re.compile(r"^[\w' ]{1,14}(?:\?|\.\.\.|…|!|\.)?$")


def is_bare_reaction(text: str) -> bool:
    """'What?', 'Mother.', 'Viktor...', 'No!' - a reaction that only means something after an unseen line."""
    t = text.strip()
    if content_cues(t):
        return False
    words = re.findall(r"[A-Za-z']+", t)
    only_names = 0 < len(words) <= 3 and all(w[0].isupper() for w in words)  # "Mother... Mara..."
    return only_names or (len(t.split()) <= 2 and bool(BARE_REACTION.match(t)))


def _has(text: str, phrase: str) -> bool:
    """Whole-word match that also accepts simple inflections: 'crash' matches 'crashes'/'crashed'.
    (v2.0 matched exact words only, so 'crash' missed 'beam crashes' and action scenes were under-scored.)"""
    double = re.escape(phrase[-1]) + "(?:ed|ing)|" if phrase[-1].isalpha() else ""  # slap -> slapped
    pattern = r"(?<![a-z])" + re.escape(phrase) + r"(?:" + double + r"s|es|ed|d|ing)?(?![a-z])"
    return re.search(pattern, text) is not None


def emotion_tension(block: Block) -> Tuple[int, str]:
    """Return (+2 high / +1 medium / 0 neutral / -1 low, matched word) from the performance direction."""
    words = [w.strip(" .-").lower() for w in re.split(r"[,/;]| and ", block.emotion) if w.strip()]
    # A list in written order, not a set: set order changes between Python processes
    # (hash randomisation), which made the quoted emotion word non-reproducible.
    tokens = [t for w in words for t in w.split()]
    for word in tokens:
        if word in HIGH_TENSION:
            return 2, word
    for word in tokens:
        if word in MEDIUM_TENSION:
            return 1, word
    for word in tokens:
        if word in LOW_TENSION:
            return -1, word
    return 0, ""


def content_cues(text: str) -> List[str]:
    lower = text.lower()
    cues = []
    if ACCUSATION_RE.search(text):
        cues.append("accusation")
    if any(_has(lower, w) for w in THREAT_WORDS):
        cues.append("threat/danger")
    if any(_has(lower, w) for w in REVEAL_WORDS):
        cues.append("reveal")
    return cues


def tension(block: Block) -> float:
    """0-1 tension of a single beat, used for the clip's tension arc."""
    level, _ = emotion_tension(block)
    value = {2: 0.8, 1: 0.55, 0: 0.4, -1: 0.15}[level]
    text = block.text.lower()
    if block.kind == "dialogue":
        value += 0.1 * len(content_cues(block.text)) + (0.08 if "!" in text else 0)
    elif block.kind == "action" and any(_has(text, w) for w in VIOLENT_ACTION):
        value = max(value, 0.8)
    elif block.kind == "sfx" and any(_has(text, w) for w in LOUD_SFX + WRITER_CLIFF_SFX):
        value = max(value, 0.7)
    return min(1.0, value)


def hook_strength(block: Block) -> Tuple[float, List[str]]:
    """How likely this beat, seen in the first 3 seconds, is to stop a scroll."""
    text = block.text
    lower = text.lower()
    reasons: List[str] = []
    score = 0.0
    if block.kind == "dialogue":
        score = 22
        level, word = emotion_tension(block)
        score += {2: 26, 1: 12, 0: 0, -1: -14}[level]
        if word:
            reasons.append(f"delivered '{word}'")
        cues = content_cues(text)
        score += 16 * len(cues)
        reasons.extend(cues)
        if "!" in text:
            score += 8
        if "?" in text and re.match(r"^(who|what|why|how|where)\b", lower):
            score += 6
            reasons.append("pointed question")
        words = len(text.split())
        if words <= 8:
            score += 8
            reasons.append("short, punchy line")
        elif words > 22:
            score -= 12
            reasons.append("long line (will not land in 3s)")
        if is_bare_reaction(text):
            score -= 24
            reasons.append("bare reaction with no content")
        elif REPLY_OPENERS.match(text):
            score -= 22
            reasons.append("starts as a reply to unseen line")
        elif BARE_PRONOUN_START.match(text) or (VAGUE_REFERENCE.search(text) and words <= 5 and not cues):
            score -= 12
            reasons.append("hinges on an unexplained 'it/that/him'")
        if SOFT_LINES.match(text.strip()):
            score -= 35
            reasons.append("soft/acknowledging line")
    elif block.kind == "action":
        if any(_has(lower, w) for w in VIOLENT_ACTION):
            score = 62
            reasons.append("physical action")
        else:
            score = 15
    elif block.kind == "sfx":
        if any(_has(lower, w) for w in LOUD_SFX):
            score = 55
            reasons.append("loud sound event")
        else:
            score = 8
    return max(0.0, min(100.0, score)), reasons


def cliff_strength(block: Block) -> Tuple[float, List[str]]:
    """How unresolved this beat leaves things, if the clip cuts right after it."""
    text = block.text
    lower = text.lower()
    reasons: List[str] = []
    score = 0.0
    if block.kind == "dialogue":
        score = 18
        level, word = emotion_tension(block)
        score += {2: 20, 1: 10, 0: 0, -1: -15}[level]
        if word:
            reasons.append(f"delivered '{word}'")
        if text.rstrip().endswith("?"):
            score += 24
            reasons.append("unanswered question")
        cues = content_cues(text)
        score += 14 * len(cues)
        reasons.extend(cues)
        if re.search(r"(?:—|--)[\"”]?$", text.strip()):
            score += 16
            reasons.append("line is interrupted")
        if "!" in text:
            score += 6
        if SOFT_LINES.match(text.strip()) or any(_has(lower, p) for p in RESOLUTION_PHRASES):
            score -= 35
            reasons.append("resolving/soft line")
    elif block.kind == "action":
        if any(_has(lower, w) for w in VIOLENT_ACTION):
            score = 55
            reasons.append("ends on physical action")
        else:
            score = 12
    elif block.kind == "sfx":
        if any(_has(lower, w) for w in LOUD_SFX):
            score = 45
            reasons.append("ends on a sound event")
        else:
            score = 10
    return max(0.0, min(100.0, score)), reasons


def is_writer_cliff_cue(block: Block) -> bool:
    return block.kind == "sfx" and any(_has(block.text.lower(), w) for w in WRITER_CLIFF_SFX)


def echoes(line_text: str, previous_text: str) -> bool:
    """'Arrested?' right after 'They arrested her!' only makes sense if you heard the line before."""
    words = re.findall(r"[a-z']+", line_text.lower())
    before = set(re.findall(r"[a-z']+", previous_text.lower()))
    return 0 < len(words) <= 3 and all(w in before for w in words)


def opening_dependency(text: str, earlier_text: str = "") -> List[str]:
    """Reasons a cold viewer would not understand this opening line."""
    problems = []
    if is_bare_reaction(text):
        problems.append("opens on a bare reaction")
    elif REPLY_OPENERS.match(text):
        problems.append("opens as a reply")
    if BARE_PRONOUN_START.match(text) and not re.search(r"\b[A-Z][a-z]{2,}\b", text[3:]):
        problems.append("opens on a pronoun with no named person")
    elif VAGUE_REFERENCE.search(text) and len(text.split()) <= 7 and not re.search(r"\b[A-Z][a-z]{2,}\b", text[1:]):
        problems.append("refers to 'it/that/him' the viewer has not seen")
    return problems
