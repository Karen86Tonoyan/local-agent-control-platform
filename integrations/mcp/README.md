# MCP Integration (Claude Desktop Operator)

This folder is the operator-facing MCP adapter for ALFA-CORE.

Scope:

- Claude Desktop connects to ALFA through MCP tools exposed here.
- Business logic stays in ALFA core modules under packages/.
- MCP layer must not execute business decisions on its own.

Hard rules:

- Tool access is allowlisted only.
- No sensitive logs on stdout.
- Adapter configuration comes from environment variables only.
- MCP adapter cannot bypass ALFA routing, policy, or audit.

Recommended MCP tool surface:

- alfa_health: reads ALFA health status.
- alfa_route: requests route + policy decision.
- alfa_ask: submits controlled model request through ALFA.
- alfa_audit_tail: reads recent audit records (redacted).

Required environment contract:

- ALFA_API_BASE_URL
- MCP_ALLOWED_TOOLS
- MCP_LOG_LEVEL
- MCP_REQUEST_TIMEOUT_SECONDS

Execution flow:

1. Claude Desktop calls an MCP tool.
2. MCP adapter forwards the request to ALFA API.
3. ALFA applies route, safety policy, model controller, and audit.
4. MCP adapter returns response to Claude Desktop.

This keeps Claude Desktop as an operator client, not a system brain.
