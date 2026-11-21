"""Tests for the continuity checker. Run: python3 -m unittest discover -s tests -v (synthetic scripts only)."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import run as cli  # noqa: E402
from continuity.checker import load, load_texts, run_checks  # noqa: E402
from continuity.review import review  # noqa: E402


def stamp(t):
    m = int(t // 60)
    return f"{m:02d}:{t - 60 * m:05.2f}"


def script(n, cues, notes="none", logline="A test.", scenes=(("INT. HALL - DAY", 0.0, 60.0),)):
    out = [f"EPISODE NUMBER: Episode {n}", f"EPISODE LOGLINE: {logline}", f"CONTINUITY NOTES: {notes}", "", "--- SCRIPT START ---"]
    for i, (head, s, e) in enumerate(scenes, 1):
        out += ["", f"SCENE {i:02d}", f"Scene heading: {head}", f"Scene start: {stamp(s)}", f"Scene end: {stamp(e)}", "",
                "Actions and dialogue:", ""]
        for label, a, b, text in cues:
            if s <= a < e:
                out += [f"**{label}:**", f"Start: ({stamp(a)}) | End: ({stamp(b)})", text if label in ("CAMERA", "ACTION") else f'"{text}"', ""]
    return "\n".join(out + ["--- SCRIPT END ---"])


CLEAN = [("CAMERA", 0, 3, "Wide shot of the hall as Mara enters."),
         ("MARA (Angry)", 1, 4, "Where is Viktor Ashford?"),
         ("VIKTOR (Cold)", 5, 8, "Right here, Mara."),
         ("MARA (Furious)", 9, 12, "You lied to the Ashford council."),
         ("VIKTOR (Calm)", 13, 16, "The council believes me.")]


def types(findings):
    return [f.type for f in findings]


class Checks(unittest.TestCase):
    def test_T01_clean_show_no_errors(self):
        """T01 normal input: two clean, consistent episodes produce no findings"""
        f = run_checks(load_texts({"e1.txt": script(1, CLEAN), "e2.txt": script(2, CLEAN, notes="Picks up directly from Episode 1.")}))
        self.assertEqual(f, [])

    def test_T02_name_drift(self):
        """T02 name drift: 'Ashford' vs 'Ashferd' across episodes is reported with both forms"""
        e2 = [c if c[3] != "You lied to the Ashford council." else (c[0], c[1], c[2], "You lied to the Ashferd council.") for c in CLEAN]
        f = run_checks(load_texts({"e1.txt": script(1, CLEAN), "e2.txt": script(2, e2)}))
        drift = [x for x in f if x.type == "NAME_DRIFT"]
        self.assertTrue(drift and "Ashferd" in drift[0].title and "Ashford" in drift[0].title)

    def test_T03_first_letter_and_sentence_start(self):
        """T03 name drift: 'Korinna' for 'Corinna' at the start of a line is still caught"""
        cues = CLEAN + [("MARA (Sad)", 20, 23, "I told Corinna everything."), ("VIKTOR (Cold)", 24, 27, "Then Corinna knows."),
                        ("MARA (Sad)", 28, 31, "And Corinna left.")]
        e2 = cues + [("VIKTOR (Cold)", 32, 35, "Korinna will not return.")]
        f = run_checks(load_texts({"e1.txt": script(1, cues), "e2.txt": script(2, e2)}))
        self.assertTrue(any(x.type == "NAME_DRIFT" and "Korinna" in x.title for x in f))

    def test_T04_different_names_not_merged(self):
        """T04 false-positive guard: 'Ashcombe' and 'Ashford' (different families) are not merged; 'General' is not 'Gerard'"""
        cues = [("MARA (Calm)", 1, 4, "The Ashcombe estate is old."), ("VIKTOR (Calm)", 5, 8, "The Ashford estate is older."),
                ("MARA (Calm)", 9, 12, "Ask Gerard about it."), ("VIKTOR (Calm)", 13, 16, "General Gerard agrees with Gerard.")]
        f = run_checks(load_texts({"e1.txt": script(1, cues + [("MARA (Calm)", 17, 20, "General rule: ask Gerard.")])}))
        self.assertFalse([x for x in f if x.type == "NAME_DRIFT"], [x.title for x in f])

    def test_T05_label_alias_but_not_couples(self):
        """T05 labels: 'LADY MARA' vs 'MARA' is flagged; 'LORD ASHFORD' and 'LADY ASHFORD' (a couple) are not"""
        cues = CLEAN + [("LADY MARA (Angry)", 20, 23, "Answer me."), ("LORD ASHFORD (Stern)", 24, 27, "Quiet."),
                        ("LADY ASHFORD (Soft)", 28, 31, "Please, both of you.")]
        f = run_checks(load_texts({"e1.txt": script(1, cues)}))
        titles = [x.title for x in f if x.type == "LABEL_ALIAS"]
        self.assertEqual(len(titles), 1)
        self.assertIn("LADY MARA", titles[0])

    def test_T06_unnamed_recurring_with_identity_guess(self):
        """T06 labels: a descriptive speaker in 3 episodes is flagged and the camera-text name is suggested"""
        cues = CLEAN + [("CAMERA", 20, 24, "Close-up on Brandt, the tall stranger, smirking."), ("TALL STRANGER (Smug)", 20, 23, "You will regret this."),
                        ("CAMERA", 24, 28, "Brandt steps closer."), ("TALL STRANGER (Smug)", 24, 27, "Every one of you.")]
        f = run_checks(load_texts({f"e{i}.txt": script(i, cues) for i in (1, 2, 3)}))
        un = [x for x in f if x.type == "UNNAMED_RECURRING"]
        self.assertTrue(un)
        self.assertEqual(un[0].evidence["likely_identity"][0][0], "Brandt")

    def test_T07_speech_rate_boundaries(self):
        """T07 boundary: 10 words in 2.5 s (4.0/s) passes; in 2.1 s (4.8/s) warns; in 1.5 s (6.7/s) is an error"""
        line = "one two three four five six seven eight nine ten"
        for dur, expected in ((2.5, None), (2.1, "warning"), (1.5, "error")):
            f = run_checks(load_texts({"e1.txt": script(1, [("MARA (Calm)", 1, 1 + dur, line)])}))
            got = [x.severity for x in f if x.type == "SPEECH_RATE"]
            self.assertEqual(got, [expected] if expected else [], dur)

    def test_T08_self_overlap_and_interruption(self):
        """T08 timing: a speaker overlapping their own line is an error; two speakers overlapping (an interruption) is not"""
        cues = [("MARA (Calm)", 1, 4, "I need to tell you"), ("MARA (Calm)", 3.5, 6, "something important."),
                ("VIKTOR (Cold)", 5.5, 8, "Not now.")]
        f = run_checks(load_texts({"e1.txt": script(1, cues)}))
        self.assertEqual(types(f).count("SELF_OVERLAP"), 1)

    def test_T09_scene_bounds_and_repeated_headings(self):
        """T09 scenes: a cue past its scene end is flagged; two scenes sharing a heading do not cause false alarms"""
        scenes = (("INT. CELL - NIGHT", 0.0, 10.0), ("EXT. YARD - DAY", 10.0, 20.0), ("INT. CELL - NIGHT", 20.0, 30.0))
        cues = [("MARA (Calm)", 1, 3, "Cold in here."), ("VIKTOR (Calm)", 11, 13, "Move along."), ("MARA (Calm)", 21, 23, "Back again.")]
        self.assertEqual(run_checks(load_texts({"e1.txt": script(1, cues, scenes=scenes)})), [])
        cues.append(("MARA (Calm)", 8, 11.5, "This line runs past the scene end."))
        f = run_checks(load_texts({"e1.txt": script(1, cues, scenes=scenes)}))
        self.assertIn("SCENE_BOUNDS", types(f))

    def test_T10_continuity_reference(self):
        """T10 continuity notes: 'Picks up from Episode 5' in episode 3 is an error; correct references pass"""
        texts = {"e1.txt": script(1, CLEAN), "e2.txt": script(2, CLEAN, notes="Follows directly from Episode 1."),
                 "e3.txt": script(3, CLEAN, notes="Picks up immediately from Episode 5.")}
        f = run_checks(load_texts(texts))
        self.assertEqual([x.episodes for x in f if x.type == "CONTINUITY_REF"], [[3]])

    def test_T11_bad_inputs(self):
        """T11 invalid input: missing folder, empty folder, empty file, duplicate episode numbers -> clear errors / exit 2"""
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            self.assertEqual(cli.main(["--show", str(d / "nope"), "--output", str(d / "o")]), 2)
            self.assertEqual(cli.main(["--show", str(d), "--output", str(d / "o")]), 2)
            (d / "e1.txt").write_text("", encoding="utf-8")
            self.assertEqual(cli.main(["--show", str(d), "--output", str(d / "o")]), 2)
            (d / "e1.txt").write_text(script(1, CLEAN), encoding="utf-8")
            (d / "e2.txt").write_text(script(1, CLEAN), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Duplicate"):
                load(d)

    def test_T12_cli_outputs_and_exit_code(self):
        """T12 end-to-end: CLI writes JSON/CSV/MD/HTML; exit 0 for a clean show, 1 when errors exist (pipeline gate)"""
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / "show").mkdir()
            (d / "show" / "e1.txt").write_text(script(1, CLEAN), encoding="utf-8")
            self.assertEqual(cli.main(["--show", str(d / "show"), "--output", str(d / "o")]), 0)
            for name in ("findings.json", "findings.csv", "report.md", "report.html"):
                self.assertTrue((d / "o" / name).exists(), name)
            (d / "show" / "e1.txt").write_text(script(1, CLEAN + [("MARA (Calm)", 20, 21, "one two three four five six seven eight")]), encoding="utf-8")
            self.assertEqual(cli.main(["--show", str(d / "show"), "--output", str(d / "o")]), 1)


class ModelReview(unittest.TestCase):
    def setUp(self):
        e2 = [c if c[3] != "You lied to the Ashford council." else (c[0], c[1], c[2], "You lied to the Ashferd council.") for c in CLEAN]
        self.findings = run_checks(load_texts({"e1.txt": script(1, CLEAN), "e2.txt": script(2, e2)}))

    def test_R01_valid_review_attached_not_deleting(self):
        """R01 model: a valid review is attached beside the finding; the finding itself is kept"""
        fake = lambda s, u: json.dumps({"canonical": "Ashford", "forms": {"Ashferd": "same", "Ashford": "same"}, "why": "typo"})  # noqa: E731
        stats = review(self.findings, fake, "fake")
        self.assertEqual(stats["reviewed"], 1)
        self.assertTrue(self.findings[0].model_review["used"])

    def test_R02_hallucinated_form_rejected(self):
        """R02 model hallucination: a reply naming a spelling that is not in the finding is rejected"""
        fake = lambda s, u: json.dumps({"canonical": "Ashfield", "forms": {"Ashfield": "same"}})  # noqa: E731
        stats = review(self.findings, fake, "fake")
        self.assertEqual(stats["rejected"], 1)
        self.assertFalse(self.findings[0].model_review["used"])

    def test_R03_model_error_keeps_rules(self):
        """R03 model error: an exception or non-JSON reply leaves the rule finding untouched"""
        def boom(s, u):
            raise RuntimeError("timeout")
        stats = review(self.findings, boom, "fake")
        self.assertEqual(stats["errors"], 1)
        self.assertEqual(self.findings[0].type, "NAME_DRIFT")


if __name__ == "__main__":
    unittest.main(verbosity=2)
