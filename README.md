# ALFA-CORE

> **Status: canonical migration in progress.**
> Core Python backend is the source of truth. Legacy TypeScript `src/` is in compatibility-only mode — no new domain logic added there.

ALFA-CORE is the backend kernel for the ALFA system: decision routing, safety guardrails, local LLM integration, and audit telemetry.

## What works now

- `GET /health` — liveness check
- `POST /route` — routes a prompt through router + safety policy, returns `AnswerEnvelope`
- `POST /ask` — routes prompt, calls Ollama, returns `AnswerEnvelope`
- Operator CLI: `bootstrap`, `smoke`, `doctor`
- 57 passing unit tests (router, safety, ollama_client, audit, API contract)

## Response contract (all endpoints)

```json
{
  "request_id": "uuid",
  "mode": "route|ask|explain|find-bug|next-step",
  "decision": "ACCEPT|VERIFY|SIMULATE|ESCALATE|BLOCK",
  "answer": "string or null",
  "citations": [],
  "warnings": [],
  "error": "string or null"
}
```

`warnings` is always a list. `error` is always present, `null` on success.

## Quickstart

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .

# operator checks
python -m apps.cli bootstrap
python -m apps.cli doctor

# run API
python -m apps.api
```

## Repo policy

- One canonical repo. No `-new`, `-v2`, `-final-final` copies.
- Experiments go to `labs/` or a branch only.
- `.venv/` and archives are not committed.
- New domain logic goes to `packages/` (Python) only.

## Architecture

```
Input → Router → Safety → LLM → Output
```

See `docs/architecture.md`, `docs/routing.md`, `docs/safety-model.md`, `docs/threat-model.md`.
