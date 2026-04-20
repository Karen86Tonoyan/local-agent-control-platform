# ALFA-CORE Architecture

ALFA-CORE follows a safety-first backend kernel architecture.

Core flow:
Input -> Router -> Safety -> LLM/Action -> Output

Primary runtime components:

- apps/api: HTTP entrypoint
- packages/router: decision routing
- packages/safety: guardrails and policy checks
- packages/llm: model adapters
- packages/telemetry: audit logging
