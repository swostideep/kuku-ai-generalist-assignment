"""Promo Finder web workspace (standard library only).

  python3 web.py --shows "<folder of show folders, or one show folder>" [--port 8701]

Endpoints (JSON):
  GET  /api/shows                 shows found under --shows, with whether results already exist
  POST /api/analyse {"show": id}  runs the real pipeline in a background thread
  GET  /api/status?show=id        idle | running (episode i of n) | done | error
  GET  /api/results?show=id       the ranked promos written by the pipeline (outputs/web/<id>/ranked_promos.json)
Results are written to outputs/web/<show id>/, the same files the CLI writes.
"""

from __future__ import annotations

import argparse
import json
import re
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from promo_finder.pipeline import run

HERE = Path(__file__).resolve().parent
WEB = HERE / "web"
STATIC = {"/": ("index.html", "text/html"), "/index.html": ("index.html", "text/html"),
          "/m3.css": ("m3.css", "text/css"), "/ui.js": ("ui.js", "text/javascript"),
          "/app.css": ("app.css", "text/css"), "/app.js": ("app.js", "text/javascript")}


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:60] or "show"


class Workspace:
    def __init__(self, shows_root: Path, out_root: Path):
        self.root, self.out = shows_root, out_root
        self.jobs = {}  # show id -> status dict
        self.lock = threading.Lock()

    def shows(self):
        root = self.root
        folders = [root] if any(root.glob("*.txt")) else sorted(p for p in root.iterdir() if p.is_dir() and any(p.glob("*.txt")))
        out = []
        for f in folders:
            sid = slug(f.name)
            res = self.out / sid / "ranked_promos.json"
            out.append({"id": sid, "name": f.name, "episodes": len(list(f.glob("*.txt"))), "path": f,
                        "has_results": res.exists(),
                        "analysed_at": time.strftime("%d %b %Y, %H:%M", time.localtime(res.stat().st_mtime)) if res.exists() else None})
        return out

    def find(self, sid):
        return next((s for s in self.shows() if s["id"] == sid), None)

    def status(self, sid):
        with self.lock:
            return dict(self.jobs.get(sid, {"state": "idle"}))

    def start(self, sid):
        show = self.find(sid)
        if show is None:
            raise KeyError(sid)
        with self.lock:
            if self.jobs.get(sid, {}).get("state") == "running":
                return
            self.jobs[sid] = {"state": "running", "done": 0, "total": show["episodes"], "message": "Reading episodes…"}

        def prog(i, n):
            with self.lock:
                self.jobs[sid].update(done=i - 1, total=n, message=f"Scoring episode {i} of {n}…")

        def work():
            try:
                res = run(show["path"], self.out / sid, log=lambda *_: None, progress=prog)
                with self.lock:
                    self.jobs[sid] = {"state": "done", "done": show["episodes"], "total": show["episodes"],
                                      "message": f"{res['stats']['selected_count']} promos ranked."}
            except Exception as exc:  # surface any failure to the UI instead of hanging
                with self.lock:
                    self.jobs[sid] = {"state": "error", "message": f"Analysis failed: {exc}"}
        threading.Thread(target=work, daemon=True).start()

    def results(self, sid):
        p = self.out / sid / "ranked_promos.json"
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def make_handler(ws: Workspace):
    class Handler(BaseHTTPRequestHandler):
        def _send(self, code, body, ctype="application/json"):
            data = body.encode("utf-8") if isinstance(body, str) else body
            self.send_response(code)
            self.send_header("Content-Type", ctype + "; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def _json(self, code, obj):
            self._send(code, json.dumps(obj, ensure_ascii=False))

        def do_GET(self):  # noqa: N802
            u = urlparse(self.path)
            q = {k: v[0] for k, v in parse_qs(u.query).items()}
            if u.path in STATIC:
                name, ctype = STATIC[u.path]
                return self._send(200, (WEB / name).read_text(encoding="utf-8"), ctype)
            if u.path == "/api/shows":
                return self._json(200, {"shows": [{k: v for k, v in s.items() if k != "path"} for s in ws.shows()]})
            if u.path == "/api/status":
                return self._json(200, ws.status(q.get("show", "")))
            if u.path == "/api/results":
                data = ws.results(q.get("show", ""))
                return self._json(200, data) if data else self._json(404, {"error": "No results yet. Run the analysis first."})
            self._json(404, {"error": "Not found."})

        def do_POST(self):  # noqa: N802
            if urlparse(self.path).path != "/api/analyse":
                return self._json(404, {"error": "Not found."})
            try:
                n = int(self.headers.get("Content-Length", "0"))
                sid = json.loads(self.rfile.read(n) or b"{}").get("show", "")
                ws.start(sid)
                self._json(202, ws.status(sid))
            except KeyError:
                self._json(404, {"error": "Unknown show."})
            except (ValueError, json.JSONDecodeError):
                self._json(400, {"error": "Bad request."})

        def log_message(self, *a):
            pass
    return Handler


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--shows", type=Path, required=True, help="A folder of show folders, or a single show folder")
    p.add_argument("--port", type=int, default=8701)
    p.add_argument("--output", type=Path, default=HERE / "outputs" / "web")
    a = p.parse_args(argv)
    if not a.shows.is_dir():
        print(f"error: not a folder: {a.shows}")
        return 2
    ws = Workspace(a.shows.resolve(), a.output)
    if not ws.shows():
        print(f"error: no episode .txt files found in {a.shows} or its subfolders")
        return 2
    server = ThreadingHTTPServer(("127.0.0.1", a.port), make_handler(ws))
    print(f"Promo Finder: open http://localhost:{a.port}  ({len(ws.shows())} show(s) found; Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
