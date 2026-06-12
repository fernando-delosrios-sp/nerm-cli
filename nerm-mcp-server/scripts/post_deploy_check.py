from __future__ import annotations

import json
import sys
from pathlib import Path

from dotenv import load_dotenv
from nerm.health import get_health_report
from nerm.release_gate import (
    ReleaseGateResult,
    check_required_runtime_env,
    evaluate_health_report,
    has_any_tenant_credential_set,
)


def run_post_deploy_check() -> ReleaseGateResult:
    load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)
    missing_runtime = check_required_runtime_env()
    has_tenant_credentials = has_any_tenant_credential_set()
    health_report = get_health_report()
    health_ok, health_reason = evaluate_health_report(health_report)

    checks = {
        "missing_runtime_env": missing_runtime,
        "has_tenant_credentials": has_tenant_credentials,
        "health": health_report,
        "health_reason": health_reason,
    }
    ok = not missing_runtime and has_tenant_credentials and health_ok
    return ReleaseGateResult(ok=ok, checks=checks)


def main() -> None:
    result = run_post_deploy_check()
    print(json.dumps({"ok": result.ok, "checks": result.checks}, indent=2))
    if not result.ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
