# NERM MCP Server Operations Runbook

## Purpose

Operational guide for deploying, validating, and triaging the NERM MCP server in runtime environments.

## Deployment

1. Build image from repo root:
   - `docker build -t nerm-agent:local .`
2. Provide runtime environment values:
   - `NERM_BASE_URL` (or `NERM_TENANT`)
   - `NERM_BEARER_TOKEN` (or `NERM_API_TOKEN`)
   - `NERM_API_BASE_PATH` (default `/api`)
3. Start container:
   - `docker run --rm --env-file nerm-mcp-server/.env nerm-agent:local`

## Startup Validation

Startup fails fast when:
- `NERM_TRANSPORT` is unsupported
- `NERM_HTTP_PORT` is outside `1..65535`
- `NERM_API_BASE_PATH` is empty or does not start with `/`

## Health Verification

Container health uses:
- `python -c "from nerm.health import get_health_report; ..."`

Healthy report fields:
- `status = ok`
- `transport`
- `host`
- `port`
- `tool_count`

## CI Requirements

The CI workflow must pass:
- `make conformance-check`
- `make full-check`
- `make release-readiness`

## Incident Triage

1. Confirm env configuration and startup validation error messages.
2. Run local checks:
   - `make conformance-check`
   - `make full-check`
3. For tenant issues, run:
   - `python -m pytest nerm-mcp-server/tests/integration/test_real_tenant_smoke.py -q -rs`
4. Check returned structured tool errors:
   - `nerm_api_error` with `status` and `body`
   - `invalid_*_spec` validation errors with `details`

## HTTP Diagnostics

Use these env flags for deeper request logging:
- `NERM_DEBUG_LOG_BODIES=1` enables request/response body previews
- `NERM_TRACE_MAX_BYTES=<n>` caps logged body size (default `4096`)

Notes:
- logs are emitted on logger `nerm.http`
- body previews are truncated with `...<truncated>` when over limit
