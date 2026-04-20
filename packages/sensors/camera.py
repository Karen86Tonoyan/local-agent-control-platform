from __future__ import annotations

import importlib
from dataclasses import dataclass, field

from .base import BaseSensor, SensorFrame, SensorKind, SensorPermissionError, SensorStatus, SensorUnavailableError


@dataclass(slots=True)
class CameraSensor(BaseSensor):
    kind: SensorKind = SensorKind.CAMERA
    device_index: int = 0
    _cap: object = field(default=None, init=False, repr=False)

    def status(self) -> SensorStatus:
        if importlib.util.find_spec("cv2") is None:
            return SensorStatus.UNAVAILABLE
        return SensorStatus.AVAILABLE

    def capture(self) -> SensorFrame:
        if self.status() != SensorStatus.AVAILABLE:
            raise SensorUnavailableError("CameraSensor: opencv-python not installed; run pip install opencv-python")

        import cv2  # type: ignore[import-untyped]

        cap = cv2.VideoCapture(self.device_index)
        if not cap.isOpened():
            raise SensorPermissionError(f"CameraSensor: cannot open device {self.device_index}")

        try:
            ret, frame = cap.read()
            if not ret or frame is None:
                raise SensorUnavailableError("CameraSensor: no frame returned from device")

            ok, buf = cv2.imencode(".png", frame)
            if not ok:
                raise SensorUnavailableError("CameraSensor: failed to encode frame")

            h, w = frame.shape[:2]
            return SensorFrame(
                sensor=self.kind,
                timestamp=SensorFrame.now(),
                payload=bytes(buf),
                meta={"width": w, "height": h, "device": self.device_index},
            )
        finally:
            cap.release()
