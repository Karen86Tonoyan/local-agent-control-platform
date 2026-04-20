from __future__ import annotations

import hashlib
import hmac
import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Callable


class ActivationState(StrEnum):
    IDLE = "IDLE"
    LISTENING = "LISTENING"
    AWAITING_L2 = "AWAITING_L2"
    AUTHENTICATED = "AUTHENTICATED"
    LOCKED = "LOCKED"


class ActivationDecision(StrEnum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    REQUIRE_L2 = "REQUIRE_L2"


# Armenian wake words — L1 trigger only, NOT authentication.
# This reduces accidental activation probability.
# It does NOT guarantee "only you" can activate.
DEFAULT_WAKE_WORDS: frozenset[str] = frozenset(
    {"հայկ", "alfa", "ալֆա"}
)

# Actions that ALWAYS require L2 confirmation regardless of L1 state.
# Maps to CommandRisk.HIGH / EXEC in voice_policy.py
HIGH_RISK_ACTIONS: frozenset[str] = frozenset(
    {"screenshot", "camera", "exec", "file_write", "network", "shell",
     "camera_request", "file_operation", "network_request", "send_data",
     "exec_request"}
)

# Defaults — overridden at runtime via VoicePolicyConfig.from_env()
MAX_FAILED_ATTEMPTS: int = 3
LOCKOUT_SECONDS: float = 300.0  # seconds; matches VOICE_LOCKOUT_SECONDS env var


@dataclass
class ActivationResult:
    state: ActivationState
    decision: ActivationDecision
    action: str
    reason: str
    timestamp: float = field(default_factory=time.time)
    requires_l2: bool = False


@dataclass
class ActivationGate:
    """
    L1 → L2 → L3 activation pipeline.

    L1: Armenian/custom wake word — reduces accidental triggers.
         NOT an authentication mechanism.
    L2: PIN hash check OR external speaker verifier callback.
         Required for all high-risk actions.
    L3: Handled by ALFA Router + Policy (called externally).

    Audit log is append-only. Every activation attempt is recorded.
    """

    wake_words: frozenset[str] = DEFAULT_WAKE_WORDS
    pin_hash: str = ""  # SHA-256 hex of the PIN; empty = L2 via verifier only
    speaker_verifier: Callable[[bytes], bool] | None = None
    high_risk_actions: frozenset[str] = HIGH_RISK_ACTIONS

    _failed_attempts: int = field(default=0, init=False, repr=False)
    _locked_until: float = field(default=0.0, init=False, repr=False)
    _state: ActivationState = field(default=ActivationState.IDLE, init=False, repr=False)
    _audit: list[dict] = field(default_factory=list, init=False, repr=False)

    # ------------------------------------------------------------------ #
    # Public interface                                                     #
    # ------------------------------------------------------------------ #

    def check_wake_word(self, text: str) -> bool:
        """L1: returns True if text contains a known wake word.
        This is a noise filter, not an auth check.
        """
        normalized = text.lower().strip()
        matched = any(w in normalized for w in self.wake_words)
        self._log("wake_word_check", {"text_len": len(normalized), "matched": matched})
        if matched:
            self._state = ActivationState.LISTENING
        return matched

    def request_action(self, action: str) -> ActivationResult:
        """Gate an action through L1+L2 state machine."""
        if self._is_locked():
            result = ActivationResult(
                state=ActivationState.LOCKED,
                decision=ActivationDecision.DENY,
                action=action,
                reason=f"Locked out for {self._remaining_lockout():.0f}s after repeated failures",
            )
            self._log("action_denied_locked", {"action": action})
            return result

        if self._state == ActivationState.IDLE:
            result = ActivationResult(
                state=ActivationState.IDLE,
                decision=ActivationDecision.DENY,
                action=action,
                reason="No active wake word detected; system is idle",
            )
            self._log("action_denied_idle", {"action": action})
            return result

        if action in self.high_risk_actions and self._state != ActivationState.AUTHENTICATED:
            self._state = ActivationState.AWAITING_L2
            result = ActivationResult(
                state=ActivationState.AWAITING_L2,
                decision=ActivationDecision.REQUIRE_L2,
                action=action,
                reason=f"High-risk action '{action}' requires L2 confirmation",
                requires_l2=True,
            )
            self._log("action_requires_l2", {"action": action})
            return result

        if self._state in {ActivationState.LISTENING, ActivationState.AUTHENTICATED}:
            result = ActivationResult(
                state=self._state,
                decision=ActivationDecision.ALLOW,
                action=action,
                reason="Action permitted by current activation state",
            )
            self._log("action_allowed", {"action": action})
            return result

        result = ActivationResult(
            state=self._state,
            decision=ActivationDecision.DENY,
            action=action,
            reason=f"Action not permitted in state {self._state}",
        )
        self._log("action_denied", {"action": action, "state": self._state})
        return result

    def confirm_l2_pin(self, pin: str) -> bool:
        """L2 via PIN. Increments failure counter and locks on excess."""
        if not self.pin_hash:
            self._log("l2_pin_skipped", {"reason": "no pin configured"})
            return False

        candidate = self._hash_pin(pin)
        ok = hmac.compare_digest(candidate, self.pin_hash)
        self._record_l2_attempt(ok)
        return ok

    def confirm_l2_voice(self, audio_bytes: bytes) -> bool:
        """L2 via external speaker verifier callback."""
        if self.speaker_verifier is None:
            self._log("l2_voice_skipped", {"reason": "no verifier configured"})
            return False

        ok: bool = False
        try:
            ok = self.speaker_verifier(audio_bytes)
        except Exception as exc:
            self._log("l2_voice_error", {"error": str(exc)})
        self._record_l2_attempt(ok)
        return ok

    def reset(self) -> None:
        """Return to IDLE; clears LISTENING/AUTHENTICATED state."""
        self._state = ActivationState.IDLE
        self._log("reset", {})

    def audit_log(self) -> list[dict]:
        """Returns a copy of the append-only audit log."""
        return list(self._audit)

    # ------------------------------------------------------------------ #
    # Internal helpers                                                    #
    # ------------------------------------------------------------------ #

    def _record_l2_attempt(self, success: bool) -> None:
        if success:
            self._failed_attempts = 0
            self._state = ActivationState.AUTHENTICATED
            self._log("l2_success", {})
        else:
            self._failed_attempts += 1
            self._log("l2_failure", {"attempts": self._failed_attempts})
            if self._failed_attempts >= MAX_FAILED_ATTEMPTS:
                self._locked_until = time.time() + LOCKOUT_SECONDS
                self._state = ActivationState.LOCKED
                self._log("lockout_applied", {"seconds": LOCKOUT_SECONDS})

    def _is_locked(self) -> bool:
        if self._state == ActivationState.LOCKED:
            if time.time() >= self._locked_until:
                self._state = ActivationState.IDLE
                self._failed_attempts = 0
                self._log("lockout_expired", {})
                return False
            return True
        return False

    def _remaining_lockout(self) -> float:
        return max(0.0, self._locked_until - time.time())

    @staticmethod
    def _hash_pin(pin: str) -> str:
        return hashlib.sha256(pin.encode("utf-8")).hexdigest()

    def _log(self, event: str, payload: dict) -> None:
        self._audit.append({"t": time.time(), "event": event, **payload})
