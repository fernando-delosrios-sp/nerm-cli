# End User Test Guidance

Use this prompt suite in the chat client to validate MCP behavior against both tool features and NERM API contract behavior.
Replace placeholders with tenant-valid values and capture results for each test.

## Test Setup

- Use a non-production tenant with representative data volume.
- Enable request logging while testing (`LOG_LEVEL=INFO`, optional `NERM_DEBUG_LOG_BODIES=1`).
- Keep a scratchpad of resolved IDs: `profile_type_id`, `profile_id`, `user_id`, `role_id`, `attribute_id`, `delegation_id`, `workflow_session_id`, `workflow_uid`.
- Record for each prompt: result status, key output fields, and whether output matches expected behavior.

## Test Conventions

- Use exact prompt text first; then run one paraphrase to validate intent routing robustness.
- For list/count prompts, confirm `total`, `returned_count`, `pages_fetched`, `pagination_limited` behavior when those fields are available.
- For filters, test both a valid value and an invalid value.
- For write operations, validate post-write state with read tools (do not trust write acknowledgement alone).

## Coverage Map

- Profiles and profile types
- Users and role relationships
- Delegations lifecycle
- Workflow sessions and async status
- Attributes and reference catalogs
- Audit query filters, shape, and pagination
- Advanced search rule syntax and validation
- Chart rendering and readability options
- Error handling, ambiguity handling, and safety behavior

## Tool-Level Prompt Suites

### Profile Types (`nerm_list_profile_types`, `nerm_get_profile_type`)

- `List profile types with ids, archived flag, and synced status.`
- `List profile types filtered by name containing "Assign".`
- `List only archived profile types.`
- `Get profile type details for id <profile_type_id>.`
- `Get profile type details for id <invalid_profile_type_id>.`
- `List profile types sorted by name.`
- `List profile types with limit 5 and offset 5.`

Expected checks:

- Name filter and archived filter both work.
- Pagination fields are coherent for limit/offset queries.
- Invalid ID returns a structured not-found error.

### Profiles (`nerm_list_profiles`, `nerm_get_profile`)

- `How many assignments are there?`
- `List assignment profiles using profile_type_id <assignment_profile_type_id>.`
- `List active assignment profiles using profile_type_id <assignment_profile_type_id> and status Active.`
- `List profiles updated after <iso_datetime>.`
- `List profiles named "<known_profile_name>" with attributes excluded.`
- `List profiles with limit 20, offset 0, then list with offset 20.`
- `List profiles with force_all=true for profile_type_id <assignment_profile_type_id>.`
- `Get profile details for id <profile_id>.`

Expected checks:

- Count answers are based on metadata-aware total.
- Single profile-type simple prompts route to list-profiles path.
- `force_all=true` traverses pages for larger sets.

### Users (`nerm_list_users`, `nerm_get_user`, `nerm_examine_jwt_user`)

- `List users with type NeprofileUser and status Active.`
- `List users with type NeaccessUser and status Disabled.`
- `Find user by login <user_login>.`
- `Find user by email <user_email>.`
- `Find user by name "<First Last>" and show candidate matches.`
- `Get user details for id <user_id>.`
- `Who am I based on the current JWT token?`
- `Find user by ambiguous name "<common_name>".`

Expected checks:

- Type/status filtering is honored.
- Name/email fallback behavior still returns users when safe normalization applies.
- Ambiguous results trigger disambiguation instead of guessing.

### Delegations (`nerm_list_delegations`, `nerm_get_delegation`, `nerm_create_delegation`, `nerm_update_delegation`, `nerm_delete_delegation`)

- `List delegations for delegator id <delegator_user_id>.`
- `Create a delegation from <delegator_user_id> to <delegate_user_id> expiring in 14 days.`
- `Get delegation details for id <delegation_id>.`
- `Update delegation <delegation_id> to expire in 30 days from now.`
- `Delete delegation <delegation_id>.`
- `Try to create a delegation with an expiration in the past.`
- `Try creating delegation where delegator and delegate are the same user.`

Expected checks:

