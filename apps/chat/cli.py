"""
ALFA-CORE CLI Chat — lokalny terminal REPL

Przepływ:
  input -> VoiceFlow (wake word + intent + risk) -> ALFA API /ask -> output

Tryb domyślny: PRIVATE_ARMENIAN
Wake word:     Հայկ  (można też pisać: alfa, ালফা)

Specjalne komendy:
  /quit   — wyjście
  /reset  — reset sesji
  /status — stan sesji
  /audit  — ostatnie 5 event audytu
"""

from __future__ import annotations

import os
import sys
import json
import time
import urllib.request
import urllib.error
from pathlib import Path

# Dodaj root projektu do path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from packages.sensors.voice_policy import (
    VoiceFlow,
    VoicePolicyConfig,
    ConfirmationRequirement,
)
from packages.sensors.activation import ActivationGate, ActivationDecision

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

ALFA_API_BASE = os.environ.get("ALFA_API_BASE_URL", "http://localhost:8000")
VOICE_MODE = os.environ.get("VOICE_MODE", "PRIVATE_ARMENIAN")

BANNER = """
╔══════════════════════════════════════════════════╗
║         ALFA-CORE  ·  Lokalny Chat CLI           ║
║  Tryb: {mode:<40}║
║  Wake word: Հայկ / alfa / alalfa                 ║
║  Wpisz /quit żeby wyjść                          ║
╚══════════════════════════════════════════════════╝
""".format(mode=VOICE_MODE)

COLORS = {
    "reset": "\033[0m",
    "grey":  "\033[90m",
    "green": "\033[92m",
    "yellow": "\033[93m",
    "red":   "\033[91m",
    "cyan":  "\033[96m",
    "bold":  "\033[1m",
}


def c(color: str, text: str) -> str:
    if not sys.stdout.isatty():
        return text
    return f"{COLORS.get(color, '')}{text}{COLORS['reset']}"


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

