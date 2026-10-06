package nermapi

import (
	"fmt"
	"strings"
	"time"

	"github.com/sailpoint-se/nerm-cli/internal/client"
	"github.com/sailpoint-se/nerm-cli/internal/pagination"
)

var (
	AuditAllowedFilterKeys = []string{
		"subject_type", "type", "subject_id", "workflow_name", "workflow_uid", "workflow_profile_type", "profile_type",
	}
	AuditSubjectTypes = []string{
		"Profile", "WorkflowSession", "Email", "FormAttributeForm", "FormAttribute", "Form", "IdentityProofingResult",
		"IdproxyPermission", "NeAttributeOption", "NeAttribute", "Notification", "WorkflowPage", "ProfilePage",
		"Permission", "PortalRegistrationWorkflow", "Portal", "ProfileTypeRole", "ProfileType", "RoleProfile",
		"NeprofileRole", "NeaccessRole", "IdproxyRole", "SecurityQuestion", "UserManager", "UserProfile", "UserRole",
		"User", "Validation", "VerificationEmail", "WorkflowAction", "CreateWorkflow", "UpdateWorkflow",
		"AutomatedWorkflow", "BatchWorkflow", "ExpirationWorkflow", "InvitationWorkflow", "LoginWorkflow",
		"PasswordResetWorkflow", "RegistrationWorkflow", "Get", "Post", "Patch", "Delete", "ApprovalAction",
		"AutomatedUser", "DelegateUser", "NeaccessUser", "NeprofileUser", "Page", "Role", "SamlConfiguration",
		"SchemaMapping", "SchemaMappingField", "Workflow",
	}
	AuditAPIMethodEventTypes = []string{"Get", "Post", "Patch", "Delete"}
	AuditEventTypes          = []string{
		"AuditableProfileCreate", "AuditableProfileUpdate", "AuditableProfileDestroy", "AuditableBulkProfileUpdate",
		"AuditableProfileContributorAdd", "AuditableProfileContributorRemove", "AuditableProfileContributorRoleAdd",
		"AuditableProfileContributorRoleRemove", "AuditableProfileOwnerUpdate", "AuditableProfileWorkflowEvent",
		"AuditableWorkflowActionSkippedEvent", "AuditableWorkflowApprovedEvent", "AuditableWorkflowAssignedEvent",
		"AuditableWorkflowAutoAssignedEvent", "AuditableWorkflowBatchCompleteEvent", "AuditableWorkflowClosedEvent",
		"AuditableWorkflowDuplicateCheckStartEvent", "AuditableWorkflowDuplicateResolutionEvent",
		"AuditableWorkflowFailedEvent", "AuditableWorkflowIdentityProofedEvent", "AuditableWorkflowInvitationSentEvent",
		"AuditableWorkflowLdapProvidedEvent", "AuditableWorkflowNotificationSentEvent",
		"AuditableWorkflowPendingApprovalEvent", "AuditableWorkflowPendingAssignmentEvent",
		"AuditableWorkflowPendingFulfillmentEvent", "AuditableWorkflowFulfilledEvent",
		"AuditableWorkflowPendingIdentityProofEvent", "AuditableWorkflowPendingLdapEvent",
		"AuditableWorkflowPendingRequestEvent", "AuditableWorkflowPendingReviewEvent",
		"AuditableWorkflowProfileCreatedEvent", "AuditableWorkflowProfileSelectEvent",
		"AuditableWorkflowProfileUpdatedEvent", "AuditableWorkflowRejectedEvent",
		"AuditableWorkflowRequestMadeEvent", "AuditableWorkflowRestApiEvent", "AuditableWorkflowReviewedEvent",
		"AuditableWorkflowRunningWorkflowEvent", "AuditableWorkflowSoapApiEvent",
		"AuditableWorkflowStatusChangedEvent", "AuditableWorkflowStoredProcedureEvent",
		"AuditableWorkflowUnassignEvent", "AuditableWorkflowWaitingForWorkflowEvent",
		"AuditableWorkflowWorkflowChangedEvent", "ActiveRecordCreate", "ActiveRecordUpdate", "ActiveRecordDestroy",
		"AuditableApiEvent",
	}
)

const maxAuditFilters = 5

