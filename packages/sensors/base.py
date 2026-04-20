from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum


class SensorKind(StrEnum):
    SCREEN = "screen"
    CAMERA = "camera"
    AUDIO = "audio"
    ACTIVITY = "activity"


class SensorStatus(StrEnum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    PERMISSION_DENIED = "permission_denied"
    DISABLED_BY_POLICY = "disabled_by_policy"


@dataclass(slots=True)
class SensorFrame:
    sensor: SensorKind
    timestamp: str
    payload: object  # raw data — bytes | str | dict
    meta: dict = field(default_factory=dict)

    @staticmethod
    def now() -> str:
        return datetime.now(UTC).isoformat()


class SensorError(RuntimeError):
    pass


class SensorPermissionError(SensorError):
    pass


class SensorUnavailableError(SensorError):
    pass


class BaseSensor(ABC):
    kind: SensorKind

    @abstractmethod
    def capture(self) -> SensorFrame:
        """Capture one frame from the sensor."""

    @abstractmethod
    def status(self) -> SensorStatus:
        """Check if the sensor is available and permitted."""

    def is_available(self) -> bool:
        return self.status() == SensorStatus.AVAILABLE
