"""Continuity Checker web workspace (standard library only).

  python3 web.py --shows "<folder of show folders, or one show folder>" [--port 8703]

Endpoints (JSON unless noted):
  GET  /api/shows                                   shows found under --shows, with whether a report exists
  POST /api/check {"show": id}                      runs the real rule checks (same as run.py) and returns the report
  GET  /api/results?show=id                         the last report (outputs/web/<id>/findings.json)
  GET  /api/context?show=id&episode=N&block=B12     the cue plus up to 2 cues either side, for reading a finding in place
  GET  /api/export?show=id                          findings.csv for triage in a spreadsheet (download)
Reports are written to outputs/web/<show id>/, the same files the CLI writes.
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

from continuity.checker import load, run_checks
from continuity.parser import format_time
from continuity.report import write_all

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
        self.cache = {}  # show id -> loaded scripts (for context lookups)
        self.lock = threading.Lock()

    def shows(self):
        root = self.root
        folders = [root] if any(root.glob("*.txt")) else sorted(p for p in root.iterdir() if p.is_dir() and any(p.glob("*.txt")))
        out = []
        for f in folders:
            sid = slug(f.name)
            res = self.out / sid / "findings.json"
            out.append({"id": sid, "name": f.name, "episodes": len(list(f.glob("*.txt"))), "path": f,
                        "has_results": res.exists(),
                        "checked_at": time.strftime("%d %b %Y, %H:%M", time.localtime(res.stat().st_mtime)) if res.exists() else None})
        return out

    def find(self, sid):
        return next((s for s in self.shows() if s["id"] == sid), None)

    def scripts(self, sid):
        with self.lock:
            if sid not in self.cache:
                show = self.find(sid)
                if show is None:
                    raise KeyError(sid)
                self.cache[sid] = load(show["path"])
            return self.cache[sid]

    def check(self, sid):
        show = self.find(sid)
        if show is None:
            raise KeyError(sid)
        t0 = time.time()
        scripts = load(show["path"])
        with self.lock:
            self.cache[sid] = scripts
        findings = run_checks(scripts)
        meta = {"show": show["name"], "episodes": len(scripts), "blocks": sum(len(s.episode.blocks) for s in scripts),
                "model": "disabled (rules only, offline)", "runtime_seconds": round(time.time() - t0, 2),
                "parser_warnings": [w for s in scripts for w in s.episode.warnings]}
        write_all(self.out / sid, findings, meta)
        return self.results(sid)

    def results(self, sid):
        p = self.out / sid / "findings.json"
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None

    def context(self, sid, episode: int, block: str, around: int = 2):
        ep = next((s.episode for s in self.scripts(sid) if s.episode.number == episode), None)
        if ep is None:
            return None
        idx = next((i for i, b in enumerate(ep.blocks) if b.id == block), None)
        if idx is None:
            return None
        lo, hi = max(0, idx - around), min(len(ep.blocks), idx + around + 1)
        return {"episode": episode, "file": ep.file, "target": block,
                "cues": [{"id": b.id, "kind": b.kind, "speaker": b.speaker, "time": format_time(b.start),
                          "end": format_time(b.end), "text": b.text} for b in ep.blocks[lo:hi]]}


def make_handler(ws: Workspace):
    class Handler(BaseHTTPRequestHandler):
        def _send(self, code, body, ctype="application/json", extra=None):
            data = body.encode("utf-8") if isinstance(body, str) else body
            self.send_response(code)
            self.send_header("Content-Type", ctype + "; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(data)

        def _json(self, code, obj):
            self._send(code, json.dumps(obj, ensure_ascii=False))

        def do_GET(self):  # noqa: N802
            u = urlparse(self.path)
            q = {k: v[0] for k, v in parse_qs(u.query).items()}
            sid = q.get("show", "")
            if u.path in STATIC:
                name, ctype = STATIC[u.path]
                return self._send(200, (WEB / name).read_text(encoding="utf-8"), ctype)
            if u.path == "/api/shows":
                return self._json(200, {"shows": [{k: v for k, v in s.items() if k != "path"} for s in ws.shows()]})
            if u.path == "/api/results":
                data = ws.results(sid)
                return self._json(200, data) if data else self._json(404, {"error": "No report yet. Run the checks first."})
            if u.path == "/api/context":
                try:
                    data = ws.context(sid, int(q.get("episode", "")), q.get("block", ""))
                except KeyError:
                    return self._json(404, {"error": "Unknown show."})
                except ValueError:
                    return self._json(400, {"error": "Bad episode number."})
                return self._json(200, data) if data else self._json(404, {"error": "Cue not found."})
            if u.path == "/api/export":
                p = ws.out / sid / "findings.csv"
                if not sid or ws.find(sid) is None or not p.exists():
                    return self._json(404, {"error": "No report yet. Run the checks first."})
                return self._send(200, p.read_bytes(), "text/csv",
                                  {"Content-Disposition": f'attachment; filename="continuity-{sid}.csv"'})
            self._json(404, {"error": "Not found."})

        def do_POST(self):  # noqa: N802
            if urlparse(self.path).path != "/api/check":
                return self._json(404, {"error": "Not found."})
            try:
                n = int(self.headers.get("Content-Length", "0"))
                sid = json.loads(self.rfile.read(n) or b"{}").get("show", "")
                self._json(200, ws.check(sid))
            except KeyError:
                self._json(404, {"error": "Unknown show."})
            except (OSError, ValueError) as exc:  # bad JSON body, or a screenplay the parser rejects
                self._json(400, {"error": f"Could not check this show: {exc}"})

        def log_message(self, *a):
            pass
    return Handler


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--shows", type=Path, required=True, help="A folder of show folders, or a single show folder")
    p.add_argument("--port", type=int, default=8703)
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
    print(f"Continuity Checker: open http://localhost:{a.port}  ({len(ws.shows())} show(s) found; Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
