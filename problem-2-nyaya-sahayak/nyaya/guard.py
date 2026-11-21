"""Anti-hallucination guard for model text.

Rules (any failure -> the model text is discarded and only the sourced, deterministic answer is shown):
  1. Every [ID] citation must be one of the IDs supplied for this answer.
  2. No legal reference that is not in the knowledge base: 'Section 420', 'Article 21', 'IPC', 'BNS',
     'X v. Y', or any '<Name> Act, <year>' not among the supplied provisions.
  3. No rupee amount that the user did not state.
  4. Must not promise outcomes ("you will win", "guaranteed").
"""

from __future__ import annotations

import re
from typing import List, Set, Tuple

from . import kb
from .intake import AMOUNT_RE, Facts, parse_amount

LEGAL_REF = re.compile(
    r"\b(?:section|sec\.|s\.|article|art\.|rule|clause|धारा|अनुच्छेद)\s*\d+[A-Z]?\b"
    r"|\border\s+(?:[IVXLC]{2,}|\d+)\b"
    r"|\b(?:IPC|BNS|BNSS|CrPC|CPC|Indian Penal Code|Bharatiya Nyaya Sanhita)\b"
    r"|\b[A-Z][a-z]+\s+(?:v\.|vs\.?|versus)\s+[A-Z][a-z]+"
    r"|\b(?:[A-Z][a-z]+\s+){1,5}Act,?\s+\d{4}", re.I)
PROMISE = re.compile(r"\b(you will (?:definitely )?win|guarantee[ds]?|100% sure|certainly win|sure to win)\b", re.I)


def _allowed_refs(ids: Set[str]) -> List[str]:
    out = []
    for i in ids:
        p = kb.PROVISIONS[i]
        out.append((p.law + " " + p.ref).lower())
    return out


def validate_model_text(text: str, allowed_ids: Set[str], facts: Facts) -> Tuple[bool, List[str]]:
    problems: List[str] = []
    if not text or not text.strip():
        return False, ["empty reply"]
    cited = set(re.findall(r"\[([A-Z][A-Z0-9-]+)\]", text))
    bad = cited - allowed_ids
    if bad:
        problems.append(f"cites unknown source(s) {sorted(bad)}")
    allowed_text = " ".join(_allowed_refs(allowed_ids))
    for m in LEGAL_REF.finditer(re.sub(r"\[[A-Z][A-Z0-9-]+\]", " ", text)):  # citation tags are not references
        ref = re.sub(r"\s+", " ", m.group(0).lower().replace("sec.", "section"))
        if re.search(r"\bact,?\s+\d{4}$", ref):
            # "the Consumer Protection Act, 2019" is fine; "Fake Protection Act, 2019" is not: the match must END
            # with a full law name from the supplied provisions.
            laws = [kb.PROVISIONS[i].law.lower().split(" (")[0].split(" + ")[0] for i in allowed_ids]
            ok = any(ref.replace(",", "").endswith(law.replace(",", "")) for law in laws)
        else:
            ok = ref in allowed_text
        if not ok:
            problems.append(f"mentions legal reference not in sources: '{m.group(0)}'")
    user_amounts = [v for v, _ in facts.amounts]
    for m in AMOUNT_RE.finditer(text):
        num, unit = (m.group(1), m.group(2)) if m.group(1) else ((m.group(3), m.group(4)) if m.group(3) else (m.group(5), m.group(6)))
        v = parse_amount(num, unit)
        kb_amounts = {5e5, 50e5, 2e7}  # thresholds stated in the knowledge base
        if v is not None and not any(abs(v - u) < 1 for u in user_amounts) and v not in kb_amounts:
            problems.append(f"states an amount the user never gave: '{m.group(0)}'")
    if PROMISE.search(text):
        problems.append("promises an outcome")
    return not problems, problems
