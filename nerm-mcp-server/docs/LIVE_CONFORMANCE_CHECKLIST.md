# Live Conformance Checklist

Use this checklist to validate the current implementation against a real NERM tenant before freezing a baseline.

## 1) Environment setup

- Activate virtualenv:
  - `source .venv/bin/activate`
- Ensure tenant creds are present in `.env` or exported:
  - `NERM_BASE_URL` (or `NERM_TENANT`)
  - `NERM_BEARER_TOKEN` (or `NERM_API_TOKEN`)
  - `NERM_API_BASE_PATH` (default `/api`)

Optional smoke flags:
- `NERM_SMOKE_ENABLE_ADVANCED_SEARCH=1`
- `NERM_SMOKE_ADVANCED_SEARCH_JSON='{"label":"smoke","condition_rules_attributes":[]}'`
- `NERM_SMOKE_ENABLE_ROLES=1`

## 2) Contract checks

Run from repo root:

```bash
make conformance-check
```

Expected:
- matrix sync tests pass
- HTTP contract tests pass
- HTTP client resilience tests pass (transport errors, retry/fail-fast, JSON handling)
- server bootstrap tests pass (FastMCP fallback + registration path)
- real-tenant smoke either passes or returns actionable route/payload diagnostics

## 3) Full regression checks

```bash
make full-check
```

Expected:
- all unit/integration tests pass
- any skipped tests are only env-gated live smokes

## 4) Endpoint conformance spot-check (live)

Validate these read paths in smoke output:
- `/profile_types`
- `/ne_attributes`
- `/profiles`
- `/users`
- `/delegations`
- `/identity_proofing_results`
- `/workflow_sessions`
- `/audit_events/query`

Validate these write/read contracts in unit HTTP contract tests:
- `PATCH /delegations/:id`
- `POST /workflow_sessions`
- `GET /job_status`
- `POST /advanced_search/run`

Validate these in-process chart contracts in unit tests:
- `nerm_generate_chart` returns image artifact path
- `embed_in_response=true` includes markdown
- `NERM_CHART_INCLUDE_BASE64=1` includes base64 data

## 5) Enum/value constraints

- Confirm `NERM_AUDIT_FILTER_ENUMS_JSON` reflects known valid values from your approved spec.
- Confirm invalid enum values fail preflight with `invalid_audit_query_spec`.
- Confirm workflow session status filtering rejects unknown values with `invalid_workflow_status`.

## 6) Baseline readiness criteria

Declare baseline-ready only when:
- `make conformance-check` passes against real tenant
- `make full-check` passes
- no speculative endpoint fallbacks remain
- tool/endpoint matrix is up to date
- CI workflow (`.github/workflows/ci.yml`) is green on current branch
- container image builds and health check reports `status=ok`
