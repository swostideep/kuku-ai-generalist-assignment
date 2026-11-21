"""Tests for the web workspace (web.py). Synthetic screenplays only. Run: python3 -m unittest discover -s tests -v"""

from __future__ import annotations

import json
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

import web  # noqa: E402
from fixtures import drama_beats, screenplay, write_show  # noqa: E402


class WebApi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        base = Path(cls.tmp.name)
        write_show(base / "shows" / "Test Show", [screenplay(n, drama_beats()) for n in range(1, 4)])
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
            return r.status, r.read().decode("utf-8")

    def post(self, path, body):
        req = urllib.request.Request(self.url + path, data=json.dumps(body).encode(), method="POST")
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read())

    def status_of(self, fn):
        try:
            return fn()[0]
        except urllib.error.HTTPError as e:
            return e.code

    def test_W01_lists_shows(self):
        """W01 /api/shows lists the show folder with its episode count"""
        shows = json.loads(self.get("/api/shows")[1])["shows"]
        self.assertEqual([(s["id"], s["episodes"]) for s in shows], [("test-show", 3)])
        self.assertNotIn("path", shows[0])  # local paths are not sent to the browser

    def test_W02_analyse_runs_real_pipeline(self):
        """W02 POST /api/analyse runs the pipeline in the background; results match the files it writes"""
        code, st = self.post("/api/analyse", {"show": "test-show"})
        self.assertEqual(code, 202)
        for _ in range(200):
            st = json.loads(self.get("/api/status?show=test-show")[1])
            if st["state"] != "running":
                break
            time.sleep(0.05)
        self.assertEqual(st["state"], "done", st)
        res = json.loads(self.get("/api/results?show=test-show")[1])
        self.assertEqual(res, json.loads((Path(self.tmp.name) / "out" / "test-show" / "ranked_promos.json").read_text()))
        self.assertGreater(len(res["promos"]), 0)

    def test_W03_errors_are_clear(self):
        """W03 unknown show -> 404, bad JSON -> 400, unknown path -> 404, no traversal outside web/"""
        self.assertEqual(self.status_of(lambda: self.post("/api/analyse", {"show": "nope"})), 404)
        req = urllib.request.Request(self.url + "/api/analyse", data=b"{not json", method="POST")
        self.assertEqual(self.status_of(lambda: urllib.request.urlopen(req)), 400)
        self.assertEqual(self.status_of(lambda: self.get("/api/results?show=nope")), 404)
        self.assertEqual(self.status_of(lambda: self.get("/../web.py")), 404)
        self.assertEqual(self.status_of(lambda: self.get("/web.py")), 404)

    def test_W04_serves_the_page(self):
        """W04 the page and its assets are served"""
        for p in ("/", "/base.css", "/kit.js", "/app.css", "/app.js"):
            self.assertEqual(self.get(p)[0], 200, p)


if __name__ == "__main__":
    unittest.main()
