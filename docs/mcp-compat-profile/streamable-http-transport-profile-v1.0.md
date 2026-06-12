# Streamable HTTP Transport Profile v1.0

Status: Published  
Applies to: `tool-nerm-mcp-server` when `NERM_TRANSPORT=streamable-http`

## Endpoint

- Base MCP endpoint: `/mcp`

## Required Headers (Client -> Server)

- `Content-Type: application/json`
- `Accept: application/json, text/event-stream` (recommended for broad compatibility)

## Session Flow

1. Client initializes transport/session with POST `/mcp`.
2. Client continues session calls as required by MCP streamable-http manager.
3. Client terminates session with DELETE `/mcp` when complete.

## Expected Status Codes

- `200 OK`: normal MCP request/response handling.
- `202 Accepted`: async/stream progression response in streamable mode.
- `404 Not Found`: endpoint mismatch or invalid/nonexistent session route/state.
- `4xx`: malformed request headers/body/negotiation.
- `5xx`: server/runtime failures.

## Client Guidance

- Treat `404` during session operations as possible session invalidation; re-init transport.
- Implement bounded retries with backoff for transient failures.
- Parse SSE/event-stream as framed events (not line-by-line ad hoc parsing).

## Server Guidance

- Keep endpoint behavior stable (`/mcp`) across versions.
- Document changes in session semantics as profile/version updates.
