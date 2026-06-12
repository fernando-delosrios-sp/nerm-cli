import json
import logging
from collections.abc import Callable
from functools import wraps
from inspect import signature
from typing import Any

from mcp.server.fastmcp import Context
from mcp.types import CallToolResult, TextContent
from nerm.auth import resolve_auth
from nerm.config import get_settings
from nerm.tools.advanced_search import nerm_run_advanced_search
from nerm.tools.attributes import nerm_get_attribute, nerm_list_attributes
from nerm.tools.audit import nerm_query_audit_events
from nerm.tools.charts import nerm_generate_chart
from nerm.tools.datetime_tools import nerm_get_current_date_time
from nerm.tools.delegations import (
    nerm_create_delegation,
    nerm_delete_delegation,
    nerm_get_delegation,
    nerm_list_delegations,
    nerm_update_delegation,
)
from nerm.tools.identity_proofing import nerm_list_identity_proofing_results
from nerm.tools.profile_types import nerm_get_profile_type, nerm_list_profile_types
from nerm.tools.profiles import nerm_get_profile, nerm_list_profiles
from nerm.tools.roles import (
    nerm_get_role,
    nerm_get_role_profile,
    nerm_list_role_profiles,
    nerm_list_roles,
)
from nerm.tools.users import (
    nerm_examine_jwt_user,
    nerm_get_user,
    nerm_get_user_manager,
    nerm_get_user_profile,
    nerm_get_user_role,
    nerm_list_user_managers,
    nerm_list_user_profiles,
    nerm_list_user_roles,
    nerm_list_users,
)
from nerm.tools.workflow import (
    nerm_add_department_via_workflow,
    nerm_add_location_via_workflow,
    nerm_add_organization_via_workflow,
    nerm_get_job_status,
    nerm_get_workflow_session,
    nerm_list_workflow_session_statuses,
    nerm_list_workflow_sessions,
)

_LOGGER = logging.getLogger("nerm.tools")
_SENSITIVE_KEYWORDS = ("authorization", "token", "secret", "password", "api_key")


def _sanitize_for_logging(payload: object) -> object:
    model_dump = getattr(payload, "model_dump", None)
    if callable(model_dump):
        try:
            return _sanitize_for_logging(model_dump(mode="json"))
        except Exception:  # noqa: BLE001
            return str(payload)
    if isinstance(payload, (bytes, bytearray, memoryview)):
        return f"<binary:{len(payload)} bytes>"
    if isinstance(payload, dict):
        is_image_block = str(payload.get("type", "")).lower() == "image"
        is_text_block = str(payload.get("type", "")).lower() == "text"
        sanitized: dict[object, object] = {}
        for key, value in payload.items():
            if is_image_block and str(key) == "data" and isinstance(value, str):
                sanitized[key] = f"<base64_image len={len(value)}>"
            elif is_text_block and str(key) == "text" and isinstance(value, str):
                try:
                    parsed_text = json.loads(value)
                    sanitized[key] = json.dumps(_redact_sensitive(parsed_text), default=str)
                except Exception:  # noqa: BLE001
                    sanitized[key] = value
            else:
                sanitized[key] = _sanitize_for_logging(value)
        return sanitized
    if isinstance(payload, list):
        return [_sanitize_for_logging(item) for item in payload]
    if isinstance(payload, tuple):
        return tuple(_sanitize_for_logging(item) for item in payload)
    if hasattr(payload, "to_image_content"):
        return "<mcp_image_content>"
    if hasattr(payload, "to_audio_content"):
        return "<mcp_audio_content>"
    return payload


def _redact_sensitive(payload: object) -> object:
    payload = _sanitize_for_logging(payload)
    if isinstance(payload, dict):
        redacted: dict[object, object] = {}
        for key, value in payload.items():
            key_text = str(key).lower()
            if any(keyword in key_text for keyword in _SENSITIVE_KEYWORDS):
                redacted[key] = "<redacted>"
            else:
                redacted[key] = _redact_sensitive(value)
        return redacted
    if isinstance(payload, list):
        return [_redact_sensitive(item) for item in payload]
    return payload


def _truncate(text: str) -> str:
    limit = max(128, get_settings().nerm_trace_max_bytes)
    if len(text) <= limit:
        return text
    return text[:limit] + "...<truncated>"


def _serialize_output(payload: object) -> str:
    safe_payload = _redact_sensitive(payload)
    try:
        raw = json.dumps(safe_payload, default=str)
    except Exception:  # noqa: BLE001
        raw = str(safe_payload)
    return _truncate(raw)


def _to_call_tool_result(payload: object) -> CallToolResult:
    if isinstance(payload, CallToolResult):
        return payload

    if isinstance(payload, dict):
        if "error" in payload:
            error_code = str(payload.get("error") or "tool_error")
            message = str(payload.get("message") or payload.get("body") or "Tool execution failed.")
            structured_error = {
                "status": "error",
                "error": error_code,
                "message": message,
                "details": payload,
            }
            return CallToolResult(
                content=[TextContent(type="text", text=json.dumps(structured_error, default=str))],
                structuredContent=structured_error,
                isError=True,
            )

        structured_success = dict(payload)
        structured_success.setdefault("status", "success")
        return CallToolResult(
            content=[TextContent(type="text", text=json.dumps(structured_success, default=str))],
            structuredContent=structured_success,
            isError=False,
        )

    structured_success = {"status": "success", "result": payload}
    return CallToolResult(
        content=[TextContent(type="text", text=json.dumps(structured_success, default=str))],
        structuredContent=structured_success,
        isError=False,
    )


