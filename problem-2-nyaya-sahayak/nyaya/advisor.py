"""Build the reply: case summary, questions, where you stand (cited), options, lawyer triggers, draft notice.

Deterministic by default. Every legal statement comes from kb.py and is cited as [ID].
An optional model may only rewrite the plain-language explanation, and its output is
validated against the knowledge base (see guard.py).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Callable, Dict, List, Optional

from . import kb
from .guard import validate_model_text
from .intake import Facts, classify, contradictions, extract, merge, months_since_problem

DISCLAIMER = ("This is general legal information from a limited, sourced knowledge base, not legal advice. "
              "Laws and rules change and differ by state; confirm with a lawyer or free legal aid (15100) before acting.")

HINDI_NEXT_STEPS = {
    "consumer_refund": "अगले कदम: 1) कंपनी को लिखित में तारीख देकर रिफंड माँगें। 2) राष्ट्रीय उपभोक्ता हेल्पलाइन 1915 पर मुफ्त शिकायत करें। "
                       "3) हल न हो तो जिला उपभोक्ता आयोग में ऑनलाइन शिकायत करें (₹5 लाख तक कोई फीस नहीं)। समय सीमा: 2 साल।",
    "rent_deposit": "अगले कदम: 1) मकान मालिक से लिखित में डिपॉजिट वापसी माँगें। 2) रजिस्टर्ड डाक से लीगल नोटिस भेजें। "
                    "3) जिला विधिक सेवा प्राधिकरण से लोक अदालत में समझौते की कोशिश करें। 4) फिर भी न मिले तो सिविल कोर्ट। मुफ्त कानूनी सहायता: 15100।",
    "unpaid_salary": "अगले कदम: 1) HR को लिखित में बकाया वेतन और तारीख माँगें। 2) जवाब न मिले तो लीगल नोटिस भेजें। "
                     "3) राज्य श्रम विभाग में वेतन संहिता (Code on Wages) के तहत दावा करें — आम तौर पर 3 साल के अंदर। मुफ्त कानूनी सहायता: 15100।",
}


def rupees(v: float) -> str:
    if v >= 1e5:
        return f"Rs {v / 1e5:g} lakh"
    s = f"{int(round(v)):,}"
    return "Rs " + s


@dataclass
class Session:
    today: date = field(default_factory=date.today)
    facts: Optional[Facts] = None
    category: str = ""
    turns: int = 0
    model: Optional[Callable[[str, str], str]] = None
    model_name: str = ""

    def turn(self, text: str) -> Dict[str, Any]:
        text = (text or "").strip()
        if not text:
            return {"type": "ask", "message": "Please describe your problem in a few sentences: what happened, when, "
                    "how much money is involved, and what proof you have.", "disclaimer": DISCLAIMER}
        if len(text) > 8000:
            text = text[:8000]
        new = extract(text, self.today)
        self.facts = new if self.facts is None else merge(self.facts, new)
        self.turns += 1
        cat, _ = classify(self.facts)
        if cat:
            self.category = cat
        return respond(self.facts, self.category, self.today, self.model, self.model_name)


def missing_facts(f: Facts, cat: str) -> List[str]:
    q = []
    claim = {"consumer_refund": "price", "rent_deposit": "deposit", "unpaid_salary": "salary"}[cat]
    has_claim_amount = any(lab == claim for _, lab, _ in f.labeled_amounts) or (
        len(f.amounts) == 1 and not any(lab for _, lab, _ in f.labeled_amounts))
    if not has_claim_amount:
        q.append({"consumer_refund": "How much did you pay (exact amount)?",
                  "rent_deposit": "How much was the security deposit (exact amount)?",
                  "unpaid_salary": "How much salary is unpaid in total, and for which months?"}[cat])
    if not f.dates and not f.months_ago:
        q.append({"consumer_refund": "When did you buy it / when did the problem start (date)?",
                  "rent_deposit": "On what date did you move out and hand back the keys?",
                  "unpaid_salary": "Since when has salary not been paid? Are you still working there?"}[cat])
    if cat in ("rent_deposit", "unpaid_salary") and not f.state:
        q.append("Which state (or city) is this in? Rent and labour rules differ by state.")
    if not f.party:
        q.append({"consumer_refund": "What is the name of the seller/company?",
                  "rent_deposit": "What is the landlord's name and the flat address?",
                  "unpaid_salary": "What is the employer's (company's) name?"}[cat])
    return q


def lawyer_triggers(f: Facts, cat: str, months: Optional[float], amount: Optional[float]) -> List[str]:
    t = []
    if f.emergency:
        t.append("Your safety may be at risk: contact the police (112) first.")
    if f.urgent:
        t.append("There is a deadline/hearing/eviction: speak to a lawyer or legal aid (15100) today.")
    if "notice_received" in f.out_of_scope:
        t.append("You received a notice/summons: replies have strict deadlines; get a lawyer to reply.")
    if amount and amount > 5e5:
        t.append(f"The amount ({rupees(amount)}) is large; a lawyer's review is worth it before filing.")
    limit = 24 if cat == "consumer_refund" else 36
    if months is not None and months >= limit - 3:
        t.append(f"About {months:.0f} months have passed: you may be close to or past the time limit "
                 f"({limit} months). Get advice on condonation of delay quickly.")
    if not f.evidence:
        t.append("You have not mentioned any written proof yet; a lawyer can advise what else counts as evidence.")
    return t


def claim_amount(f: Facts, cat: str) -> Optional[float]:
    if f.partial_claim and cat in ("rent_deposit", "consumer_refund"):
        return f.partial_claim[0]
    if cat == "unpaid_salary" and f.monthly_rate and f.months_unpaid:
        return f.monthly_rate * f.months_unpaid
    claim = {"consumer_refund": "price", "rent_deposit": "deposit", "unpaid_salary": "salary"}[cat]
    vals = [v for v, lab, _ in f.labeled_amounts if lab == claim]
    if len(set(vals)) == 1:
        return vals[0]
    if not vals and len(f.amounts) == 1:
        return f.amounts[0][0]
    return None


def draft_notice(f: Facts, cat: str, amount: Optional[float], today: date) -> str:
    party = f.party or "[NAME OF THE OTHER PARTY]"
    amt = rupees(amount) if amount else "[EXACT AMOUNT]"
    when = (f.dates[0][1] if f.dates else (f.months_ago[0][1] if f.months_ago else "[DATE]"))
    body = {
        "consumer_refund": f"I purchased goods/services from you on {when} for {amt} [ORDER/INVOICE NO.]. "
                           "They were [defective / not delivered / not as promised: DESCRIBE]. Despite my complaints on "
                           "[DATES], you have not refunded or replaced them.",
        "rent_deposit": f"I was your tenant at [FLAT ADDRESS] under an agreement dated [DATE]. I paid a security deposit "
                        f"of {amt}. I vacated and handed over possession on {when} [DATE]. You have not returned the deposit "
                        "and have not given any itemised account of deductions.",
        "unpaid_salary": f"I was employed with you as [DESIGNATION] from [DATE]. My wages of {amt} for [MONTHS] remain unpaid "
                         f"(unpaid since {when}), although wages are due within the time limits under the Code on Wages, 2019.",
    }[cat]
    return (f"LEGAL NOTICE (draft: fill every [BRACKET]; do not send with blanks)\n"
            f"Date: {today.isoformat()}\nTo: {party}\nFrom: [YOUR NAME, ADDRESS, PHONE]\n\n"
            f"Subject: Demand for payment of {amt}\n\n{body}\n\n"
            f"I call upon you to pay {amt} within 15 days of receiving this notice, failing which I will take "
            "appropriate legal action before the competent forum, at your cost and risk.\n\n[SIGNATURE]\n"
            "Send by registered post/speed post with acknowledgement and keep the receipt.")


def respond(f: Facts, cat: str, today: date, model=None, model_name: str = "") -> Dict[str, Any]:
    out: Dict[str, Any] = {"disclaimer": DISCLAIMER, "language": f.language}
    if f.emergency or f.fraud:
        out["safety"] = []
        if f.emergency:
            out["safety"].append(f"If you are in danger, call {kb.EMERGENCY['police_emergency']} now. "
                                 f"Women can also call {kb.EMERGENCY['women_helpline']}.")
        if f.fraud:
            out["safety"].append(f"For online money fraud, call {kb.EMERGENCY['cyber_fraud']}.")
    scope_issues = [s for s in f.out_of_scope if s != "notice_received" or not cat]
    if cat and "counterparty_role" in f.out_of_scope:
        cat = ""  # "I am a landlord, my tenant..." is not the tenant-side claim this tool covers
    if not cat:
        if f.out_of_scope:
            out.update(type="out_of_scope", message=(
                "I can only help in depth with three problems: consumer refunds, rent deposits and unpaid salary. "
                f"Your situation looks like {', '.join(kb.OUT_OF_SCOPE[s] for s in f.out_of_scope)}, which I do not cover. "
                f"Please contact free legal aid soon: {kb.PROVISIONS['NALSA'].says} [NALSA]"), citations=["NALSA"])
        else:
            out.update(type="ask", message=(
                "I'm not sure which kind of problem this is. Is it (1) a refund or defective product/service, "
                "(2) a landlord not returning your deposit, or (3) salary not paid? Tell me in your own words."))
        out["sources"] = sources(out.get("citations", []))
        return out

    c = kb.CATEGORIES[cat]
    amount = claim_amount(f, cat)
    months = months_since_problem(f, today)
    have = sorted(set(f.evidence))
    missing_ev = [label for label, kind in c.evidence if kind not in have]
    questions = contradictions(f, today) + missing_facts(f, cat)
    citations = list(c.provisions) + ["NALSA"]
    stand = [f"{kb.PROVISIONS[p].says} [{p}]" for p in c.provisions]
    if cat == "rent_deposit" and not f.state:
        stand.insert(0, "Rent law is state law. Until you tell me the state, I can only give the general route below.")
    if months is not None:
        limit = 24 if cat == "consumer_refund" else 36
        ref = 'CPA-LIMIT' if cat == 'consumer_refund' else ('COW-45' if cat == 'unpaid_salary' else 'LIMITATION')
        if months > limit:
            stand.insert(0, f"TIME LIMIT WARNING: about {months:.0f} months have passed, which is past the usual limit of "
                            f"{limit} months [{ref}]. A late claim is accepted only if you show sufficient cause for the "
                            "delay. Speak to a lawyer or legal aid (15100) quickly.")
        else:
            stand.insert(0, f"Time check: about {months:.0f} months have passed; the usual limit is {limit} months [{ref}].")
    summary = {
        "problem": c.name,
        "amount_claimed": rupees(amount) if amount else "not clear yet",
        "when": ", ".join(s for _, s in f.dates) or ", ".join(s for _, s in f.months_ago) or "not given",
        "where": f"{f.state.title()} (from '{f.state_source}')" if f.state else "not given",
        "against": f.party or "not given",
        "proof_you_mentioned": have or ["none yet"],
        "proof_that_would_help": missing_ev,
        "you_said_you_do_not_have": f.evidence_missing_said,
    }
    out.update(type="advice", category=cat, case_summary=summary, questions=questions, where_you_stand=stand,
               options=c.steps, see_a_lawyer_if=lawyer_triggers(f, cat, months, amount),
               draft_notice=draft_notice(f, cat, amount, today), citations=citations, sources=sources(citations))
    calc = []
    if cat == "unpaid_salary" and f.monthly_rate and f.months_unpaid:
        calc.append(f"I calculated {rupees(f.monthly_rate)} per month x {f.months_unpaid} months = {rupees(amount)}. "
                    "Is that the full amount owed (any deductions or partial payments)?")
    elif cat == "unpaid_salary" and f.months_unpaid and not f.monthly_rate and amount:
        calc.append(f"Is {rupees(amount)} your monthly salary or the total owed for the {f.months_unpaid} months? "
                    "The notice must state the total.")
    elif cat == "unpaid_salary" and f.monthly_rate and not f.months_unpaid:
        calc.append("For how many months is the salary unpaid? I need the total, not the monthly rate.")
    if f.partial_claim and cat in ("rent_deposit", "consumer_refund"):
        calc.append(f"From '{f.partial_claim[1]}', I took the withheld amount as {rupees(f.partial_claim[0])}. Is that right?")
    out["questions"] = calc + out["questions"]
    if cat == "unpaid_salary" and f.government:
        out["see_a_lawyer_if"].append("You mentioned a government job: government employees are often covered by separate "
                                      "service rules, so the wage-claim route above may not apply. Check with legal aid (15100) first.")
    if scope_issues:
        out["also_noted"] = [f"Part of your message sounds like {kb.OUT_OF_SCOPE[s]}; I don't cover that. "
                             "Please contact legal aid (15100)." for s in scope_issues]
    if f.language in ("hi", "hinglish"):
        out["hindi_summary"] = HINDI_NEXT_STEPS[cat]
    if model is not None:
        out["plain_explanation"], out["model_check"] = model_explanation(model, model_name, f, out)
    return out


def sources(ids: List[str]) -> List[Dict[str, str]]:
    return [{"id": i, "law": kb.PROVISIONS[i].law, "ref": kb.PROVISIONS[i].ref, "verification": kb.PROVISIONS[i].verification,
             "url": kb.PROVISIONS[i].sources[0], "caveat": kb.PROVISIONS[i].caveat} for i in ids if i in kb.PROVISIONS]


def model_explanation(model, model_name: str, f: Facts, out: Dict[str, Any]):
    """Ask the model to explain the cited points simply, in the user's language. Validate, else fall back."""
    allowed = {i: kb.PROVISIONS[i].says for i in out["citations"]}
    lang = {"hi": "Hindi (Devanagari)", "hinglish": "simple Hinglish", "en": "simple English"}[f.language]
    system = ("You explain Indian legal information to a non-lawyer. Use ONLY the numbered facts given; cite them as [ID]. "
              "Never mention any law, section, article, case or amount that is not in the facts or the user's story. "
              "If something is unknown, say so. 120 words max. Write in " + lang + ".")
    user = ("FACTS:\n" + "\n".join(f"[{k}] {v}" for k, v in allowed.items()) + "\n\nUSER STORY:\n" + "\n".join(f.raw)
            + "\n\nCASE SUMMARY:\n" + str(out["case_summary"]))
    try:
        text = model(system, user)
    except Exception as exc:  # network/quota: the deterministic answer above is complete on its own
        return None, {"used": False, "reason": f"model error: {str(exc)[:200]}"}
    ok, problems = validate_model_text(text, set(allowed), f)
    if not ok:
        return None, {"used": False, "reason": "rejected: " + "; ".join(problems), "model": model_name}
    return text.strip(), {"used": True, "model": model_name}


