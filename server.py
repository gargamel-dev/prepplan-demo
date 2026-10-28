#!/usr/bin/env python3
"""PrepPlan demo backend — serves the demo and proxies AI calls to Anthropic.

The API key NEVER goes in the HTML. It lives only on this server, in the
ANTHROPIC_API_KEY environment variable or in a local .env file next to
this script (which you must never share or commit).

Run:
    python3 server.py
Then open:
    http://localhost:8000

Requires only the Python standard library. No packages to install.
"""
import json
import os
import re
import urllib.error
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", "8000"))
MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-haiku-4-5")
MAX_PROMPT_CHARS = 8000


def load_dotenv():
    """Load KEY=VALUE lines from .env, without overriding real env vars."""
    env_file = HERE / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def extract_json(text):
    """Pull a JSON object out of model output, tolerating ```json fences."""
    if not isinstance(text, str):
        raise ValueError("Model did not return text")
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("Model did not return JSON")
    return json.loads(match.group(0))


def call_anthropic(prompt, api_key):
    body = json.dumps({
        "model": MODEL,
        "max_tokens": 2000,
        "messages": [{"role": "user", "content": prompt}],
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=body,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "ignore")
        if e.code == 401:
            return 401, {"error": "The API key was rejected.", "code": "unauthorized"}
        if e.code == 429:
            return 429, {"error": "Too many requests. Wait a moment and try again.", "code": "rate_limited"}
        if e.code == 400:
            return 400, {"error": "The AI request was rejected. Check the model name and try again.", "code": "bad_request"}
        print(f"Anthropic error {e.code}: {detail[:300]}")
        return 502, {"error": "The AI service returned an error. Try again.", "code": "upstream_error"}
    except Exception as e:  # network failure, timeout, etc.
        print(f"Anthropic request failed: {e}")
        return 502, {"error": "Could not reach the AI service. Check your connection and try again.", "code": "upstream_error"}

    text = "".join(
        block.get("text", "")
        for block in payload.get("content", [])
        if isinstance(block, dict)
    )
    try:
        return 200, extract_json(text)
    except Exception:
        return 502, {"error": "The AI returned something unexpected. Try again.", "code": "bad_response"}


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(HERE), **kwargs)

    def log_message(self, *args):  # keep the console clean; never log keys
        pass

    def send_json(self, status, obj):
        data = json.dumps(obj).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path in ("/health", "/health/"):
            return self.send_json(200, {
                "ok": True,
                "ai_configured": bool(os.environ.get("ANTHROPIC_API_KEY")),
            })
        if self.path in ("/", ""):
            self.path = "/index.html"
        return super().do_GET()

    def do_POST(self):
        if self.path != "/api/generate":
            return self.send_json(404, {"error": "Not found.", "code": "not_found"})
        length = int(self.headers.get("Content-Length") or 0)
        if length > 20000:
            return self.send_json(413, {"error": "Request too large.", "code": "too_large"})
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except Exception:
            return self.send_json(400, {"error": "Invalid request.", "code": "bad_request"})
        prompt = payload.get("prompt")
        if not isinstance(prompt, str) or not prompt.strip():
            return self.send_json(400, {"error": "A prompt is required.", "code": "bad_request"})
        if len(prompt) > MAX_PROMPT_CHARS:
            return self.send_json(400, {"error": "Prompt too long.", "code": "too_large"})
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            return self.send_json(503, {
                "error": "AI is not set up yet on this server. Add your Anthropic API key and restart it.",
                "code": "missing_api_key",
            })
        status, obj = call_anthropic(prompt, api_key)
        return self.send_json(status, obj)


if __name__ == "__main__":
    load_dotenv()
    print(f"PrepPlan demo at http://{HOST}:{PORT}")
    print("AI configured:", bool(os.environ.get("ANTHROPIC_API_KEY")))
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("To enable AI meals: put ANTHROPIC_API_KEY=... in a .env file here, then restart.")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
