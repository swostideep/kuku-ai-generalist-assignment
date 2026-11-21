"""The ONLY legal statements the assistant may make.

Every entry has a source URL and how it was checked. The assistant cannot cite a
provision that is not in this file: deterministic answers are built from these entries,
and model output that mentions any section/Act not listed here is rejected.

Verification levels:
  official   - read on a government page (gov.in / nic.in)
  secondary  - consistent across >=2 reputable secondary sources (law firms, LiveLaw, PIB summaries);
               the official text should be re-checked before production use
  general    - a long-standing provision stated only at a general level; its text was NOT re-fetched in
               this build (link is the India Code search page). Lowest confidence: phrased with "generally".
Last checked: 2026-11-21. Law changes: this file needs an owner and a review date.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

LAST_CHECKED = "2026-11-21"


@dataclass(frozen=True)
class Provision:
    id: str
    law: str
    ref: str
    says: str  # plain-language statement, deliberately conservative
    sources: tuple
    verification: str
    caveat: str = ""


PROVISIONS: Dict[str, Provision] = {p.id: p for p in [
    # ---------------- Consumer ----------------
    Provision(
        "CPA-LIMIT", "Consumer Protection Act, 2019", "Section 69",
        "A consumer complaint should be filed within 2 years from the date the problem (cause of action) arose. "
        "A Commission can accept a late complaint only if you show sufficient cause for the delay.",
        ("https://www.advocatekhoj.com/library/bareacts/consumerprotection2019/69.php",
         "https://www.indiacode.nic.in/"), "secondary"),
    Provision(
        "CPA-FORUM", "Consumer Protection Act, 2019 + Jurisdiction Rules, 2021", "Section 34 and 2021 Rules",
        "The District Consumer Commission hears complaints where the price paid for the goods or service is up to "
        "Rs 50 lakh; the State Commission above Rs 50 lakh up to Rs 2 crore; the National Commission above Rs 2 crore. "
        "The limit depends on the amount you paid, not the compensation you ask for.",
        ("https://theprint.in/economy/govt-notifies-new-rules-for-consumer-commissions-national-bodys-jurisdiction-enhanced/791753",
         "https://www.livelaw.in/supreme-court/rutu-mihir-panchal-consumer-protection-act-2019-fixing-pecuniary-jurisdiction-on-value-consideration-constitutional-supreme-court-290743"),
        "secondary"),
    Provision(
        "CPA-FEE", "Consumer Commission fee rules", "Fee schedule",
        "Filing at the District Commission has no fee when the amount involved is up to Rs 5 lakh. Above that a "
        "fee applies; check the current schedule on the official portal.",
        ("https://consumerhelpline.gov.in/public/about", "https://www.sansalegal.com/post/how-to-file-a-consumer-complaint-online-in-india-through-e-daakhil"),
        "secondary", "Fee brackets above Rs 5 lakh differ between sources; not stated by this tool."),
    Provision(
        "NCH", "National Consumer Helpline (Department of Consumer Affairs)", "Helpline 1915",
        "You can register a grievance free of charge by calling 1915 or on consumerhelpline.gov.in (also WhatsApp "
        "8800001915). The helpline takes it up with the company; it can take up to about 30 days.",
        ("https://consumerhelpline.gov.in/public/about",), "official"),
    Provision(
        "EFILE", "Consumer commissions online filing", "e-Daakhil / e-Jagriti",
        "Consumer complaints can be filed online through the government's consumer commission portal (e-Daakhil). "
        "Reports say filing is moving to e-Jagriti; check consumeraffairs.nic.in for the current address.",
        ("https://www.drishtiias.com/daily-updates/daily-news-analysis/consumer-protection-rules-2021",
         "https://righttoinformation.wiki/edaakhil-online-consumer-commission-filing-india"),
        "secondary", "Portal name/address may have changed; the tool tells the user to check."),
    # ---------------- Wages ----------------
    Provision(
        "COW-INFORCE", "Code on Wages, 2019", "Commencement",
        "The Code on Wages, 2019 and the other three labour codes came into force on 21 November 2025, replacing "
        "older laws such as the Payment of Wages Act, 1936. Some rules are notified separately by each state.",
        ("https://www.livelaw.in/amp/top-stories/centre-brings-four-labour-codes-into-operation-with-effect-from-november-21-310772",
         "https://www.newsonair.gov.in/government-implements-four-new-labour-codes/"), "secondary"),
    Provision(
        "COW-17", "Code on Wages, 2019", "Section 17",
        "Wages have time limits: monthly wages are due before the 7th day of the next month; if you resign, are "
        "removed, dismissed or retrenched, wages due must be paid within 2 working days.",
        ("https://www.advocatekhoj.com/library/bareacts/codeonwages/17.php",
         "https://www.taxmann.com/post/blog/payment-of-wages-act-code-on-wages-wage-period-time-limit"),
        "secondary", "The government can prescribe other time limits; state rules may differ."),
    Provision(
        "COW-45", "Code on Wages, 2019", "Section 45",
        "A claim for unpaid or short-paid wages can be filed before the authority appointed under the Code, by you, "
        "your registered trade union, or the Inspector-cum-Facilitator, generally within 3 years from when the claim "
        "arose (later only with sufficient cause). The authority aims to decide within 3 months.",
        ("https://www.advocatekhoj.com/library/bareacts/codeonwages/45.php",
         "https://www.indiacode.nic.in/bitstream/123456789/15793/1/aA2019-29.pdf"), "secondary",
        "Which officer is the 'authority' is set by your state; ask the local Labour Department."),
    # ---------------- Rent deposit ----------------
    Provision(
        "MTA-2021", "Model Tenancy Act, 2021 (model law)", "Security deposit cap",
        "The Model Tenancy Act caps a residential security deposit at 2 months' rent and sets up Rent Authorities "
        "and Rent Courts. It is only a model: it applies only where your state has adopted it; many states still "
        "use their own older rent laws.",
        ("https://www.deccanherald.com/india/union-cabinet-approves-model-tenancy-act-district-wise-rent-courts-new-security-deposit-rules-992937.html",
         "https://www.drishtiias.com/daily-updates/daily-news-analysis/model-tenancy-act-2"), "secondary",
        "Adoption varies by state and the tool cannot confirm your state's current law."),
    Provision(
        "CPC-20", "Code of Civil Procedure, 1908", "Section 20",
        "A civil suit (for example to recover your deposit) is generally filed in the court where the other party "
        "lives or works, or where the cause of action arose.",
        ("https://www.indiacode.nic.in/",), "general"),
    Provision(
        "CPC-O37", "Code of Civil Procedure, 1908", "Order XXXVII",
        "If the money is owed under a written contract (such as a signed rent agreement), a faster 'summary suit' "
        "may be possible in courts where Order XXXVII applies. A lawyer should advise if it fits.",
        ("https://www.indiacode.nic.in/",), "general"),
    Provision(
        "LIMITATION", "Limitation Act, 1963", "General money claims",
        "Most civil claims to recover money must be filed within 3 years; the exact start date depends on the facts. "
        "Do not wait: delay can make a valid claim unenforceable.",
        ("https://www.indiacode.nic.in/",), "general", "The exact article and start date need a lawyer's check."),
    # ---------------- Help & escalation ----------------
    Provision(
        "NALSA", "Legal Services Authorities Act, 1987", "Section 12; NALSA helpline 15100",
        "Free legal aid is available through Legal Services Authorities. Women, children, SC/ST members and people "
        "who cannot afford a lawyer are among those eligible (Section 12). Call 15100 or visit the nearest District "
        "Legal Services Authority. The authority must also see that you have a case worth pursuing.",
        ("https://nalsa.gov.in/legal-services/", "https://nalsa.gov.in/faqs/"), "official"),
    Provision(
        "LOKADALAT", "Legal Services Authorities Act, 1987", "Lok Adalat",
        "Many money disputes can be settled at a Lok Adalat, including before a case is filed; there is no court fee "
        "and settlements are binding. Ask the District Legal Services Authority.",
        ("https://nalsa.gov.in/legal-services/",), "general"),
]}

# Hard-coded emergency contacts (national numbers).
EMERGENCY = {
    "police_emergency": "112 (national emergency number)",
    "women_helpline": "181 (women helpline)",
    "cyber_fraud": "1930 or cybercrime.gov.in (online financial fraud: report within hours)",
    "legal_aid": "15100 (NALSA free legal aid)",
}


@dataclass
class Category:
    id: str
    name: str
    provisions: List[str]
    evidence: List[tuple]  # (what proof helps, in plain words; intake evidence kind that covers it)
    facts_needed: List[str]  # keys the case needs
    steps: List[str] = field(default_factory=list)


CATEGORIES: Dict[str, Category] = {c.id: c for c in [
    Category(
        "consumer_refund", "Refund / defective product or service (consumer dispute)",
        ["NCH", "CPA-FORUM", "CPA-FEE", "CPA-LIMIT", "EFILE"],
        [("invoice or order confirmation", "receipt/invoice"), ("payment proof (bank/UPI/card statement)", "bank/UPI proof"),
         ("screenshots of the product page/promise", "messages/emails"), ("photos or video of the defect", "photos/video"),
         ("your complaint emails/chats and their replies, with dates", "messages/emails")],
        ["amount", "purchase_date", "seller"],
        ["Write to the company once more, in writing, giving a clear deadline (7 to 15 days). Keep the proof.",
         "Register a free grievance with the National Consumer Helpline [NCH].",
         "If unresolved, file a complaint with the District Consumer Commission online [EFILE] [CPA-FORUM]; "
         "no fee up to Rs 5 lakh [CPA-FEE]. Check the 2-year time limit [CPA-LIMIT]."]),
    Category(
        "rent_deposit", "Landlord not returning the security deposit",
        ["MTA-2021", "LOKADALAT", "CPC-20", "CPC-O37", "LIMITATION"],
        [("rent/lease agreement", "written agreement"), ("proof you paid the deposit (bank transfer/receipt)", "bank/UPI proof"),
         ("rent payment history", "bank/UPI proof"), ("photos/video of the flat when you left", "photos/video"),
         ("messages asking for the deposit back", "messages/emails")],
        ["amount", "move_out_date", "state"],
        ["Ask in writing (WhatsApp/email) for the deposit with an itemised list of any deductions, and a deadline.",
         "Send a formal legal notice (draft below) by registered post / speed post and keep the receipt.",
         "Try settlement at a Lok Adalat through the District Legal Services Authority [LOKADALAT].",
         "If still unpaid, a civil suit for recovery in the proper court [CPC-20] (summary suit may fit a written "
         "agreement [CPC-O37]). Mind the time limit [LIMITATION]. If your state adopted the Model Tenancy Act, a Rent "
         "Authority may be available [MTA-2021]."]),
    Category(
        "unpaid_salary", "Salary / wages not paid",
        ["COW-INFORCE", "COW-17", "COW-45", "LIMITATION"],
        [("offer/appointment letter or contract", "salary slips/offer letter"),
         ("salary slips and bank statements showing what was paid", "salary slips/offer letter"),
         ("attendance records, emails or chats showing you worked", "messages/emails"),
         ("resignation/termination letter with date", "written agreement"), ("any written promise to pay", "messages/emails")],
        ["amount", "unpaid_since", "employer"],
        ["Write to HR/management asking for the exact amount by a date, citing the wage time limits [COW-17].",
         "Send a legal notice (draft below) if there is no answer.",
         "File a claim before the wage authority under the Code on Wages through your state Labour Department "
         "[COW-45]; a trade union or Inspector-cum-Facilitator can also file for you.",
         "Keep working records; claims generally must be made within 3 years [COW-45]."]),
]}

OUT_OF_SCOPE = {
    "criminal": "criminal matters (arrest, FIR, police case, bail, assault)",
    "family": "family matters (divorce, custody, maintenance, domestic violence)",
    "property_title": "property ownership, inheritance and land title disputes",
    "notice_received": "replying to a court summons or legal notice you received",
    "harassment": "sexual harassment or harassment at work (a serious matter that needs specialised help)",
    "cheque_bounce": "a bounced cheque (these cases can have short deadlines)",
    "insurance": "an insurance claim dispute",
    "loan_banking": "a loan, EMI, credit card or bank dispute",
    "counterparty_role": "a claim by a landlord, employer or seller against the other side (I only cover the tenant, "
                         "employee or customer side)",
}
