"""Optional OpenAI-compatible model client (Ollama, Groq, OpenRouter, vLLM, Kuku's gateway...). Stdlib only."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request


class OpenAICompatible:
    def __init__(self, base_url: str, model: str, api_key: str = "", timeout: int = 60, retries: int = 1):
        url = base_url.rstrip("/")
        self.url = url if url.endswith("/chat/completions") else url + "/chat/completions"
        self.model, self.api_key, self.timeout, self.retries = model, api_key, timeout, retries

    def __call__(self, system: str, user: str) -> str:
        body = json.dumps({"model": self.model, "temperature": 0, "messages": [
            {"role": "system", "content": system}, {"role": "user", "content": user}]}).encode()
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        last = None
        for attempt in range(self.retries + 1):
            try:
                req = urllib.request.Request(self.url, data=body, headers=headers, method="POST")
                with urllib.request.urlopen(req, timeout=self.timeout) as r:
                    return json.loads(r.read().decode())["choices"][0]["message"]["content"]
            except (urllib.error.URLError, TimeoutError, KeyError, IndexError, ValueError) as exc:
                if isinstance(exc, urllib.error.HTTPError):
                    exc.close()
                last = exc
                if attempt < self.retries:
                    time.sleep(1.0)
        raise RuntimeError(f"model call failed: {last}")