- Create/update/delete lifecycle works end-to-end.
- Date-format and "expiration after today" errors are actionable.
- Validation failures do not leak sensitive tokens.

### Identity Proofing (`nerm_list_identity_proofing_results`)

- `List identity proofing results with limit 20.`
- `List identity proofing results filtered by pass result.`
- `List identity proofing results filtered by fail result.`

Expected checks:

- Result filter values map correctly to API-supported values.
- Sensitive details are handled safely in summaries.

### Roles and Relationship Tools

Tools covered: `nerm_list_roles`, `nerm_get_role`, `nerm_list_user_roles`, `nerm_get_user_role`, `nerm_list_user_managers`, `nerm_get_user_manager`, `nerm_list_user_profiles`, `nerm_get_user_profile`, `nerm_list_role_profiles`, `nerm_get_role_profile`.

- `List roles with type NeaccessRole.`
- `List roles with type NeprofileRole.`
- `Get role details for id <role_id>.`
- `List user-role mappings for user id <user_id>.`
- `Get user-role mapping details for id <user_role_id>.`
- `List manager relationships for user id <user_id>.`
- `Get manager relationship details for id <user_manager_id>.`
- `List user-profile relationships for user id <user_id>.`
- `Get user-profile relationship details for id <user_profile_id>.`
- `List role-profile relationships for role id <role_id>.`
- `Get role-profile relationship details for id <role_profile_id>.`

Expected checks:

- Relationship records resolve and cross-link to principal entities.
- Invalid relationship IDs return structured not-found behavior.

### Workflow Sessions (`nerm_list_workflow_session_statuses`, `nerm_list_workflow_sessions`, `nerm_get_workflow_session`, `nerm_get_job_status`)

- `What workflow session statuses currently exist in this tenant?`
- `List workflow sessions with status pending approval.`
- `List workflow sessions for requester id <requester_user_id>.`
- `List workflow sessions filtered by workflow uid <workflow_uid>.`
- `Get workflow session details for id <workflow_session_id>.`
- `Get job status for job id <job_id>.`
- `List workflow sessions with limit 50 offset 0, then offset 50.`

Expected checks:

- Status values are tenant-valid and normalized.
- Workflow-session lookups accept session ID variants.
- Job status payload is normalized and includes requested ID context.

### Workflow Submission (`nerm_add_location_via_workflow`, `nerm_add_department_via_workflow`, `nerm_add_organization_via_workflow`)

- `Submit a workflow request to add location "<new_location_name>".`
- `Submit a workflow request to add department "<new_department_name>".`
- `Submit a workflow request to add organization "<new_organization_name>".`
- `After each submission, report workflow_session_full_id and initial status only.`
- `Track each submission until terminal status, then verify resulting data exists.`
- `Try submission without required workflow id configuration and explain the error.`

Expected checks:

- Responses are "request submitted" semantics, not immediate profile-update claims.
- `workflow_session_full_id` is returned and used for tracking.

### Attributes (`nerm_list_attributes`, `nerm_get_attribute`)

- `List attributes for profile type id <profile_type_id>.`
- `List attributes filtered by data type "text field".`
- `List attributes filtered by data type "profile select".`
- `Get attribute details for id <attribute_id>.`
- `Get attribute details for id <invalid_attribute_id>.`

Expected checks:

- Attribute catalog retrieval and filtering work.
- Invalid attribute lookups return actionable errors.

### Audit (`nerm_query_audit_events`)

- `Show all audit events for workflow uid <workflow_uid>.`
- `Show all audit events for workflow name "<workflow_name>" with subject_type WorkflowSession.`
- `Show audit events with subject_type Profile and subject_id <profile_id>.`
- `Show only event_type Delete for subject_type WorkflowSession.`
- `What are valid audit subject types and event types?`
- `Run audit query with invalid event_type "<bad_value>" and explain allowed values.`
- `Run audit query with 6 filters and explain filter-budget validation.`
- `Run audit query with force_all=false and limit 25 for a bounded sample.`
- `Run audit query with force_all=true for full traversal and report pages_fetched and total.`

Expected checks:

