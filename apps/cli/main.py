from __future__ import annotations

import json
import os
import sys
import urllib.request
from pathlib import Path
from urllib.error import URLError


API_BASE = os.getenv("ALFA_API_BASE_URL", "http://localhost:8000")
OLLAMA_BASE = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
AUDIT_LOG_PATH = Path(os.getenv("ALFA_AUDIT_LOG_PATH", "./logs/audit.jsonl"))


def _http_get_json(url: str, timeout: float = 5.0) -> tuple[int, dict]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except URLError as exc:
        return 0, {"error": str(exc)}
    except Exception as exc:
        return 0, {"error": str(exc)}


def _http_post_json(url: str, payload: dict, timeout: float = 10.0) -> tuple[int, dict]:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except URLError as exc:
        return 0, {"error": str(exc)}
    except Exception as exc:
        return 0, {"error": str(exc)}


def _ok(msg: str) -> None:
    print(f"  OK  {msg}")


def _fail(msg: str) -> None:
    print(f"  FAIL  {msg}", file=sys.stderr)


def _warn(msg: str) -> None:
    print(f"  WARN  {msg}")


def cmd_bootstrap() -> int:
    """Create required local directories and verify .env.example."""
    print("=== bootstrap ===")
    dirs = [
        Path("./logs"),
        Path("./labs"),
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
        _ok(f"directory ensured: {d}")

    env_example = Path(".env.example")
    if env_example.exists():
        _ok(".env.example present")
    else:
        _warn(".env.example not found — copy manually from docs")

    env_local = Path(".env")
    if env_local.exists():
        _ok(".env present")
    else:
        _warn(".env not found — create from .env.example before running API")

    print("bootstrap done.")
    return 0


def cmd_smoke() -> int:
    """Quick smoke test: ALFA-CORE API health + route + ask."""
    print("=== smoke ===")
    failed = 0

    status, body = _http_get_json(f"{API_BASE}/health")
    if status == 200 and body.get("status") == "ok":
        _ok(f"GET /health → {body}")
    else:
        _fail(f"GET /health → status={status} body={body}")
        failed += 1

    status, body = _http_post_json(f"{API_BASE}/route", {"prompt": "explain this function"})
    if status == 200 and "decision" in body:
        _ok(f"POST /route → decision={body.get('decision')}")
    else:
        _fail(f"POST /route → status={status} body={body}")
        failed += 1

    status, body = _http_post_json(f"{API_BASE}/ask", {"prompt": "hello"})
    if status == 200 and "decision" in body:
        _ok(f"POST /ask → decision={body.get('decision')} error={body.get('error')}")
    else:
        _fail(f"POST /ask → status={status} body={body}")
        failed += 1

    if failed:
        print(f"smoke FAILED ({failed} checks).")
        return 1
    print("smoke passed.")
    return 0


def cmd_doctor() -> int:
    """Diagnose local dependencies: ALFA API, Ollama, audit log."""
    print("=== doctor ===")
    failed = 0

    status, body = _http_get_json(f"{API_BASE}/health")
    if status == 200:
        _ok(f"ALFA API reachable at {API_BASE}")
    else:
        _fail(f"ALFA API not reachable at {API_BASE} (status={status})")
        failed += 1

    status, body = _http_get_json(f"{OLLAMA_BASE}/api/tags")
    if status == 200:
        models = [m.get("name") for m in body.get("models", [])]
        _ok(f"Ollama reachable at {OLLAMA_BASE}, models: {models or '(none)'}")
    else:
        _fail(f"Ollama not reachable at {OLLAMA_BASE} (status={status})")
        failed += 1

    env_local = Path(".env")
    if env_local.exists():
        _ok(".env present")
    else:
        _warn(".env missing — set environment variables manually or create .env")

    if AUDIT_LOG_PATH.exists():
        lines = AUDIT_LOG_PATH.read_text(encoding="utf-8").splitlines()
        _ok(f"audit log present: {AUDIT_LOG_PATH} ({len(lines)} records)")
    else:
        _warn(f"audit log not yet created at {AUDIT_LOG_PATH} — created on first request")

    if failed:
        print(f"doctor found {failed} issue(s).")
        return 1
    print("doctor: all checks passed.")
    return 0


COMMANDS: dict[str, tuple[str, "function"]] = {
    "bootstrap": ("Create local dirs and verify config files", cmd_bootstrap),
    "smoke": ("Quick smoke test against running ALFA API", cmd_smoke),
    "doctor": ("Diagnose local dependencies (API, Ollama, audit)", cmd_doctor),
}


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print("Usage: python -m apps.cli <command>")
        print()
        print("Commands:")
        for name, (desc, _) in COMMANDS.items():
            print(f"  {name:<12} {desc}")
        return 0

    cmd = args[0]
    if cmd not in COMMANDS:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        print(f"Available: {', '.join(COMMANDS)}", file=sys.stderr)
        return 2

    _, fn = COMMANDS[cmd]
    return fn()


if __name__ == "__main__":
    sys.exit(main())
