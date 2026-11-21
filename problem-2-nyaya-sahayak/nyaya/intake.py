"""Turn a messy story into structured facts. Deterministic; no model needed.

Handles English, Hindi (Devanagari) and Hinglish keywords. Everything extracted keeps the
exact text span it came from, so the case summary can show the user what was understood.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from typing import Dict, List, Optional, Tuple

KEYWORDS: Dict[str, List[str]] = {
    "consumer_refund": ["refund", "return", "defective", "damaged", "broken", "order", "delivered", "delivery",
                        "product", "warranty", "service centre", "service center", "replacement", "seller",
                        "wrong item", "cancelled", "canceled", "booking", "e-commerce", "online shopping", "customer care",
                        "रिफंड", "खराब", "ऑर्डर", "सामान", "वापसी", "paisa wapas", "refund nahi"],
    "rent_deposit": ["deposit", "landlord", "landlady", "tenant", "rent", "flat", "vacated", "moved out", "move out",
                     "house owner", "owner of the house", "pg", "lease", "rent agreement", "security amount",
                     "मकान मालिक", "किराया", "किराए", "जमा", "डिपॉजिट", "makan malik", "kiraya", "kirayedar"],
    "unpaid_salary": ["salary", "wages", "wage", "employer", "payslip", "pay slip", "full and final", "f&f",
                      "hr ", "resigned", "resignation", "notice period", "not paid me", "unpaid", "terminated",
                      "fired", "boss", "company is not paying", "stipend",
                      "तनख्वाह", "वेतन", "सैलरी", "मजदूरी", "tankhwah", "salary nahi", "pagar"],
}
OUT_OF_SCOPE_KEYWORDS: Dict[str, List[str]] = {
    "criminal": ["arrested", "arrest", "fir", "bail", "police station", "assault", "murder", "theft", "stolen",
                 "jail", "गिरफ्तार", "एफआईआर"],
    "family": ["divorce", "custody", "maintenance", "dowry", "alimony", "domestic violence", "in-laws",
               "तलाक", "दहेज"],
    "property_title": ["inheritance", "ancestral", "land dispute", "partition", "property papers", "will of",
                       "mutation", "encroach", "जमीन", "वसीयत"],
    "notice_received": ["received a notice", "got a notice", "summons", "court notice", "legal notice from",
                        "notice from court", "notice from my"],
    "harassment": ["sexually harassed", "sexual harassment", "harassed me", "harassing me", "molested", "groped",
                   "inappropriate touching"],
    "cheque_bounce": ["cheque bounced", "cheque bounce", "bounced cheque", "cheque was dishonoured", "cheque dishonoured",
                      "cheque got bounced", "check bounced"],
    "insurance": ["insurance", "insurer", "policy claim", "claim was rejected", "rejected my claim", "claim rejected"],
    "loan_banking": ["loan", "emi", "recovery agent", "credit card", "account frozen", "cibil"],
    "counterparty_role": [],  # filled by role detection below
}
ROLE_RE = re.compile(r"\b(?:i am|i'm|we are)\s+(?:a|an|the)\s+(?:landlord|landlady|house owner|owner of the flat|employer|"
                     r"shop owner|seller|business owner)\b|\bmy (?:tenant|tenants|employee|employees|customer|customers)\b", re.I)
NEGATION = re.compile(r"\b(?:not|never|no|didn't|did not|doesn't|does not|nobody|no one|without)\b[^.!?;,]{0,30}$", re.I)
PAST_AFTER = re.compile(r"^\s*(?:\w+\s+){0,2}?(?:was|were|had been|happened|ended|is over|took place)\b", re.I)
PAST_ANYWHERE = re.compile(r"\b(?:last (?:year|month|week)|years? ago|months? ago|already over)\b", re.I)
RATE_RE = re.compile(r"(?:per month|a month|/month|monthly|per mensem|p\.m\.|every month|mahina)", re.I)
MONTHS_UNPAID_RE = re.compile(r"\b(?:for|since|past|last)\s+(\d+|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)\s+months?\b"
                              r"|\b(\d+|two|three|four|five|six)\s+months?(?:'|’)?\s+(?:salary|wages|pay)\b"
                              r"|\b(\d+)\s+months?\s+se\b", re.I)
PARTIAL_RE = re.compile(r"(?:returned|refunded|gave back|paid back|given back)\s+(?:only\s+)?(?P<a>(?:rs\.?|inr|₹)?\s*[\d,]+(?:\s*k)?)"
                        r"\s+(?:out\s+)?of\s+(?:my|the|our)?\s*(?P<b>(?:rs\.?|inr|₹)?\s*[\d,]+(?:\s*k)?)", re.I)
DEDUCT_RE = re.compile(r"(?:deducted|cut|kept|withheld)\s+(?P<a>(?:rs\.?|inr|₹)?\s*[\d,]+(?:\s*k)?)\s+(?:from|out of)\s+(?:my|the|our)?\s*"
                       r"(?P<b>(?:rs\.?|inr|₹)?\s*[\d,]+(?:\s*k)?)", re.I)


def _plain_amount(s: str) -> Optional[float]:
    m = re.search(r"([\d,]+(?:\.\d+)?)\s*(k)?", s, re.I)
    return parse_amount(m.group(1), m.group(2)) if m else None


def _affirmed(text: str, word: str) -> bool:
    """True if `word` occurs in a clause that is neither negated ("did not hit me") nor about the past
    ("the hearing was last year"). Used for safety and urgency triggers."""
    for m in re.finditer(r"(?<![a-z])" + re.escape(word) + r"(?:s|es|ed|ing|ly)?(?![a-z])", text):
        before = text[max(0, m.start() - 40):m.start()]
        clause_start = max(before.rfind(c) for c in ".!?;") + 1
        clause = text[max(0, m.start() - 40) + clause_start: text.find(".", m.end()) if text.find(".", m.end()) != -1 else len(text)]
        if NEGATION.search(before[clause_start:]):
            continue
        return True
    return False
EMERGENCY_WORDS = ["beat me", "beating me", "hit me", "hits me", "threatened to kill", "kill me", "attack",
                   "unsafe", "locked me", "suicide", "end my life", "hurt myself", "sexual", "molest",
                   "threatening me", "goons", "मारा", "मारता", "धमकी"]
URGENT_WORDS = ["hearing", "court date", "deadline", "evict", "eviction", "thrown out", "changed the locks",
                "throw me out", "within 24 hours", "summons", "last date", "sunwai", "सुनवाई"]
FRAUD_WORDS = ["otp", "upi fraud", "scam", "fraud", "money debited", "unknown transaction", "hacked", "phishing"]

EVIDENCE_WORDS = {
    "written agreement": ["agreement", "contract", "lease", "allotment letter", "एग्रीमेंट", "अनुबंध"],
    "receipt/invoice": ["receipt", "invoice", "bill", "order id", "order number", "order confirmation", "रसीद", "बिल"],
    "bank/UPI proof": ["bank transfer", "upi", "gpay", "google pay", "phonepe", "paytm", "neft", "imps", "bank statement",
                       "cheque", "card statement", "paid online", "transferred"],
    "messages/emails": ["whatsapp", "email", "e-mail", "chat", "sms", "messages", "screenshot", "mail"],
    "photos/video": ["photo", "picture", "video", "photos"],
    "salary slips/offer letter": ["payslip", "pay slip", "salary slip", "offer letter", "appointment letter",
                                  "relieving letter"],
    "witness": ["witness", "neighbour saw", "neighbor saw", "colleague saw"],
}
NO_EVIDENCE = re.compile(r"\b(?:no|don't have|do not have|didn't get|did not get|never got|without|nahi hai|नहीं है)\b"
                         r"[^.;]*?(?=\bbut\b|[.;]|$)", re.I)

STATES = ["andhra pradesh", "arunachal pradesh", "assam", "bihar", "chhattisgarh", "goa", "gujarat", "haryana",
          "himachal pradesh", "jharkhand", "karnataka", "kerala", "madhya pradesh", "maharashtra", "manipur",
          "meghalaya", "mizoram", "nagaland", "odisha", "punjab", "rajasthan", "sikkim", "tamil nadu", "telangana",
          "tripura", "uttar pradesh", "uttarakhand", "west bengal", "delhi", "jammu and kashmir", "ladakh",
          "chandigarh", "puducherry"]
CITY_STATE = {"mumbai": "maharashtra", "pune": "maharashtra", "nagpur": "maharashtra", "bengaluru": "karnataka",
              "bangalore": "karnataka", "mysuru": "karnataka", "chennai": "tamil nadu", "coimbatore": "tamil nadu",
              "hyderabad": "telangana", "kolkata": "west bengal", "ahmedabad": "gujarat", "surat": "gujarat",
              "jaipur": "rajasthan", "lucknow": "uttar pradesh", "noida": "uttar pradesh", "ghaziabad": "uttar pradesh",
              "kanpur": "uttar pradesh", "gurgaon": "haryana", "gurugram": "haryana", "faridabad": "haryana",
              "patna": "bihar", "bhopal": "madhya pradesh", "indore": "madhya pradesh", "kochi": "kerala",
              "thiruvananthapuram": "kerala", "bhubaneswar": "odisha", "guwahati": "assam", "dehradun": "uttarakhand",
              "new delhi": "delhi", "chandigarh": "chandigarh", "visakhapatnam": "andhra pradesh",
              "लखनऊ": "uttar pradesh", "दिल्ली": "delhi", "मुंबई": "maharashtra", "पुणे": "maharashtra",
              "जयपुर": "rajasthan", "पटना": "bihar", "भोपाल": "madhya pradesh", "इंदौर": "madhya pradesh",
              "नोएडा": "uttar pradesh", "कानपुर": "uttar pradesh", "बेंगलुरु": "karnataka", "हैदराबाद": "telangana",
              "कोलकाता": "west bengal", "चेन्नई": "tamil nadu", "अहमदाबाद": "gujarat", "गुरुग्राम": "haryana"}
HINDI_AGO_RE = re.compile(r"(\d+)\s*(दिन|हफ्ते|हफ़्ते|सप्ताह|महीने|महीना|माह|साल|वर्ष)\s*(?:पहले|से)")
HINDI_UNIT = {"दिन": 1 / 30, "हफ्ते": 0.25, "हफ़्ते": 0.25, "सप्ताह": 0.25, "महीने": 1, "महीना": 1, "माह": 1, "साल": 12, "वर्ष": 12}
MONTHS = {m: i for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july", "august",
                                      "september", "october", "november", "december"], 1)}
MONTHS.update({m[:3]: i for m, i in list(MONTHS.items())})

AMOUNT_RE = re.compile(
    r"(?:(?:rs\.?|inr|₹)\s*([\d,]+(?:\.\d+)?)\s*(k|thousand|lakh|lakhs|lac|crore)?)|"
    r"(?:\b([\d,]+(?:\.\d+)?)\s*(k|thousand|lakh|lakhs|lac|crore)?\s*(?:rs\b|rupees|inr|₹|रुपये|rupaye))|"
    r"(?:\b([\d,]+(?:\.\d+)?)\s*(lakh|lakhs|lac|crore|k)\b)", re.I)
DATE_NUM_RE = re.compile(r"\b(\d{1,2})[/.-](\d{1,2})[/.-](\d{2,4})\b")
DATE_TXT_RE = re.compile(r"\b(?:(\d{1,2})(?:st|nd|rd|th)?\s+)?(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)"
                         r"[a-z]*\.?,?\s+(\d{4})\b", re.I)
AGO_RE = re.compile(r"\b(\d+|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)\s+"
                    r"(day|week|month|year)s?\s+(?:ago|back|since|before)\b", re.I)
SINCE_RE = re.compile(r"\b(?:for|since|past|last)\s+(\d+|one|two|three|four|five|six)\s+(month|year|week)s?\b", re.I)
WORDNUM = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
           "ten": 10, "eleven": 11, "twelve": 12}


@dataclass
class Facts:
    category: str = ""
    category_scores: Dict[str, int] = field(default_factory=dict)
    out_of_scope: List[str] = field(default_factory=list)
    language: str = "en"
    amounts: List[Tuple[float, str]] = field(default_factory=list)
    labeled_amounts: List[Tuple[float, str, str]] = field(default_factory=list)  # (value, label, span)
    dates: List[Tuple[date, str]] = field(default_factory=list)
    months_ago: List[Tuple[float, str]] = field(default_factory=list)
    state: str = ""
    state_source: str = ""
    evidence: List[str] = field(default_factory=list)
    evidence_missing_said: List[str] = field(default_factory=list)
    emergency: List[str] = field(default_factory=list)
    urgent: List[str] = field(default_factory=list)
    fraud: List[str] = field(default_factory=list)
    party: str = ""
    monthly_rate: Optional[float] = None
    months_unpaid: Optional[int] = None
    partial_claim: Optional[Tuple[float, str]] = None  # (amount actually withheld, explanation)
    government: bool = False
    raw: List[str] = field(default_factory=list)


def _contains(text: str, word: str) -> bool:
    if re.search(r"[ऀ-ॿ]", word):
        return word in text
    w = word.strip()
    plural = "(?:s|es)?" if w[-1:].isalpha() else ""  # "receipts", "photos"
    return re.search(r"(?<![a-z])" + re.escape(w) + plural + r"(?![a-z])", text) is not None


def parse_amount(num: str, unit: Optional[str]) -> Optional[float]:
    try:
        value = float(num.replace(",", ""))
    except ValueError:
        return None
    unit = (unit or "").lower()
    value *= {"k": 1e3, "thousand": 1e3, "lakh": 1e5, "lakhs": 1e5, "lac": 1e5, "crore": 1e7}.get(unit, 1)
    return value if value >= 1 else None


def extract(text: str, today: date) -> Facts:
    f = Facts(raw=[text])
    lower = " " + text.lower() + " "
    if re.search(r"[ऀ-ॿ]", text):
        f.language = "hi"
    elif re.search(r"\b(mera|meri|nahi|nahin|paisa|wapas|hai|kya|karu|mujhe|unhone|abhi)\b", lower):
        f.language = "hinglish"

    for cat, words in KEYWORDS.items():
        f.category_scores[cat] = sum(1 for w in words if _contains(lower, w))
    for cat, words in OUT_OF_SCOPE_KEYWORDS.items():
        if any(_contains(lower, w) for w in words):
            f.out_of_scope.append(cat)
    f.emergency = [w for w in EMERGENCY_WORDS if _affirmed(lower, w)]
    # urgency only if the clause is not negated and not in the past ("the hearing was last year")
    f.urgent = []
    for w in URGENT_WORDS:
        for clause in re.split(r"[.!?;]", lower):
            m = re.search(r"(?<![a-z])" + re.escape(w), clause)
            # "the hearing was last year" is not urgent; "changed the locks today while I was at work" is
            if m and _affirmed(clause, w) and not PAST_AFTER.search(clause[m.end():]) and not PAST_ANYWHERE.search(clause):
                f.urgent.append(w)
                break
    if "harassment" in f.out_of_scope and "sexual" not in f.emergency:
        f.emergency.append("sexual harassment")
    if re.search(r"\bcheque\b[^.]{0,60}\b(?:bounced|bounce|dishonou?red|returned unpaid)\b", lower) and "cheque_bounce" not in f.out_of_scope:
        f.out_of_scope.append("cheque_bounce")
    if ROLE_RE.search(text):
        f.out_of_scope.append("counterparty_role")
    f.government = bool(re.search(r"\b(?:government|govt|sarkari|public sector|psu)\b", lower))
    f.fraud = [w for w in FRAUD_WORDS if _contains(lower, w)]

    for m in AMOUNT_RE.finditer(text):
        num, unit = (m.group(1), m.group(2)) if m.group(1) else ((m.group(3), m.group(4)) if m.group(3) else (m.group(5), m.group(6)))
        value = parse_amount(num, unit)
        if value is None:
            continue
        label = _amount_label(text, m.start(), m.end())
        if not any(abs(value - v) < 0.5 and lab == label for v, lab, _ in f.labeled_amounts):
            f.labeled_amounts.append((value, label, m.group(0).strip()))
        if not any(abs(value - v) < 0.5 for v, _ in f.amounts):
            f.amounts.append((value, m.group(0).strip()))

    for v, lab, span in f.labeled_amounts:
        i = text.find(span)
        if lab == "salary" and i != -1 and RATE_RE.search(text[i:i + len(span) + 25]):
            f.monthly_rate = v
    mm = MONTHS_UNPAID_RE.search(text)
    if mm:
        g = next(x for x in mm.groups() if x)
        f.months_unpaid = int(g) if g.isdigit() else WORDNUM.get(g.lower())
    pm = PARTIAL_RE.search(text) or DEDUCT_RE.search(text)
    if pm:
        a, b = _plain_amount(pm.group("a")), _plain_amount(pm.group("b"))
        if a and b and a < b:
            withheld = b - a if pm.re is PARTIAL_RE else a
            f.partial_claim = (withheld, pm.group(0).strip())

    for m in DATE_NUM_RE.finditer(text):
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        y = y + 2000 if y < 100 else y
        try:
            f.dates.append((date(y, mo, d), m.group(0)))
        except ValueError:
            pass
    for m in DATE_TXT_RE.finditer(text):
        mo = MONTHS.get(m.group(2).lower()[:3])
        try:
            f.dates.append((date(int(m.group(3)), mo, int(m.group(1) or 1)), m.group(0)))
        except (ValueError, TypeError):
            pass
    for rx in (AGO_RE, SINCE_RE):
        for m in rx.finditer(text):
            g = m.group(1).lower()
            n = int(g) if g.isdigit() else WORDNUM.get(g, 1)
            unit = m.group(2).lower()
            months = n * {"day": 1 / 30, "week": 0.25, "month": 1, "year": 12}[unit]
            f.months_ago.append((months, m.group(0)))

    for m in HINDI_AGO_RE.finditer(text):
        f.months_ago.append((int(m.group(1)) * HINDI_UNIT[m.group(2)], m.group(0)))

    for s in STATES:
        if _contains(lower, s):
            f.state, f.state_source = s, s
            break
    if not f.state:
        for city, s in CITY_STATE.items():
            if _contains(lower, city):
                f.state, f.state_source = s, city
                break

    for kind, words in EVIDENCE_WORDS.items():
        if any(_contains(lower, w) for w in words):
            f.evidence.append(kind)
    for m in NO_EVIDENCE.finditer(text):
        clause = " " + m.group(0).lower() + " "
        negated = [k for k, words in EVIDENCE_WORDS.items() if any(_contains(clause, w) for w in words)]
        if negated:
            # "I don't have any agreement or receipt" must not count as having either
            f.evidence_missing_said.append(m.group(0).strip())
            f.evidence = [k for k in f.evidence if k not in negated]

    named = re.search(r"\b(?:landlord|landlady|owner|employer|company|seller|builder)(?:'s name)?\s+(?:is|was|name is)\s+"
                      r"((?:Mr\.?|Mrs\.?|Ms\.?|Shri|Smt\.?)?\s*(?:[A-Z][\w&.]+\s?){1,4})", text)
    party = named or re.search(r"\b(?:from|by|at|with|against)\s+((?:[A-Z][\w&.]+\s?){1,4}?)(?=[\s,.]|$)", text)
    if party and party.group(1).strip().lower() not in {"i", "my", "the", "mr", "it"}:
        f.party = party.group(1).strip().rstrip(".")
    return f


AMOUNT_LABELS = {"deposit": ["deposit", "security", "advance", "जमा", "डिपॉजिट"], "rent": ["rent", "kiraya", "किराया"],
                 "salary": ["salary", "wage", "wages", "pay ", "dues", "f&f", "full and final", "सैलरी", "वेतन"],
                 "price": ["paid", "price", "cost", "bought", "order", "refund", "worth", "rupaye"]}


def _amount_label(text: str, start: int, end: int) -> str:
    """Which money is this? Look at the nearest label word within 40 characters."""
    lower = text.lower()
    best, best_d = "", 41
    for label, words in AMOUNT_LABELS.items():
        for w in words:
            for m in re.finditer(re.escape(w), lower[max(0, start - 40): end + 40]):
                pos = max(0, start - 40) + m.start()
                d = min(abs(pos - start), abs(pos - end))
                if d < best_d:
                    best, best_d = label, d
    return best


def merge(old: Facts, new: Facts) -> Facts:
    """Combine a follow-up turn with what we already knew. New, conflicting values are kept, not overwritten,
    so the contradiction check can ask the user."""
    out = Facts(**{k: v for k, v in old.__dict__.items()})
    out.raw = old.raw + new.raw
    for key in ("amounts", "labeled_amounts", "dates", "months_ago", "evidence", "evidence_missing_said", "emergency", "urgent",
                "fraud", "out_of_scope"):
        merged = list(getattr(old, key))
        for item in getattr(new, key):
            if item not in merged:
                merged.append(item)
        setattr(out, key, merged)
    out.category_scores = {k: old.category_scores.get(k, 0) + new.category_scores.get(k, 0)
                           for k in set(old.category_scores) | set(new.category_scores)}
    out.state = new.state or old.state
    out.state_source = new.state_source or old.state_source
    out.party = new.party or old.party
    out.language = old.language if old.language != "en" else new.language
    return out


def classify(f: Facts) -> Tuple[str, float]:
    """Return (category or '' if unclear, margin). Ties and weak signals return '' so the assistant asks."""
    ranked = sorted(f.category_scores.items(), key=lambda kv: (-kv[1], kv[0]))
    if not ranked or ranked[0][1] == 0:
        return "", 0.0
    top, score = ranked[0]
    second = ranked[1][1] if len(ranked) > 1 else 0
    if score == second:
        return "", 0.0
    return top, (score - second) / max(1, score)


def contradictions(f: Facts, today: date) -> List[str]:
    issues = []
    if f.partial_claim:
        return [i for i in _date_issues(f, today)]
    # Different amounts are normal (rent vs deposit). Two DIFFERENT values for the SAME thing are not.
    by_label: Dict[str, List[Tuple[float, str]]] = {}
    for value, label, span in f.labeled_amounts:
        if label in ("deposit", "salary", "price") and value >= 100:
            by_label.setdefault(label, [])
            if not any(abs(value - v) < 0.5 for v, _ in by_label[label]):
                by_label[label].append((value, span))
    for label, vals in by_label.items():
        if len(vals) >= 2:
            issues.append(f"You gave different amounts for the {label}: {', '.join(s for _, s in vals)}. "
                          "Which one is correct? The notice must state one exact figure.")
    return issues + _date_issues(f, today)


def _date_issues(f: Facts, today: date) -> List[str]:
    issues = []
    for d, span in f.dates:
        if d > today:
            issues.append(f"The date '{span}' is in the future. Did you mean a different date?")
    if len(f.dates) >= 2:
        ds = sorted(f.dates)
        if (ds[-1][0] - ds[0][0]).days > 365 * 20:
            issues.append("The dates you gave are more than 20 years apart. Please check them.")
    return issues


def months_since_problem(f: Facts, today: date) -> Optional[float]:
    candidates = [((today - d).days / 30.4) for d, _ in f.dates if d <= today]
    candidates += [m for m, _ in f.months_ago]
    return max(candidates) if candidates else None
