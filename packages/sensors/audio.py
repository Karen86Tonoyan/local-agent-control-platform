from __future__ import annotations

import importlib
from dataclasses import dataclass, field

from .base import BaseSensor, SensorFrame, SensorKind, SensorStatus, SensorUnavailableError


@dataclass(slots=True)
class AudioSensor(BaseSensor):
    """Captures a short audio chunk from the microphone.

    This is a raw capture sensor only. It does NOT perform STT,
    wake-word detection, or speaker verification. Those happen in
    the observation pipeline above this layer.
    """

    kind: SensorKind = SensorKind.AUDIO
    duration_seconds: float = 3.0
    sample_rate: int = 16000
    channels: int = 1
    chunk_size: int = 1024

    def status(self) -> SensorStatus:
        if importlib.util.find_spec("sounddevice") is None:
            return SensorStatus.UNAVAILABLE
        return SensorStatus.AVAILABLE

    def capture(self) -> SensorFrame:
        if self.status() != SensorStatus.AVAILABLE:
            raise SensorUnavailableError(
                "AudioSensor: sounddevice not installed; run pip install sounddevice"
            )

        import sounddevice as sd  # type: ignore[import-untyped]
        import numpy as np

        samples = sd.rec(
            int(self.duration_seconds * self.sample_rate),
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype="int16",
        )
        sd.wait()

        raw: bytes = samples.tobytes()
        peak = int(np.abs(samples).max())

        return SensorFrame(
            sensor=self.kind,
            timestamp=SensorFrame.now(),
            payload=raw,
            meta={
                "sample_rate": self.sample_rate,
                "channels": self.channels,
                "duration_seconds": self.duration_seconds,
                "peak_amplitude": peak,
            },
        )
