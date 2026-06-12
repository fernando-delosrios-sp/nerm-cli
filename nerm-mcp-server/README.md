# NERM MCP Server

Platform-agnostic MCP server for SailPoint NERM administration.

## Local setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## Runtime

- Default transport: `stdio`
- Optional network transport: `streamable-http` (SSE)
- Configuration source: environment variables only

## Run MCP locally

From the `nerm-mcp-server` directory, start the server from the `app` module directory.

### 1) Configure environment

```bash
cd nerm-mcp-server
source .venv/bin/activate
export NERM_BASE_URL="https://tenant.example.com"
export NERM_API_BASE_PATH="/api"
export NERM_BEARER_TOKEN="Bearer eyJ..."
```

### 2) Run over stdio (default)

```bash
cd app
export NERM_TRANSPORT=stdio
python -m main
```

### 3) Run over streamable-http

```bash
cd app
export NERM_TRANSPORT=streamable-http
export NERM_HTTP_HOST=127.0.0.1
export NERM_HTTP_PORT=8080
python -m main
```

Or from repo root, use the helper script:

```bash
./nerm-mcp-server/scripts/start-local.sh
```

Notes:
- `stdio` is best for local MCP clients launched as subprocesses.
- `streamable-http` is best for network clients and manual endpoint testing.
- Optional request payload logging: `export NERM_DEBUG_LOG_BODIES=1` (disable when not needed).

## Real tenant smoke validation

Set tenant credentials through environment variables (either naming set works):

- `NERM_BASE_URL` or `NERM_TENANT`
- `NERM_BEARER_TOKEN` or `NERM_API_TOKEN`

Example:

```bash
export NERM_BASE_URL="https://tenant.example.com"
export NERM_API_BASE_PATH="/api"
export NERM_BEARER_TOKEN="Bearer eyJ..."
source .venv/bin/activate
python -m pytest nerm-mcp-server/tests/integration/test_real_tenant_smoke.py -q
```

Notes:
- The smoke suite is safe to keep in CI because it auto-skips when tenant credentials are not set.
- It validates live behavior for profile types, attributes, profiles, users, delegations, workflow reads, and verifies cached reference lookups avoid a second upstream call.
- It also includes a read-only audit query smoke check.
- Advanced-search smoke is opt-in and guarded to avoid broad queries. Enable it only with constrained payloads:

```bash
export NERM_SMOKE_ENABLE_ADVANCED_SEARCH=1
export NERM_SMOKE_ADVANCED_SEARCH_JSON='{"label":"smoke","condition_rules_attributes":[]}'
python -m pytest nerm-mcp-server/tests/integration/test_real_tenant_smoke.py -q -rs
```

Roles-domain smoke is also opt-in (read-only list checks):

```bash
export NERM_SMOKE_ENABLE_ROLES=1
python -m pytest nerm-mcp-server/tests/integration/test_real_tenant_smoke.py -q -rs
```

Get-by-id smoke is opt-in (read-only detail endpoint checks from discovered IDs):

```bash
export NERM_SMOKE_ENABLE_GET_BY_ID=1
python -m pytest nerm-mcp-server/tests/integration/test_real_tenant_smoke.py -q -rs
```

Write smoke is opt-in and requires explicit payloads (dangerous in shared tenants):

```bash
export NERM_SMOKE_ENABLE_WRITES=1
export NERM_SMOKE_CREATE_DELEGATION_JSON='{"delegator_id":"<id>","delegate_id":"<id>"}'
export NERM_SMOKE_WORKFLOW_SUBMIT_JSON='{"workflow_id":"<workflow-id>","name":"Smoke submit"}'
python -m pytest nerm-mcp-server/tests/integration/test_real_tenant_smoke.py -q -rs
```

Audit query enum validation:
- You can enforce spec-known allowed values per audit filter by setting `NERM_AUDIT_FILTER_ENUMS_JSON`.
- Example:

```bash
export NERM_AUDIT_FILTER_ENUMS_JSON='{"subject_type":["WorkflowSession","Profile"],"type":["Get","Post","Patch","Delete"]}'
```

## Conformance check

From repo root:

```bash
make conformance-check
```

This runs:
- tool/endpoint matrix sync tests
- HTTP contract tests
- real-tenant smoke suite (auto-skips when tenant env is not set)

Full regression suite:

```bash
make full-check
```

Release readiness gate:

```bash
make release-readiness
```

Phase 3 rollout gate (includes post-deploy checks):

```bash
make phase3-readiness
```

## Local test agent chat

You can run a separate local test agent that talks to this MCP server over stdio:

```bash
source .venv/bin/activate
python nerm-mcp-server/scripts/test_agent_chat.py
```

Inside the chat:
- `/tools` to list tools
- `/call <tool_name> <json_args>` to invoke a specific tool
- plain English prompts for heuristic tool suggestions

For a tenant-ready validation flow, use:
- `docs/LIVE_CONFORMANCE_CHECKLIST.md`
- `docs/RELEASE_CHECKLIST.md`

## Container runtime

Build from repo root:

```bash
docker build -t nerm-agent:local .
```

Run with env file:

```bash
docker run --rm --env-file nerm-mcp-server/.env nerm-agent:local
```

The container health check executes:
- `from nerm.health import get_health_report`
- exits healthy only when startup validation and tool bootstrap succeed.

## CI gate

GitHub Actions workflow at `.github/workflows/ci.yml` runs:
- `make conformance-check`
- `make full-check`