def _wrap_tool(name: str, fn: Callable[..., dict]) -> Callable[..., CallToolResult]:
    fn_params = signature(fn).parameters
    supports_base_url = "nerm_base_url" in fn_params
    supports_bearer_token = "nerm_bearer_token" in fn_params

    def _extract_headers_from_ctx(ctx: Any) -> dict[str, str]:
        request_context = getattr(ctx, "request_context", None)
        if request_context is None:
            return {}
        request = getattr(request_context, "request", None)
        if request is None:
            return {}
        headers = getattr(request, "headers", None)
        if headers is None:
            return {}
        return {str(key): str(value) for key, value in dict(headers).items()}

    @wraps(fn, assigned=("__module__", "__name__", "__qualname__", "__doc__"))
    def _wrapped(*args: Any, ctx: Context | None = None, **kwargs: Any) -> CallToolResult:
        try:
            settings = get_settings()
            detail_log_level = logging.INFO if settings.nerm_verbose_trace else logging.DEBUG
            call_kwargs = dict(kwargs)
            if ctx is not None and (supports_base_url or supports_bearer_token):
                headers = _extract_headers_from_ctx(ctx)
                if headers:
                    auth = resolve_auth(headers, settings)
                    if supports_base_url and not call_kwargs.get("nerm_base_url"):
                        call_kwargs["nerm_base_url"] = auth.base_url
                    if supports_bearer_token and not call_kwargs.get("nerm_bearer_token"):
                        call_kwargs["nerm_bearer_token"] = auth.bearer_token
                    _LOGGER.log(
                        detail_log_level,
                        "tool_auth_source tool=%s injected_from_headers=%s",
                        name,
                        {"nerm_base_url": supports_base_url, "nerm_bearer_token": supports_bearer_token},
                    )

            _LOGGER.info("tool_call_input tool=%s args=%s", name, _serialize_output(call_kwargs))
            raw_result = fn(*args, **call_kwargs)
            result = _to_call_tool_result(raw_result)
            _LOGGER.info("tool_call_output tool=%s output=%s", name, _serialize_output(result))
            return result
        except Exception:
            _LOGGER.exception("tool_call_failed tool=%s", name)
            raise

    return _wrapped


_RAW_NERM_TOOLS = {
    "nerm_list_profile_types": nerm_list_profile_types,
    "nerm_get_profile_type": nerm_get_profile_type,
    "nerm_list_profiles": nerm_list_profiles,
    "nerm_get_profile": nerm_get_profile,
    "nerm_list_users": nerm_list_users,
    "nerm_get_user": nerm_get_user,
    "nerm_examine_jwt_user": nerm_examine_jwt_user,
    "nerm_list_delegations": nerm_list_delegations,
    "nerm_get_delegation": nerm_get_delegation,
    "nerm_create_delegation": nerm_create_delegation,
    "nerm_update_delegation": nerm_update_delegation,
    "nerm_delete_delegation": nerm_delete_delegation,
    "nerm_list_identity_proofing_results": nerm_list_identity_proofing_results,
    "nerm_list_roles": nerm_list_roles,
    "nerm_get_role": nerm_get_role,
    "nerm_list_user_roles": nerm_list_user_roles,
    "nerm_get_user_role": nerm_get_user_role,
    "nerm_list_user_managers": nerm_list_user_managers,
    "nerm_get_user_manager": nerm_get_user_manager,
    "nerm_list_user_profiles": nerm_list_user_profiles,
    "nerm_get_user_profile": nerm_get_user_profile,
    "nerm_list_role_profiles": nerm_list_role_profiles,
    "nerm_get_role_profile": nerm_get_role_profile,
    "nerm_list_workflow_session_statuses": nerm_list_workflow_session_statuses,
    "nerm_list_workflow_sessions": nerm_list_workflow_sessions,
    "nerm_get_workflow_session": nerm_get_workflow_session,
    "nerm_add_location_via_workflow": nerm_add_location_via_workflow,
    "nerm_add_department_via_workflow": nerm_add_department_via_workflow,
    "nerm_add_organization_via_workflow": nerm_add_organization_via_workflow,
    "nerm_get_job_status": nerm_get_job_status,
    "nerm_list_attributes": nerm_list_attributes,
    "nerm_get_attribute": nerm_get_attribute,
    "nerm_query_audit_events": nerm_query_audit_events,
    "nerm_run_advanced_search": nerm_run_advanced_search,
    "nerm_generate_chart": nerm_generate_chart,
    "nerm_get_current_date_time": nerm_get_current_date_time,
}


def _build_wrapped_tools(raw_tools: dict[str, Callable[..., dict]]) -> dict[str, Callable[..., CallToolResult]]:
    return {name: _wrap_tool(name, fn) for name, fn in raw_tools.items()}


NERM_TOOLS = _build_wrapped_tools(_RAW_NERM_TOOLS)


def register_tools(server: object) -> None:
    if not hasattr(server, "tools"):
        return
    server.tools.update(NERM_TOOLS)
