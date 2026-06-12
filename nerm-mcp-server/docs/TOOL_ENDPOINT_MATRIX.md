# NERM Tool Endpoint Matrix

Source of truth for current MCP tool HTTP contracts.

| Tool | Method | Endpoint | Smoke Coverage |
|---|---|---|---|
| `nerm_list_profile_types` | `GET` | `/profile_types` | yes |
| `nerm_get_profile_type` | `GET` | `/profile_types/:id` | yes |
| `nerm_list_profiles` | `GET` | `/profiles` | yes |
| `nerm_get_profile` | `GET` | `/profiles/:id` | guarded |
| `nerm_list_users` | `GET` | `/users` | yes |
| `nerm_get_user` | `GET` | `/users/:id` | guarded |
| `nerm_examine_jwt_user` | `N/A` | `local JWT decode` | no |
| `nerm_list_delegations` | `GET` | `/delegations` | yes |
| `nerm_get_delegation` | `GET` | `/delegations/:id` | no |
| `nerm_create_delegation` | `POST` | `/delegations` | guarded |
| `nerm_update_delegation` | `PATCH` | `/delegations/:id` | no |
| `nerm_delete_delegation` | `DELETE` | `/delegations/:id` | no |
| `nerm_list_identity_proofing_results` | `GET` | `/identity_proofing_results` | yes |
| `nerm_list_roles` | `GET` | `/roles` | guarded |
| `nerm_get_role` | `GET` | `/roles/:id` | no |
| `nerm_list_user_roles` | `GET` | `/user_roles` | guarded |
| `nerm_get_user_role` | `GET` | `/user_roles/:id` | no |
| `nerm_list_user_managers` | `GET` | `/user_managers` | guarded |
| `nerm_get_user_manager` | `GET` | `/user_managers/:id` | no |
| `nerm_list_user_profiles` | `GET` | `/user_profiles` | guarded |
| `nerm_get_user_profile` | `GET` | `/user_profiles/:id` | no |
| `nerm_list_role_profiles` | `GET` | `/role_profiles` | guarded |
| `nerm_get_role_profile` | `GET` | `/role_profiles/:id` | no |
| `nerm_list_workflow_session_statuses` | `GET` | `/workflow_sessions` (derived statuses) | yes |
| `nerm_list_workflow_sessions` | `GET` | `/workflow_sessions` | yes |
| `nerm_get_workflow_session` | `GET` | `/workflow_sessions` (client-side lookup) | no |
| `nerm_add_location_via_workflow` | `POST` | `/workflow_sessions` | guarded |
| `nerm_add_department_via_workflow` | `POST` | `/workflow_sessions` | no |
| `nerm_add_organization_via_workflow` | `POST` | `/workflow_sessions` | no |
| `nerm_get_job_status` | `GET` | `/job_status` | no |
| `nerm_list_attributes` | `GET` | `/ne_attributes` | yes |
| `nerm_get_attribute` | `GET` | `/ne_attributes/:id` | yes |
| `nerm_query_audit_events` | `POST` | `/audit_events/query` | yes |
| `nerm_run_advanced_search` | `POST` | `/advanced_search/run` | guarded |
| `nerm_generate_chart` | `N/A` | `in-process` | no |
| `nerm_get_current_date_time` | `N/A` | `in-process` | no |
