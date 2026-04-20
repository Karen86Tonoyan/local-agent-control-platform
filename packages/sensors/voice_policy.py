"""
voice_policy.py — PRIVATE_ARMENIAN operator mode

Security model:
  L1: Wake word (Armenian phrase) — switches system to LISTENING.
      NOT an authentication mechanism. Reduces accidental activation only.
  L2: Confirmation — required for MEDIUM (policy-dependent) and all HIGH/EXEC.
  L3: ALFA Router + Safety Policy gate (called externally).
  L4: Audit — every event logged, no exceptions.

Armenian wake word does NOT grant access rights on its own.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Literal


# ---------------------------------------------------------------------------
# Risk classification
# ---------------------------------------------------------------------------

class CommandRisk(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    EXEC = "EXEC"


class ConfirmationRequirement(StrEnum):
    NONE = "NONE"           # proceed after wake word
    SOFT = "SOFT"           # optional / policy-dependent
    REQUIRED = "REQUIRED"   # must confirm before proceeding
    BLOCKED = "BLOCKED"     # no execution path without full auth


# ---------------------------------------------------------------------------
# Armenian intent dictionary
# Mapping: recognized phrase -> intent token (NOT direct action)
# ALFA policy decides whether the intent is allowed.
# ---------------------------------------------------------------------------

ARMENIAN_COMMANDS: dict[str, str] = {
    "արեջ լուսին": "camera_request",
    "էկրանի նկար": "screenshot_request",
    "ինչ ես տեսնում": "analyze_view",
    "վերջ": "stop_session",
    "օգնիր": "help_request",
    "կարգավիճակ": "status_check",
    "կատարիր": "exec_request",     # HIGH / EXEC — always blocked without auth
    "ֆայլ": "file_operation",       # HIGH — requires confirmation
    "ցանց": "network_request",      # HIGH — requires confirmation
    "ուղարկիր": "send_data",        # HIGH — requires confirmation
}

# Risk level for each intent token.
# Unrecognized intents default to MEDIUM (conservative).
INTENT_RISK: dict[str, CommandRisk] = {
    "help_request":     CommandRisk.LOW,
    "analyze_view":     CommandRisk.LOW,
    "stop_session":     CommandRisk.LOW,
    "status_check":     CommandRisk.MEDIUM,
    "screenshot_request": CommandRisk.MEDIUM,
    "camera_request":   CommandRisk.HIGH,
    "file_operation":   CommandRisk.HIGH,
    "network_request":  CommandRisk.HIGH,
    "send_data":        CommandRisk.HIGH,
    "exec_request":     CommandRisk.EXEC,
}


# ---------------------------------------------------------------------------
# Policy configuration — read from environment
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class VoicePolicyConfig:
    mode: str = "PRIVATE_ARMENIAN"
    wake_word: str = "Հայկ"
    voice_lang: str = "pl-PL"
    alt_voice_lang: str = "hy-AM"
    require_confirm_for_high_risk: bool = True
    allow_exec_after_voice: bool = False
    audit_enabled: bool = True
    max_failed_attempts: int = 3
    lockout_seconds: float = 300.0

    @classmethod
    def from_env(cls) -> "VoicePolicyConfig":
        def _bool(key: str, default: bool) -> bool:
            val = os.environ.get(key, "").strip().lower()
            if val in {"true", "1", "yes"}:
                return True
            if val in {"false", "0", "no"}:
                return False
            return default

        return cls(
            mode=os.environ.get("VOICE_MODE", "PRIVATE_ARMENIAN"),
            wake_word=os.environ.get("ARMENIAN_ACTIVATION", "Հայկ"),
            voice_lang=os.environ.get("VOICE_LANG", "pl-PL"),
            alt_voice_lang=os.environ.get("ALT_VOICE_LANG", "hy-AM"),
            require_confirm_for_high_risk=_bool("REQUIRE_CONFIRM_FOR_HIGH_RISK", True),
            allow_exec_after_voice=_bool("ALLOW_EXEC_AFTER_VOICE", False),
            audit_enabled=_bool("VOICE_AUDIT", True),
            max_failed_attempts=int(os.environ.get("VOICE_MAX_FAILED_ATTEMPTS", "3")),
            lockout_seconds=float(os.environ.get("VOICE_LOCKOUT_SECONDS", "300")),
        )


# ---------------------------------------------------------------------------
# Policy decision
# ---------------------------------------------------------------------------

@dataclass
class PolicyDecision:
    intent: str
    risk: CommandRisk
    confirmation: ConfirmationRequirement
    reason: str
    allowed: bool

    def requires_confirmation(self) -> bool:
        return self.confirmation in {
            ConfirmationRequirement.SOFT,
            ConfirmationRequirement.REQUIRED,
        }


class VoicePolicy:
    """
    Classifies an intent token and returns the policy decision.

    Rules (PRIVATE_ARMENIAN mode):
      LOW   -> ALLOW, no confirmation required
      MEDIUM -> ALLOW, soft confirmation (policy-dependent)
      HIGH  -> ALLOW only after REQUIRED confirmation
      EXEC  -> BLOCKED unless allow_exec_after_voice is explicitly True
               and confirmation is provided (default: always BLOCKED)
    """

    def __init__(self, config: VoicePolicyConfig | None = None) -> None:
        self.config = config or VoicePolicyConfig.from_env()

    def evaluate(self, intent: str) -> PolicyDecision:
        risk = INTENT_RISK.get(intent, CommandRisk.MEDIUM)

        if risk == CommandRisk.LOW:
            return PolicyDecision(
                intent=intent,
                risk=risk,
                confirmation=ConfirmationRequirement.NONE,
                reason="Low-risk intent, permitted after wake word",
                allowed=True,
            )

        if risk == CommandRisk.MEDIUM:
            return PolicyDecision(
                intent=intent,
                risk=risk,
                confirmation=ConfirmationRequirement.SOFT,
                reason="Medium-risk intent, policy may request soft confirmation",
                allowed=True,
            )

        if risk == CommandRisk.HIGH:
            if not self.config.require_confirm_for_high_risk:
                return PolicyDecision(
                    intent=intent,
                    risk=risk,
                    confirmation=ConfirmationRequirement.NONE,
                    reason="High-risk intent, confirmation disabled by config (not recommended)",
                    allowed=True,
                )
            return PolicyDecision(
                intent=intent,
                risk=risk,
                confirmation=ConfirmationRequirement.REQUIRED,
                reason=f"High-risk intent '{intent}' requires explicit confirmation",
                allowed=False,  # allowed=True only after confirmation is provided
            )

        # EXEC
        if self.config.allow_exec_after_voice:
            return PolicyDecision(
                intent=intent,
                risk=risk,
                confirmation=ConfirmationRequirement.REQUIRED,
                reason="EXEC intent: confirmation required (allow_exec_after_voice=True)",
                allowed=False,
            )

        return PolicyDecision(
            intent=intent,
            risk=risk,
            confirmation=ConfirmationRequirement.BLOCKED,
            reason="EXEC and system operations are blocked; full authentication required",
            allowed=False,
        )

    def resolve_intent(self, text: str) -> str | None:
        """
        Resolve raw text (in any supported language) to an intent token.
        Returns None if no intent is recognized.
        """
        normalized = text.lower().strip()
        # Direct Armenian phrase lookup
        for phrase, intent in ARMENIAN_COMMANDS.items():
            if phrase in normalized:
                return intent
        return None


# ---------------------------------------------------------------------------
# Flow entry point
# ---------------------------------------------------------------------------

@dataclass
class VoiceFlowResult:
    text: str
    intent: str | None
    decision: PolicyDecision | None
    wake_word_matched: bool
    lang_hint: Literal["pl-PL", "hy-AM", "unknown"]
    audit_event: dict = field(default_factory=dict)


class VoiceFlow:
    """
    Top-level voice flow for PRIVATE_ARMENIAN mode.

    Usage:
        flow = VoiceFlow()
        result = flow.process(text="Հայկ, zrób screenshot")
    """

    def __init__(self, config: VoicePolicyConfig | None = None) -> None:
        self.config = config or VoicePolicyConfig.from_env()
        self.policy = VoicePolicy(self.config)

    def process(self, text: str, already_listening: bool = False) -> VoiceFlowResult:
        """
        Process one utterance through the full L1→L2-prep flow.

        already_listening=True skips wake word check (gate is already open).
        """
        import time

        normalized = text.lower().strip()
        wake_word = self.config.wake_word.lower()
        wake_matched = wake_word in normalized or already_listening

        if not wake_matched:
            audit = _build_audit(
                text=text,
                wake_matched=False,
                intent=None,
                risk=None,
                confirmation=None,
                final="IGNORED",
                lang=self._detect_lang(text),
            )
            return VoiceFlowResult(
                text=text,
                intent=None,
                decision=None,
                wake_word_matched=False,
                lang_hint=self._detect_lang(text),
                audit_event=audit,
            )

        intent = self.policy.resolve_intent(normalized)
        lang = self._detect_lang(text)

        if intent is None:
            audit = _build_audit(
                text=text,
                wake_matched=True,
                intent=None,
                risk=None,
                confirmation=None,
                final="UNRECOGNIZED",
                lang=lang,
            )
            return VoiceFlowResult(
                text=text,
                intent=None,
                decision=None,
                wake_word_matched=True,
                lang_hint=lang,
                audit_event=audit,
            )

        decision = self.policy.evaluate(intent)
        final = "BLOCKED" if decision.confirmation == ConfirmationRequirement.BLOCKED else (
            "ALLOWED" if decision.confirmation == ConfirmationRequirement.NONE else
            "REQUIRES_CONFIRMATION"
        )

        audit = _build_audit(
            text=text,
            wake_matched=True,
            intent=intent,
            risk=decision.risk,
            confirmation=decision.confirmation,
            final=final,
            lang=lang,
        )

        return VoiceFlowResult(
            text=text,
            intent=intent,
            decision=decision,
            wake_word_matched=True,
            lang_hint=lang,
            audit_event=audit,
        )

    def _detect_lang(self, text: str) -> Literal["pl-PL", "hy-AM", "unknown"]:
        """Heuristic: Armenian Unicode block = hy-AM, else pl-PL or unknown."""
        if any("\u0531" <= ch <= "\u058F" for ch in text):
            return "hy-AM"
        if any(ch in text for ch in "ąćęłńóśźżĄĆĘŁŃÓŚŹŻ"):
            return "pl-PL"
        return "unknown"


def _build_audit(
    *,
    text: str,
    wake_matched: bool,
    intent: str | None,
    risk: CommandRisk | None,
    confirmation: ConfirmationRequirement | None,
    final: str,
    lang: str,
) -> dict:
    import hashlib
    import time

    return {
        "timestamp": time.time(),
        "wake_word_matched": wake_matched,
        "recognized_text_hash": hashlib.sha256(text.encode()).hexdigest()[:16],
        "language_mode": lang,
        "intent": intent,
        "risk_level": risk.value if risk else None,
        "confirmation_required": confirmation not in {None, ConfirmationRequirement.NONE},
        "final_action": final,
        "result": final,
    }
