# NERM MCP Server Release Checklist

Use this checklist when promoting a branch to release.

## 1) Branch and CI

- Pull request is up to date with base branch.
- `.github/workflows/ci.yml` is green for the release commit.
- Required checks are configured in repository settings:
  - `CI / test`
- Branch protection is enabled for the default branch:
  - require pull request before merge
  - require status checks to pass
  - include `CI / test` in required checks

## 2) Local verification

From repository root:

```bash
make release-readiness
make phase3-readiness
```

Expected outcome:
- startup/health unit checks pass
- conformance checks pass
- full regression suite passes
- post-deploy check script reports `ok=true`

## 3) Tenant conformance

- Real-tenant smoke checks are executed with approved tenant credentials.
- Any write-smoke skips are understood and accepted (idempotent duplicate delegation case).

## 4) Container validation

```bash
make docker-build
docker run --rm --env-file nerm-mcp-server/.env nerm-agent:local
```

Verify:
- process starts cleanly
- startup validation passes
- health report returns `status=ok`

## 5) Documentation

- `docs/TOOL_ENDPOINT_MATRIX.md` is up to date with current tool contracts.
- `docs/LIVE_CONFORMANCE_CHECKLIST.md` reflects current validation process.
- `docs/OPERATIONS_RUNBOOK.md` includes latest deployment/triage guidance.

## 6) Release handoff

- Known risks and tenant-specific caveats are noted in release notes.
- Rollback approach is documented (previous image tag or commit SHA).