def render(resp: Dict[str, Any]) -> str:
    """Plain-text rendering for the CLI and transcripts."""
    lines: List[str] = []
    for s in resp.get("safety", []):
        lines.append("!! " + s)
    if resp["type"] != "advice":
        lines.append(resp["message"])
    else:
        s = resp["case_summary"]
        lines += ["CASE SUMMARY", f"  Problem: {s['problem']}", f"  Amount: {s['amount_claimed']}", f"  When: {s['when']}",
                  f"  Where: {s['where']}", f"  Against: {s['against']}", f"  Proof you mentioned: {', '.join(s['proof_you_mentioned'])}",
                  f"  Proof that would help: {', '.join(s['proof_that_would_help']) or 'nothing obvious missing'}"]
        if resp["questions"]:
            lines += ["", "I NEED TO KNOW"] + [f"  - {q}" for q in resp["questions"]]
        if resp.get("plain_explanation"):
            lines += ["", "IN SIMPLE WORDS (model, checked against sources)", "  " + resp["plain_explanation"]]
        lines += ["", "WHERE YOU STAND"] + [f"  - {x}" for x in resp["where_you_stand"]]
        lines += ["", "WHAT YOU CAN DO"] + [f"  {i}. {x}" for i, x in enumerate(resp["options"], 1)]
        if resp["see_a_lawyer_if"]:
            lines += ["", "GET A LAWYER / LEGAL AID BECAUSE"] + [f"  - {x}" for x in resp["see_a_lawyer_if"]]
        for a in resp.get("also_noted", []):
            lines.append("NOTE: " + a)
        if resp.get("hindi_summary"):
            lines += ["", resp["hindi_summary"]]
        lines += ["", resp["draft_notice"]]
    if resp.get("sources"):
        lines += ["", "SOURCES"] + [f"  [{x['id']}] {x['law']}, {x['ref']} ({x['verification']}): {x['url']}" for x in resp["sources"]]
    lines += ["", resp["disclaimer"]]
    return "\n".join(lines)
