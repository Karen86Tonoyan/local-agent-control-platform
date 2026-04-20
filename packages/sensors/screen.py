from __future__ import annotations

import importlib
from dataclasses import dataclass

from .base import BaseSensor, SensorFrame, SensorKind, SensorStatus, SensorUnavailableError


@dataclass(slots=True)
class ScreenSensor(BaseSensor):
    kind: SensorKind = SensorKind.SCREEN
    region: tuple[int, int, int, int] | None = None  # (x, y, w, h) or None for fullscreen

    def status(self) -> SensorStatus:
        if importlib.util.find_spec("PIL") is None:
            return SensorStatus.UNAVAILABLE
        return SensorStatus.AVAILABLE

    def capture(self) -> SensorFrame:
        if self.status() != SensorStatus.AVAILABLE:
            raise SensorUnavailableError("ScreenSensor: Pillow not installed; run pip install Pillow")

        from PIL import ImageGrab  # type: ignore[import-untyped]

        screenshot = ImageGrab.grab(bbox=self.region)
        import io
        buf = io.BytesIO()
        screenshot.save(buf, format="PNG")
        raw = buf.getvalue()

        return SensorFrame(
            sensor=self.kind,
            timestamp=SensorFrame.now(),
            payload=raw,
            meta={
                "width": screenshot.width,
                "height": screenshot.height,
                "region": self.region,
            },
        )
