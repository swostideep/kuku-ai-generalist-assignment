"""Nyaya Sahayak: a narrow, honest AI legal-help assistant for everyday Indian money disputes.

  python3 app.py chat                       # talk in the terminal (type 'quit' to stop)
  python3 app.py web [--port 8765]          # browser UI with voice input (Chrome), http://localhost:8765
  python3 app.py cases [--output outputs]   # run all scripted test conversations in cases/ -> raw outputs
Optional model (any OpenAI-compatible endpoint) for the plain-language explanation:
  --llm-base-url http://localhost:11434/v1 --llm-model llama3.1   (API key from env LLM_API_KEY)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from nyaya.advisor import Session, render
from nyaya.llm import OpenAICompatible

HERE = Path(__file__).resolve().parent


def make_model(a):
    if not a.llm_base_url:
        return None, ""
    return OpenAICompatible(a.llm_base_url, a.llm_model, os.environ.get("LLM_API_KEY", "")), a.llm_model


def chat(a) -> int:
    model, name = make_model(a)
    s = Session(model=model, model_name=name)
    print("Describe your problem (refund, rent deposit or unpaid salary). Type 'quit' to stop.\n")
    while True:
        try:
            text = input("you> ")
        except EOFError:
            break
        if text.strip().lower() in {"quit", "exit"}:
            break
        print("\n" + render(s.turn(text)) + "\n")
    return 0


def run_cases(a) -> int:
    model, name = make_model(a)
    out_dir = a.output
    out_dir.mkdir(parents=True, exist_ok=True)
    index = []
    for path in sorted((HERE / "cases").glob("*.json")):
        case = json.loads(path.read_text(encoding="utf-8"))
        s = Session(today=date.fromisoformat(case.get("today", "2026-11-21")), model=model, model_name=name)
        turns = []
        for msg in case["turns"]:
            resp = s.turn(msg)
            turns.append({"user": msg, "response": resp, "rendered": render(resp)})
        record = {"id": case["id"], "title": case["title"], "tests": case.get("tests", []), "expect": case.get("expect", {}),
                  "turns": turns}
        (out_dir / f"{case['id']}.json").write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        (out_dir / f"{case['id']}.txt").write_text(
            "\n\n".join(f">>> USER: {t['user']}\n\n{t['rendered']}" for t in turns), encoding="utf-8")
        index.append({"id": case["id"], "title": case["title"], "final_type": turns[-1]["response"]["type"],
                      "category": turns[-1]["response"].get("category", "")})
        print(f"{case['id']}: {case['title']} -> {turns[-1]['response']['type']} {turns[-1]['response'].get('category', '')}")
    (out_dir / "index.json").write_text(json.dumps(index, indent=2), encoding="utf-8")
    return 0


PAGE = (HERE / "web" / "index.html")
SESSIONS = {}


class Handler(BaseHTTPRequestHandler):
    model = None
    model_name = ""

    def _send(self, code, body, ctype="application/json"):
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype + "; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):  # noqa: N802
        if self.path in ("/", "/index.html"):
            return self._send(200, PAGE.read_text(encoding="utf-8"), "text/html")
        self._send(404, json.dumps({"error": "not found"}))

    def do_POST(self):  # noqa: N802
        if self.path != "/api/turn":
            return self._send(404, json.dumps({"error": "not found"}))
        try:
            n = int(self.headers.get("Content-Length", "0"))
            if n > 20000:
                return self._send(413, json.dumps({"error": "message too long"}))
            payload = json.loads(self.rfile.read(n) or b"{}")
            sid = str(payload.get("session") or uuid.uuid4())
            if len(SESSIONS) > 1000:
                SESSIONS.clear()
            s = SESSIONS.setdefault(sid, Session(model=type(self).model, model_name=type(self).model_name))
            resp = s.turn(str(payload.get("text", "")))
            resp["session"] = sid
            self._send(200, json.dumps(resp, ensure_ascii=False))
        except (ValueError, json.JSONDecodeError):
            self._send(400, json.dumps({"error": "bad request"}))

    def log_message(self, *args):
        pass


def web(a) -> int:
    Handler.model, Handler.model_name = make_model(a)
    server = ThreadingHTTPServer(("127.0.0.1", a.port), Handler)
    print(f"Open http://localhost:{a.port}  (Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("mode", choices=["chat", "web", "cases"])
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--output", type=Path, default=HERE / "outputs")
    p.add_argument("--llm-base-url")
    p.add_argument("--llm-model")
    a = p.parse_args(argv)
    if bool(a.llm_base_url) != bool(a.llm_model):
        print("error: pass both --llm-base-url and --llm-model, or neither", file=sys.stderr)
        return 2
    return {"chat": chat, "web": web, "cases": run_cases}[a.mode](a)


if __name__ == "__main__":
    raise SystemExit(main())
