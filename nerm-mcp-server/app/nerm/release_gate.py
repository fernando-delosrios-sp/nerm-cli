from __future__ import annotations

import os
from dataclasses import dataclass

from nerm.config import get_settings


REQUIRED_RUNTIME_ENV_KEYS = ("NERM_API_BASE_PATH",)
REQUIRED_TENANT_ENV_KEY_SETS = (
    ("NERM_BASE_URL", "NERM_BEARER_TOKEN"),
    ("NERM_TENANT", "NERM_API_TOKEN"),
)


@dataclass
class ReleaseGateResult:
    ok: bool
    checks: dict[str, object]


def check_required_runtime_env(env: dict[str, str] | None = None) -> list[str]:
    if env is not None:
        source = env
    else:
        settings = get_settings()
        source = {
            "NERM_API_BASE_PATH": settings.nerm_api_base_path,
        }
    missing = [key for key in REQUIRED_RUNTIME_ENV_KEYS if not str(source.get(key, "")).strip()]
    return missing


def has_any_tenant_credential_set(env: dict[str, str] | None = None) -> bool:
    if env is not None:
        source = env
    else:
        settings = get_settings()
        source = {
            "NERM_BASE_URL": settings.nerm_base_url,
            "NERM_BEARER_TOKEN": settings.nerm_bearer_token,
            "NERM_TENANT": settings.nerm_base_url,
            "NERM_API_TOKEN": settings.nerm_bearer_token,
        }
    for keys in REQUIRED_TENANT_ENV_KEY_SETS:
        if all(str(source.get(key, "")).strip() for key in keys):
            return True
    return False


def evaluate_health_report(report: dict[str, object]) -> tuple[bool, str]:
    if report.get("status") != "ok":
        return False, "health status is not ok"
    tool_count = report.get("tool_count")
    if not isinstance(tool_count, int) or tool_count <= 0:
        return False, "tool_count is missing or invalid"
    return True, "healthy"
