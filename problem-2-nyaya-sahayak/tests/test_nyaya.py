"""Tests for the AI lawyer. Run: python3 -m unittest discover -s tests -v"""

from __future__ import annotations

import json
import sys
import threading
import unittest
from datetime import date
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from nyaya import kb  # noqa: E402
from nyaya.advisor import Session, render  # noqa: E402
from nyaya.guard import validate_model_text  # noqa: E402
from nyaya.intake import classify, extract  # noqa: E402
from nyaya.llm import OpenAICompatible  # noqa: E402

TODAY = date(2026, 11, 21)
CASES = sorted((ROOT / "cases").glob("*.json"))


def run_case(case, model=None):
    s = Session(today=date.fromisoformat(case["today"]), model=model, model_name="fake")
    return [s.turn(t) for t in case["turns"]]


class ScriptedCases(unittest.TestCase):
    """CASE: every scripted conversation in cases/ meets its 'expect' block."""

    def test_all_cases(self):
        self.assertGreaterEqual(len(CASES), 28)
        for path in CASES:
            case = json.loads(path.read_text(encoding="utf-8"))
            with self.subTest(case=case["id"]):
                r = run_case(case)[-1]
                e = case["expect"]
                text = render(r)
                if "type" in e:
                    self.assertEqual(r["type"], e["type"])
                if "category" in e:
                    self.assertEqual(r.get("category"), e["category"])
                for cid in e.get("cites", []):
                    self.assertIn(cid, r.get("citations", []))
                if "amount" in e:
                    self.assertEqual(r["case_summary"]["amount_claimed"], e["amount"])
                if "state" in e:
                    self.assertIn(e["state"], r["case_summary"]["where"])
                if e.get("hindi"):
                    self.assertIn("hindi_summary", r)
                if "lawyer_trigger" in e:
                    self.assertTrue(any(e["lawyer_trigger"] in t for t in r["see_a_lawyer_if"]), r["see_a_lawyer_if"])
                if "question_contains" in e:
                    self.assertTrue(any(e["question_contains"] in q for q in r["questions"]), r["questions"])
                if e.get("safety"):
                    self.assertTrue(any("112" in x for x in r.get("safety", [])))
                if e.get("no_safety"):
                    self.assertFalse(r.get("safety"), r.get("safety"))
                if "no_lawyer_trigger" in e:
                    self.assertFalse(any(e["no_lawyer_trigger"] in t for t in r.get("see_a_lawyer_if", [])))
                if "no_question" in e:
                    self.assertFalse(any(e["no_question"] in q for q in r.get("questions", [])))
                if "message_contains" in e:
                    self.assertIn(e["message_contains"], r.get("message", ""))
                if "note_contains" in e:
                    self.assertTrue(any(e["note_contains"] in n for n in r.get("also_noted", [])))
                if e.get("fraud_safety"):
                    self.assertTrue(any("1930" in x for x in r.get("safety", [])))
                for bad in e.get("no_text", []):
                    self.assertNotIn(bad, text)
                # Universal rules for every reply:
                self.assertIn("not legal advice", r["disclaimer"])
                for cid in r.get("citations", []):
                    self.assertIn(cid, kb.PROVISIONS, "cites only knowledge-base entries")


class Intake(unittest.TestCase):
    def test_I01_amount_units(self):
        """I01 amounts: Rs 18,999 / 45 lakh / 30000 rs / 20000 रुपये are parsed"""
        f = extract("paid Rs 18,999 and 45 lakh and 30000 rs and 20000 रुपये", TODAY)
        self.assertEqual(sorted(v for v, _ in f.amounts), [18999, 20000, 30000, 4500000])

    def test_I02_negated_evidence(self):
        """I02 missing evidence: 'I don't have any agreement' does not count as having one"""
        f = extract("I don't have any agreement or receipt for the deposit", TODAY)
        self.assertNotIn("written agreement", f.evidence)
        self.assertTrue(f.evidence_missing_said)

    def test_I03_future_date_flagged(self):
        """I03 contradictory facts: a move-out date in the future is questioned"""
        r = Session(today=TODAY).turn("Landlord in Pune kept my deposit of Rs 20,000. I moved out on 10/02/2027.")
        self.assertTrue(any("future" in q for q in r["questions"]))

    def test_I04_tie_is_ambiguous(self):
        """I04 ambiguous input: equal evidence for two categories -> ask, don't guess"""
        f = extract("salary and deposit", TODAY)
        self.assertEqual(classify(f)[0], "")

    def test_I05_rent_vs_deposit_not_contradiction(self):
        """I05 no false contradiction: rent Rs 15,000 and deposit Rs 45,000 are different things"""
        r = Session(today=TODAY).turn("Rent was Rs 15,000 a month and the deposit was Rs 45,000. Landlord in Pune, moved out 1 month ago.")
        self.assertFalse(any("different amounts" in q for q in r["questions"]))
        self.assertEqual(r["case_summary"]["amount_claimed"], "Rs 45,000")

    def test_I06_long_input_truncated(self):
        """I06 boundary: a 50,000-character message is handled without error"""
        r = Session(today=TODAY).turn("salary not paid " * 3500)
        self.assertEqual(r["type"], "advice")


