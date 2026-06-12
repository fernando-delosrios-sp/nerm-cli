# NERM API Value Guidance (Tool-Facing)

This document centralizes authoritative allowed-value guidance for NERM APIs used by this agent. It is derived from:

- NERM API docs: <https://developer.sailpoint.com/docs/api/nerm/v1>
- Local spec copy: `docs/nerm-api-spec.json`
- Current tool contracts in `nerm-mcp-server/app/nerm/tools/`

Use these value lists as authoritative for constrained fields exposed by the tools.
For open-string fields in the API contract, tool-level enforcement may use known value
lists published in SDK/spec references for safer calls.

## Cross-Cutting

- **Pagination:** `limit` positive int, `offset` non-negative int.
- **Metadata:** when supported, set `metadata=true` for count/total-aware flows.
- **Filter budget:** audit query supports at most 5 non-pagination filters.

## Profiles API (`/profiles`)

- Common status values:
  - `Active`
  - `Inactive`
  - `On Leave`
  - `Terminated`
- Query-shaping fields used by tools:
  - `profile_type_id`, `status`, `name`, `order`, `after_id`, `updated_after`

## Users API (`/users`)

- `user_status` common values:
  - `Active`
  - `Pending`
  - `Disabled`
- `type` values:
  - `NeprofileUser` (Lifecycle user)
  - `NeaccessUser` (Portal/Collaboration user)

## Roles API (`/roles`)

- `type` values:
  - `NeprofileRole` (Lifecycle role)
  - `NeaccessRole` (Portal/Collaboration role)
  - `IdproxyRole`

## User/Role Relationship APIs

- Relationship type values:
  - `owner`
  - `contributor`

## Identity Proofing (`/identity_proofing_results`)

- Result values:
  - `pass`
  - `fail`

## Attributes (`/ne_attributes`)

- Data type values used in filters/guidance:
  - `text field`, `text area`, `drop-down`, `radio buttons`, `check boxes`
  - `date`, `tags`, `attachment`
  - `profile select`, `profile search`
  - `owner select`, `owner search`
  - `contributor select`, `contributor search`

## Workflow Sessions (`/workflow_sessions`)

- Query filters exposed by tools:
  - `status`, `order`, `profile_id`, `uid`, `workflow_id`, `requester_id`, `metadata`
- Known workflow status values are numerous (see `WorkflowSessionStatus` in `nerm-mcp-server/app/nerm/tools/param_specs.py`).
- Preferred pattern:
  - Resolve valid status options via `nerm_list_workflow_session_statuses` when uncertain.

## Audit Query (`POST /audit_events/query`)

- Primary filters:
  - `subject_type`, `type`, `subject_id`
- Extended filters:
  - `workflow_name`, `workflow_uid`, `workflow_profile_type`, `profile_type`
- Common `subject_type` values:
  - `WorkflowSession`, `Profile`
- Common API-operation subject families:
  - `Get`, `Post`, `Patch`, `Delete`
- Note:
  - `subject_type`/`type` are open-string domains in spec context; additional values exist (workflow/profile/api/config domains).

## Delegations (`/delegations`)

- `expired` is boolean (`true` / `false`)
- Write payloads:
  - Use exact key `expiration` with ISO-8601 date-time
  - Avoid unsupported keys: `end_date`, `expiration_date`, `expires_at`

## Safety Notes

- Prefer spec-known values and IDs resolved from list/get tools.
- If an API returns “no \<resource\> found” during paging, treat it as terminal page.
- For count intents, prefer metadata `total` when present; otherwise derive total via pagination continuation.
