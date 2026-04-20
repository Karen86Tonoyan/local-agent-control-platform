from __future__ import annotations

import os
import time
import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI

from packages.llm.ollama_client import OllamaClient
from packages.llm.ollama_controller import OllamaController
from packages.router.router import AlfaRouter
from packages.safety.policy import apply_policy
from packages.schemas.api import AnswerEnvelopeSchema, AskRequestSchema, RouteRequestSchema
from packages.telemetry.audit import AuditLogger

app = FastAPI(title="ALFA-CORE API", version="0.1.0")


router_engine = AlfaRouter()


def get_audit_logger() -> AuditLogger:
    path = Path(os.getenv("ALFA_AUDIT_LOG_PATH", "./logs/audit.jsonl"))
    return AuditLogger(path=path)


def get_ollama_client() -> OllamaClient:
    return OllamaClient(
        base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        model=os.getenv("OLLAMA_MODEL", "llama3.1"),
    )


def get_ollama_controller() -> OllamaController:
    return OllamaController(router=router_engine, client=get_ollama_client())


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/route", response_model=AnswerEnvelopeSchema)
def route(req: RouteRequestSchema) -> AnswerEnvelopeSchema:
    request_id = str(uuid.uuid4())
    start = time.perf_counter()
    route_decision = router_engine.route(req.prompt, req.metadata)

    policy = apply_policy(
        route_decision=route_decision,
        metadata={**req.metadata, "prompt": req.prompt},
    )

    duration_ms = int((time.perf_counter() - start) * 1000)
    get_audit_logger().log(
        prompt=req.prompt,
        route_decision=route_decision,
        final_decision=policy.final_decision,
        reason=policy.reason,
        source="api.route",
        duration_ms=duration_ms,
    )

    warnings: list[str] = []
    if policy.final_decision != route_decision:
        warnings.append(f"Policy overrode router decision: {route_decision} → {policy.final_decision}")

    return AnswerEnvelopeSchema(
        request_id=request_id,
        mode="route",
        decision=policy.final_decision,
        answer=None,
        citations=[],
        warnings=warnings,
        error=None,
    )


@app.post("/ask", response_model=AnswerEnvelopeSchema)
def ask(req: AskRequestSchema) -> AnswerEnvelopeSchema:
    request_id = str(uuid.uuid4())
    start = time.perf_counter()
    ask_result = get_ollama_controller().ask(prompt=req.prompt, metadata=req.metadata)

    duration_ms = int((time.perf_counter() - start) * 1000)
    get_audit_logger().log(
        prompt=req.prompt,
        route_decision=ask_result.route_decision,
        final_decision=ask_result.policy.final_decision,
        reason=(
            ask_result.policy.reason
            if not ask_result.error
            else f"{ask_result.policy.reason}; ollama_error={ask_result.error}"
        ),
        source="api.ask",
        duration_ms=duration_ms,
    )

    warnings: list[str] = []
    if ask_result.error:
        warnings.append(f"LLM error: {ask_result.error}")

    return AnswerEnvelopeSchema(
        request_id=request_id,
        mode="ask",
        decision=ask_result.policy.final_decision,
        answer=ask_result.output,
        citations=[],
        warnings=warnings,
        error=ask_result.error,
    )