class Guard(unittest.TestCase):
    def setUp(self):
        self.f = extract("My landlord kept my deposit of Rs 40,000 in Pune", TODAY)
        self.allowed = {"MTA-2021", "CPC-20", "CPC-O37", "LIMITATION", "LOKADALAT", "NALSA"}

    def test_G01_clean_text_passes(self):
        """G01 grounded model text with known citations passes"""
        ok, p = validate_model_text("Ask in writing first, then try a Lok Adalat [LOKADALAT]. Your Rs 40,000 claim is "
                                    "generally a civil matter [CPC-20]. Order XXXVII may apply [CPC-O37].", self.allowed, self.f)
        self.assertTrue(ok, p)

    def test_G02_invented_section_rejected(self):
        """G02 hallucinated provision: 'Section 420 IPC' is rejected"""
        ok, p = validate_model_text("Under Section 420 IPC the landlord is a cheat [CPC-20].", self.allowed, self.f)
        self.assertFalse(ok)

    def test_G03_invented_act_rejected(self):
        """G03 hallucinated law: 'Tenant Rights Act, 2022' is rejected; a real listed Act name is not"""
        self.assertFalse(validate_model_text("The Tenant Rights Act, 2022 protects you.", self.allowed, self.f)[0])
        ok, _ = validate_model_text("The Consumer Protection Act, 2019 applies [CPA-LIMIT].", {"CPA-LIMIT"}, self.f)
        self.assertTrue(ok)

    def test_G04_unknown_citation_and_case_law(self):
        """G04 hallucinated citations: an unlisted [ID] and an invented case 'Sharma v. Gupta' are rejected"""
        self.assertFalse(validate_model_text("See [RENT-99].", self.allowed, self.f)[0])
        self.assertFalse(validate_model_text("As held in Sharma v. Gupta, you win.", self.allowed, self.f)[0])

    def test_G05_invented_amount_and_promise(self):
        """G05 invented facts: an amount the user never gave, or a promised outcome, is rejected"""
        self.assertFalse(validate_model_text("You can claim Rs 1,00,000 in damages.", self.allowed, self.f)[0])
        self.assertFalse(validate_model_text("You will definitely win this case.", self.allowed, self.f)[0])


class ModelPath(unittest.TestCase):
    def test_M01_hallucinating_model_is_discarded(self):
        """M01 model error: a model that invents 'Section 138' is discarded; the sourced answer still stands"""
        bad = lambda s, u: "Under Section 138 of the Negotiable Instruments Act, 1881 you get double the money."  # noqa: E731
        r = Session(today=TODAY, model=bad, model_name="fake").turn(
            "My landlord in Pune kept my Rs 40,000 deposit. I moved out 1 month ago. I have the agreement.")
        self.assertIsNone(r["plain_explanation"])
        self.assertFalse(r["model_check"]["used"])
        self.assertTrue(r["where_you_stand"])

    def test_M02_good_model_text_used(self):
        """M02 swappable model: grounded model text is shown, labelled with the model name"""
        good = lambda s, u: "Ask for the deposit in writing, then try a Lok Adalat [LOKADALAT]. Free legal aid: call 15100 [NALSA]."  # noqa: E731
        r = Session(today=TODAY, model=good, model_name="fake").turn(
            "My landlord in Pune kept my Rs 40,000 deposit. I moved out 1 month ago. I have the agreement.")
        self.assertTrue(r["model_check"]["used"])
        self.assertIn("Lok Adalat", r["plain_explanation"])

    def test_M03_model_crash_falls_back(self):
        """M03 model error: an exception from the model never breaks the reply"""
        def boom(s, u):
            raise RuntimeError("quota exceeded")
        r = Session(today=TODAY, model=boom, model_name="fake").turn("Salary of Rs 30,000 not paid by my employer in Delhi since 2 months.")
        self.assertEqual(r["type"], "advice")
        self.assertIn("quota", r["model_check"]["reason"])

    def test_M04_http_client_against_mock_server(self):
        """M04 OpenAI-compatible client works over HTTP (mock server) and returns content"""
        class H(BaseHTTPRequestHandler):
            def do_POST(self):  # noqa: N802
                self.rfile.read(int(self.headers["Content-Length"]))
                body = json.dumps({"choices": [{"message": {"content": "ok [NALSA]"}}]}).encode()
                self.send_response(200); self.end_headers(); self.wfile.write(body)  # noqa: E702

            def log_message(self, *a):
                pass
        srv = HTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            client = OpenAICompatible(f"http://127.0.0.1:{srv.server_port}/v1", "m", timeout=5)
            self.assertEqual(client("s", "u"), "ok [NALSA]")
        finally:
            srv.shutdown(); srv.server_close()  # noqa: E702


class KnowledgeBase(unittest.TestCase):
    def test_K01_every_provision_sourced(self):
        """K01 grounding: every provision has a source URL and a verification level"""
        for p in kb.PROVISIONS.values():
            self.assertTrue(p.sources and p.sources[0].startswith("https://"), p.id)
            self.assertIn(p.verification, {"official", "secondary", "general"}, p.id)

    def test_K02_category_citations_exist(self):
        """K02 grounding: categories only reference existing provisions, and their steps cite only those"""
        import re
        for c in kb.CATEGORIES.values():
            for pid in c.provisions:
                self.assertIn(pid, kb.PROVISIONS)
            for step in c.steps:
                for pid in re.findall(r"\[([A-Z0-9-]+)\]", step):
                    self.assertIn(pid, kb.PROVISIONS)


if __name__ == "__main__":
    unittest.main(verbosity=2)
