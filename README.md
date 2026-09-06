# ALFA Core

> **Experimental local Python kernel for routing, policy checks, model clients and audit envelopes**

ALFA Core is organised as a Python package with separate API, CLI and chat
entry points. It exposes a small FastAPI service and contains modules for
routing, safety policy, model controllers, command execution, sensors, memory
and audit telemetry.

## Architecture

```text
apps/api/             FastAPI application and module entry point
apps/cli/, apps/chat/ command-line entry points
packages/router/      prompt routing
packages/safety/      policy handling
packages/llm/         Ollama, OpenAI and Claude client modules
packages/telemetry/   audit support
packages/sensors/     camera, screen, audio and voice-policy abstractions
tests/unit/           unit tests for contracts and policy
```

## Requirements and startup

Python 3.11+ is required. The declared dependencies are FastAPI, Uvicorn and
Pydantic:

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -e .
python -m apps.api
```

The API entry point starts Uvicorn on port 8000. The project also includes
PowerShell scripts in `scripts/` for bootstrap, development, lint and test
tasks.

## Configuration

`.env.example` documents local Ollama settings, audit location, command
whitelist, optional OpenAI/Anthropic settings and voice-policy settings. Copy
it to a local `.env`, replace only needed placeholders and keep all credentials
out of Git. Review the command whitelist and confirmation flags before
enabling execution-related code.

## Status and safety

The repository is in a canonical-migration phase according to its existing
documentation. Sensors, model calls and command pathways must be explicitly
configured and tested. Policy decisions and audit records are development
features; they do not guarantee safe execution or protect against all harmful
input.

## Licence

`LICENSE` is MIT.
