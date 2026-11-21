"""Tests for the web workspace (web.py). Synthetic screenplays only. Run: python3 -m unittest discover -s tests -v"""

from __future__ import annotations

import json
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

import web  # noqa: E402
from test_continuity import CLEAN, script  # noqa: E402


class WebApi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        base = Path(cls.tmp.name)
        show = base / "shows" / "Test Show"
        show.mkdir(parents=True)
        e2 = [c if c[3] != "You lied to the Ashford council." else (c[0], c[1], c[2], "You lied to the Ashferd council.") for c in CLEAN]
        (show / "e1.txt").write_text(script(1, CLEAN), encoding="utf-8")
        (show / "e2.txt").write_text(script(2, e2, notes="Picks up directly from Episode 1."), encoding="utf-8")
        cls.ws = web.Workspace(base / "shows", base / "out")
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), web.make_handler(cls.ws))
        cls.url = f"http://127.0.0.1:{cls.server.server_address[1]}"
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def get(self, path):
        with urllib.request.urlopen(self.url + path) as r:
            return r.status, r.read(), dict(r.headers)

    def post(self, path, body):
        req = urllib.request.Request(self.url + path, data=json.dumps(body).encode(), method="POST")
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read())

    def code(self, fn):
        try:
            return fn()[0]
        except urllib.error.HTTPError as e:
            return e.code

    def test_W01_check_matches_cli_rules(self):
        """W01 POST /api/check runs the same rules as run.py and finds the planted name drift"""
        code, res = self.post("/api/check", {"show": "test-show"})
        self.assertEqual(code, 200)
        self.assertEqual([f["type"] for f in res["findings"]], ["NAME_DRIFT"])
        self.assertEqual(json.loads(self.get("/api/results?show=test-show")[1]), res)

    def test_W02_context_and_export(self):
        """W02 /api/context returns the cue with its neighbours; /api/export downloads the CSV"""
        self.post("/api/check", {"show": "test-show"})
        ctx = json.loads(self.get("/api/context?show=test-show&episode=2&block=B3")[1])
        self.assertEqual(ctx["target"], "B3")
        self.assertEqual([c["id"] for c in ctx["cues"]], ["B1", "B2", "B3", "B4", "B5"])
        _, body, headers = self.get("/api/export?show=test-show")
        self.assertIn("attachment", headers["Content-Disposition"])
        self.assertTrue(body.decode("utf-8-sig").startswith("n,severity,type"))

    def test_W03_errors_are_clear(self):
        """W03 unknown show / cue / bad numbers give 404 or 400, never a crash"""
        self.assertEqual(self.code(lambda: self.post("/api/check", {"show": "nope"})), 404)
        self.assertEqual(self.code(lambda: self.get("/api/context?show=test-show&episode=x&block=B1")), 400)
        self.assertEqual(self.code(lambda: self.get("/api/context?show=test-show&episode=9&block=B1")), 404)
        self.assertEqual(self.code(lambda: self.get("/api/context?show=nope&episode=1&block=B1")), 404)
        self.assertEqual(self.code(lambda: self.get("/api/export?show=nope")), 404)
        self.assertEqual(self.code(lambda: self.get("/web.py")), 404)

    def test_W04_serves_the_page(self):
        """W04 the page and its assets are served"""
        for p in ("/", "/base.css", "/kit.js", "/app.css", "/app.js"):
            self.assertEqual(self.get(p)[0], 200, p)


if __name__ == "__main__":
    unittest.main()
