from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


@dataclass(slots=True)
class AuditLogger:
    path: Path

    @staticmethod
    def prompt_hash(prompt: str) -> str:
        return hashlib.sha256(prompt.encode("utf-8")).hexdigest()

    def log(
        self,
        *,
        prompt: str,
        route_decision: str,
        final_decision: str,
        reason: str,
        source: str,
        duration_ms: int,
    ) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "timestamp": datetime.now(UTC).isoformat(),
            "prompt_hash": self.prompt_hash(prompt),
            "route_decision": route_decision,
            "final_decision": final_decision,
            "reason": reason,
            "source": source,
            "duration_ms": duration_ms,
        }
        with self.path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(record, ensure_ascii=True) + "\n")