func QueryAudit(c *client.Client, filters map[string]any, limit, offset int, forceAll bool) (map[string]any, error) {
	allowedEvents := append(append([]string{}, AuditAPIMethodEventTypes...), AuditEventTypes...)
	if subject, ok := filters["subject_type"].(string); ok && subject != "" && !contains(AuditSubjectTypes, subject) {
		return invalidAudit("One or more audit core values are not allowed by API-spec value lists.", allowedEvents, map[string]any{
			"subject_type": map[string]any{"provided": subject, "allowed_values": AuditSubjectTypes},
		}), nil
	}
	if eventType, ok := filters["type"].(string); ok && eventType != "" && !contains(allowedEvents, eventType) {
		return invalidAudit("One or more audit core values are not allowed by API-spec value lists.", allowedEvents, map[string]any{
			"type": map[string]any{"provided": eventType, "allowed_values": allowedEvents},
		}), nil
	}
	for key := range filters {
		if !contains(AuditAllowedFilterKeys, key) {
			return invalidAudit("Unsupported audit filters: ["+key+"]", allowedEvents, nil), nil
		}
	}
	if len(filters) > maxAuditFilters {
		out := invalidAudit(fmt.Sprintf("A maximum of %d audit filters is allowed.", maxAuditFilters), allowedEvents, nil)
		out["filter_count"] = len(filters)
		return out, nil
	}

	boundedLimit, boundedOffset, err := pagination.Normalize(defaultInt(limit, 100), offset)
	if err != nil {
		return pagination.ValidationJSON(err), nil
	}
	effective := boundedLimit
	if forceAll && boundedLimit == 100 {
		effective = 2147483647
	}
	fetch := func(pageOffset, pageLimit, _, _ int) (any, error) {
		query := map[string]any{"limit": pageLimit, "offset": pageOffset}
		if len(filters) > 0 {
			query["filters"] = filters
		}
		payload, err := c.Request("POST", client.AuditEventsQuery, nil, map[string]any{"audit_events": query}, 15*time.Second)
		if err != nil {
			if apiErr, ok := err.(*client.APIError); ok && isEmptyCollection(apiErr, "no audit") {
				return map[string]any{"audit_events": []any{}}, nil
			}
			return nil, err
		}
		return payload, nil
	}
	result, err := pagination.Collect(effective, boundedOffset, forceAll, fetch, func(payload any) []map[string]any {
		return ListRecords(payload, "audit_events")
	})
	if err != nil {
		return nil, err
	}
	out := ListResponse(result, effective, boundedOffset)
	out["allowed_subject_type_values"] = AuditSubjectTypes
	out["allowed_event_type_values"] = allowedEvents
	return out, nil
}

func invalidAudit(message string, events []string, invalid map[string]any) map[string]any {
	out := map[string]any{
		"error":                       "invalid_audit_query_spec",
		"message":                     message,
		"allowed_filters":             AuditAllowedFilterKeys,
		"allowed_subject_type_values": AuditSubjectTypes,
		"allowed_event_type_values":   events,
	}
	if invalid != nil {
		out["invalid_values"] = invalid
	}
	return out
}

func contains(items []string, value string) bool {
	for _, item := range items {
		if item == value {
			return true
		}
	}
	return false
}

func RunAdvancedSearch(c *client.Client, payload map[string]any) (map[string]any, error) {
	raw := payload
	if inner, ok := payload["advanced_search"].(map[string]any); ok {
		raw = inner
	}
	for _, key := range []string{"field", "operator", "condition"} {
		if _, ok := raw[key]; ok {
			return map[string]any{
				"error":   "invalid_advanced_search_spec",
				"message": "Use NERM condition_rules_attributes schema, not SQL-style clauses.",
			}, nil
		}
	}
	if _, ok := raw["condition_rules_attributes"]; !ok {
		return map[string]any{
			"error":   "invalid_advanced_search_spec",
			"message": "advanced_search missing required keys: [condition_rules_attributes]",
		}, nil
	}
	rules, _ := raw["condition_rules_attributes"].([]any)
	if len(rules) == 0 {
		return map[string]any{
			"error":   "insufficient_advanced_search_filters",
			"message": "Provide at least one condition rule to avoid broad profile listing.",
		}, nil
	}
	result, err := c.Request("POST", client.AdvancedSearchRun, nil, map[string]any{"advanced_search": raw}, 30*time.Second)
	if err != nil {
		return nil, err
	}
	asMap, ok := result.(map[string]any)
	if !ok {
		return map[string]any{"result": result}, nil
	}
	items := ListRecords(asMap, "profiles")
	if len(items) > 0 {
		asMap["items"] = items
	}
	return asMap, nil
}

func SubmitWorkflow(c *client.Client, payload map[string]any) (map[string]any, error) {
	workflowID, _ := payload["workflow_id"].(string)
	if strings.TrimSpace(workflowID) == "" {
		return map[string]any{
			"error":   "nerm_api_error",
			"status":  400,
			"body":    "workflow_id is required",
		}, nil
	}
	result, err := c.Request("POST", client.WorkflowSessions, nil, payload, 30*time.Second)
	if err != nil {
		return nil, err
	}
	asMap, _ := result.(map[string]any)
	sessionID := firstString(asMap, "workflow_session_full_id", "workflow_session_id", "id")
	status := firstString(asMap, "status")
	if status == "" {
		status = "Pending"
	}
	return map[string]any{
		"message":                  "request submitted",
		"status":                   status,
		"workflow_session_full_id": sessionID,
	}, nil
}

func WorkflowStatuses(sessions map[string]any) map[string]any {
	seen := map[string]struct{}{}
	items := []map[string]any{}
	rawItems, _ := sessions["items"].([]map[string]any)
	if len(rawItems) == 0 {
		if generic, ok := sessions["items"].([]any); ok {
			rawItems = mapsFromAny(generic)
		}
	}
	for _, item := range rawItems {
		status := strings.TrimSpace(fmt.Sprint(item["status"]))
		if status == "" {
			continue
		}
		if _, ok := seen[status]; ok {
			continue
		}
		seen[status] = struct{}{}
		items = append(items, map[string]any{"status": status})
	}
	return map[string]any{
		"items":  items,
		"limit":  sessions["limit"],
		"offset": sessions["offset"],
		"total":  len(items),
	}
}