- Request body uses `audit_events` with nested `filters`.
- Full-trail mode traverses beyond first page by default unless bounded explicitly.
- Workflow-history prompts prefer `workflow_uid`/`workflow_name` scoping.

### Advanced Search (`nerm_run_advanced_search`)

- `Find active assignments using advanced search with ProfileTypeRule and ProfileStatusRule.`
- `Find organizations with risk score above <threshold> using RiskRule.`
- `Find profiles by specific attribute value using ProfileAttributeRule.`
- `Group assignment results by organization and return counts.`
- `Run advanced search with empty condition_rules_attributes and show validation guidance.`
- `Run advanced search using SQL-style keys field/operator/condition and show rejection.`

Expected checks:

- Rule-object schema is enforced.
- SQL-style payloads are rejected with clear guidance.
- Multi-filter analytics route here rather than broad profile list calls.

### Chart Generation (`nerm_generate_chart`)

- `Create a bar chart for counts: Org A=10, Org B=7, Org C=4.`
- `Create a multi-line chart for two daily series over 14 days.`
- `Create a date-based line chart with x-axis dates and ensure chronological ordering.`
- `Create a grouped_bar chart comparing Active vs Terminated by organization.`
- `Create a heatmap for a 3x3 risk matrix and include labels.`
- `Render a long-label chart with readability options (rotation and max_visible_ticks).`
- `Try to chart non-numeric values and report fallback behavior.`

Expected checks:

- Supported chart types render correctly.
- Date axes are ordered and readable.
- No-data/invalid-data failures are handled cleanly.

## Cross-Tool Business Scenarios

### Scenario A: Assignment Operations Dashboard

- `How many active assignments are there?`
- `Break down active assignments by organization and population.`
- `Show top 10 organizations by active assignments, then generate a bar chart.`
- `List assignments expiring in the next 30 days.`

### Scenario B: Workflow Incident Investigation

- `Show all events for workflow with subject_label "<workflow_label>".`
- `Who changed it last and what changed?`
- `Filter to workflow-session-specific events only.`
- `Provide a timeline chart of event counts by day for that workflow.`

### Scenario C: Access Governance Trace

- `For user <user_email>, list roles, managers, and related profiles.`
- `For each role, list associated profile types.`
- `Highlight disabled users with active role assignments.`

### Scenario D: Delegation Compliance Audit

- `Create a short-lived delegation and verify creation audit event.`
- `Update expiration and verify update audit event.`
- `Delete delegation and verify deletion audit event.`
- `Summarize delegation event counts by type and chart them.`

### Scenario E: Reference Data Change Lifecycle

- `Submit add-location workflow for "<location_name>".`
- `Track workflow status progression to terminal state.`
- `Validate new reference data is available in downstream lists/attributes.`
- `Show audit trail for that workflow uid.`

## Negative and Robustness Tests

- `Use an invalid UUID for each get-by-id tool and confirm structured errors.`
- `Ask for ambiguous entity names and verify disambiguation prompt behavior.`
- `Request extremely broad listing without filters and verify safe pagination behavior is explained.`
- `Request forbidden/malformed advanced search schema and verify validation details.`
- `Request audit query with unsupported filter key and verify allowed filter feedback.`
- `Attempt write operations without required payload fields and verify clear remediation guidance.`

## Final Acceptance Checklist

- [ ] Every registered tool is executed at least once.
- [ ] Every list tool is tested for pagination (`limit`, `offset`) and at least one filtered query.
- [ ] At least one `force_all` path is verified for profiles or workflow sessions, and audit full traversal is verified.
- [ ] Audit tests confirm nested `filters` request shape and valid-value guidance in responses.
- [ ] Advanced search validation rejects SQL-style payloads and empty rules with useful guidance.
- [ ] Workflow submission tests confirm asynchronous semantics and status tracking.
- [ ] At least one write lifecycle (`create`, `update`, `delete`) is verified with read-back confirmation.
- [ ] Chart tests cover at least three chart types, including one date-axis chart.
- [ ] Error outputs remain actionable and do not expose secrets.