def api_ask(prompt: str, metadata: dict) -> dict:
    payload = json.dumps({"prompt": prompt, "metadata": metadata}).encode()
    req = urllib.request.Request(
        f"{ALFA_API_BASE}/ask",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except urllib.error.URLError as exc:
        return {"error": str(exc), "output": None}


def api_health() -> bool:
    try:
        with urllib.request.urlopen(f"{ALFA_API_BASE}/health", timeout=5) as resp:
            data = json.loads(resp.read())
            return data.get("status") == "ok"
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

class ChatSession:
    def __init__(self) -> None:
        self.cfg = VoicePolicyConfig.from_env()
        self.flow = VoiceFlow(self.cfg)
        self.gate = ActivationGate(
            wake_words=frozenset({self.cfg.wake_word.lower(), "alfa", "ალфа"}),
        )
        self.listening = False
        self.audit_events: list[dict] = []
        self.message_count = 0

    def reset(self) -> None:
        self.gate.reset()
        self.listening = False
        self.message_count = 0
        print(c("yellow", "↺  Sesja zresetowana."))

    def status(self) -> None:
        state = "SŁUCHANIE AKTYWNE" if self.listening else "IDLE (czeka na wake word)"
        print(c("cyan", f"  Stan:        {state}"))
        print(c("cyan", f"  Wake word:   {self.cfg.wake_word}"))
        print(c("cyan", f"  Języki:      {self.cfg.voice_lang} / {self.cfg.alt_voice_lang}"))
        print(c("cyan", f"  Wiadomości:  {self.message_count}"))
        print(c("cyan", f"  ALFA API:    {ALFA_API_BASE}"))

    def show_audit(self, n: int = 5) -> None:
        events = self.gate.audit_log() + self.audit_events
        for ev in events[-n:]:
            print(c("grey", f"  {json.dumps(ev, ensure_ascii=False)}"))


# ---------------------------------------------------------------------------
# Main REPL
# ---------------------------------------------------------------------------

def run() -> None:
    print(BANNER)

    # Sprawdź dostępność API
    if api_health():
        print(c("green", f"✓  ALFA API online: {ALFA_API_BASE}"))
    else:
        print(c("yellow", f"⚠  ALFA API niedostępne ({ALFA_API_BASE}) — odpowiedzi będą offline"))
    print()

    session = ChatSession()

    while True:
        try:
            prefix = c("green", "◉ ") if session.listening else c("grey", "○ ")
            user_input = input(f"{prefix}{c('bold', 'Ty')}: ").strip()
        except (KeyboardInterrupt, EOFError):
            print(c("grey", "\nDo widzenia."))
            break

        if not user_input:
            continue

        # --- Specjalne komendy ---
        if user_input.startswith("/"):
            cmd = user_input.lower()
            if cmd in {"/quit", "/exit", "/q"}:
                print(c("grey", "Do widzenia."))
                break
            elif cmd == "/reset":
                session.reset()
            elif cmd == "/status":
                session.status()
            elif cmd.startswith("/audit"):
                session.show_audit()
            else:
                print(c("red", f"  Nieznana komenda: {user_input}"))
            continue

        # --- VoiceFlow pipeline ---
        already_listening = session.listening
        result = session.flow.process(user_input, already_listening=already_listening)
        session.audit_events.append(result.audit_event)

        # Aktualizuj stan słuchania
        if result.wake_word_matched:
            session.listening = True

        if not result.wake_word_matched and not already_listening:
            print(c("grey", f"  (brak wake word — system IDLE; powiedz '{session.cfg.wake_word}')"))
            continue

        if result.intent is None and result.wake_word_matched:
            print(c("yellow", "  Tryb słuchania aktywny. Podaj komendę."))
            continue

        if result.decision is None:
            # Brak rozpoznanego intentu — wyślij bezpośrednio do API
            _send_to_api(user_input, session, risk_hint="LOW")
            continue

        decision = result.decision
        lang_tag = f"[{result.lang_hint}]" if result.lang_hint != "unknown" else ""

        # BLOCKED — exec bez auth
        if decision.confirmation == ConfirmationRequirement.BLOCKED:
            print(c("red", f"  ✗  {decision.reason}"))
            print(c("grey",  "     Operacja EXEC jest zablokowana bez pełnej autoryzacji."))
            continue

        # HIGH RISK — wymagane potwierdzenie
        if decision.confirmation == ConfirmationRequirement.REQUIRED and not decision.allowed:
            print(c("yellow", f"  ⚠  {decision.reason}"))
            confirm = input(c("yellow", "     Potwierdź PIN: ")).strip()
            ok = session.gate.confirm_l2_pin(confirm)
            if not ok:
                print(c("red", "     ✗ PIN nieprawidłowy. Akcja anulowana."))
                _check_lockout(session)
                continue
            print(c("green", "     ✓ L2 potwierdzone."))

        # SOFT — opcjonalne info
        if decision.confirmation == ConfirmationRequirement.SOFT:
            print(c("grey", f"  ℹ  (ryzyko: {decision.risk}) {lang_tag}"))

        # Wyślij do API
        _send_to_api(
            user_input,
            session,
            risk_hint=decision.risk.value,
            intent=result.intent,
            lang=result.lang_hint,
        )


def _send_to_api(
    prompt: str,
    session: ChatSession,
    risk_hint: str = "LOW",
    intent: str | None = None,
    lang: str = "unknown",
) -> None:
    metadata: dict = {"risk_hint": risk_hint}
    if intent:
        metadata["intent"] = intent
    if lang != "unknown":
        metadata["lang"] = lang

    start = time.perf_counter()
    response = api_ask(prompt, metadata)
    elapsed = (time.perf_counter() - start) * 1000
    session.message_count += 1

    if "error" in response and response.get("output") is None:
        print(c("red", f"  API ERROR: {response['error']}"))
        print(c("grey", "  (Uruchom: uvicorn apps.api.main:app --reload)"))
        return

    output = response.get("output") or response.get("detail") or str(response)
    route = response.get("route_decision", "")
    final = response.get("final_decision", "")

    label = c("cyan", "ALFA")
    print(f"  {label}: {output}")
    if route or final:
        print(c("grey", f"  [{route} → {final} | {elapsed:.0f}ms]"))


def _check_lockout(session: ChatSession) -> None:
    log = session.gate.audit_log()
    last = log[-1] if log else {}
    if last.get("event") == "lockout_applied":
        print(c("red", f"  ⛔  System zablokowany na {session.cfg.lockout_seconds:.0f}s po zbyt wielu błędach."))
        session.listening = False


if __name__ == "__main__":
    run()
