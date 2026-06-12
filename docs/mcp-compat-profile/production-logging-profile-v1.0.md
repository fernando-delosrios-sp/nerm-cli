# Production Logging Profile v1.0

Status: Published  
Scope: Tool invocation and transport-safe logging for production deployments.

## Goals

- Keep logs useful for diagnostics.
- Prevent leakage of sensitive and large binary payloads.
- Keep logging deterministic across client/server ecosystems.

## Required Logging Events

- `tool_call_input tool=<name> args=<sanitized>`
- `tool_call_output tool=<name> output=<sanitized>`
- `tool_call_failed tool=<name>` with stack trace for unexpected failures.

## Redaction Rules

- Keys containing sensitive terms MUST be redacted:
  - `authorization`, `token`, `password`, `secret`, `api_key`
- Binary payloads MUST NOT be logged raw.
- Image block `data` fields SHOULD be logged as:
  - `<base64_image len=<n>>`

## Truncation Rules

- Long payload logs SHOULD be truncated to configured max bytes.
- Truncation marker SHOULD be appended (`...<truncated>`).

## Operational Defaults

- INFO-level logging for tool input/output in production.
- Optional verbose trace mode for deeper diagnostics.
- Logging failures MUST NOT break request handling.

## Compliance Checklist

- [ ] Sensitive keys redacted
- [ ] Binary/base64 image data masked
- [ ] Payload truncation active
- [ ] Tool call name and args visible
