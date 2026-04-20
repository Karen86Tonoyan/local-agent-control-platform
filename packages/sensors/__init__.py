"""Sensors package — observation, capture, and activation layer."""
from packages.sensors.base import BaseSensor, SensorFrame, SensorKind, SensorStatus
from packages.sensors.activation import ActivationGate, ActivationState, ActivationDecision
from packages.sensors.voice_policy import (
    VoiceFlow,
    VoicePolicy,
    VoicePolicyConfig,
    CommandRisk,
    ConfirmationRequirement,
    ARMENIAN_COMMANDS,
    INTENT_RISK,
)

__all__ = [
    "BaseSensor",
    "SensorFrame",
    "SensorKind",
    "SensorStatus",
    "ActivationGate",
    "ActivationState",
    "ActivationDecision",
]
