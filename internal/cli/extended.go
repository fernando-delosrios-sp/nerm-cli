package cli

import "github.com/spf13/cobra"

func restWrites(name, createPath, updatePath, deletePath string) []op {
	var ops []op
	if createPath != "" {
		ops = append(ops, op{Use: "create", Short: "Create " + name, Method: "POST", Path: createPath, Body: true})
	}
	if updatePath != "" {
		ops = append(ops, op{Use: "update", Short: "Update " + name, Method: "PATCH", Path: updatePath, Args: []string{"ID"}, Body: true})
	}
	if deletePath != "" {
		ops = append(ops, op{Use: "delete", Short: "Delete " + name, Method: "DELETE", Path: deletePath, Args: []string{"ID"}})
	}
	return ops
}

func bulkOp(use, short, method, path string, body bool) op {
	return op{Use: use, Short: short, Method: method, Path: path, Body: body}
}

func attachProfileWrites(cmd *cobra.Command, rt *runtime) {
	addOps(cmd, rt, append(
		restWrites("one profile", "/profile", "/profiles/%s", "/profiles/%s"),
		bulkOp("create-many", "Create multiple profiles", "POST", "/profiles", true),
		bulkOp("update-many", "Update multiple profiles", "PATCH", "/profiles", true),
		bulkOp("delete-many", "Delete multiple profiles", "DELETE", "/profiles", true),
		op{Use: "avatar", Short: "Get a profile avatar URL", Method: "GET", Path: "/profiles/%s/avatar", Args: []string{"ID"}},
		op{Use: "avatar-upload", Short: "Upload a profile avatar", Method: "POST", Path: "/profiles/%s/avatar", Args: []string{"ID"}, File: true},
		op{Use: "attachment", Short: "Get a profile attachment URL", Method: "GET", Path: "/profiles/%s/upload/%s", Args: []string{"ID", "ATTRIBUTE_ID"}},
		op{Use: "attachment-upload", Short: "Upload a profile attachment", Method: "POST", Path: "/profiles/%s/upload/%s", Args: []string{"ID", "ATTRIBUTE_ID"}, File: true},
	))
}

func attachProfileTypeWrites(cmd *cobra.Command, rt *runtime) {
	addOps(cmd, rt, append(
		restWrites("a profile type", "/profile_type", "/profile_types/%s", "/profile_types/%s"),
		op{Use: "attributes", Short: "List attributes on a profile type", Method: "GET", Path: "/profile_types/%s/ne_attributes", Args: []string{"PROFILE_TYPE_ID"}, Query: []flagSpec{
			{name: "active-filter", api: "active_filter", help: "active attribute filter"},
			{name: "search", api: "search", help: "search text"},
			{name: "page", api: "page", help: "page"},
			{name: "attr", api: "attr", help: "attribute filter"},
			{name: "order", api: "order", help: "order field"},
		}},
		op{Use: "sync", Short: "Create a synced attribute", Method: "POST", Path: "/profile_types/%s/synced_attributes", Args: []string{"PROFILE_TYPE_ID"}, Body: true},
		op{Use: "unsync", Short: "Delete a synced attribute", Method: "DELETE", Path: "/profile_types/%s/synced_attributes/%s", Args: []string{"PROFILE_TYPE_ID", "ATTRIBUTE_ID"}},
		op{Use: "grant-role", Short: "Create a profile type role", Method: "POST", Path: "/profile_type_roles", Body: true},
	))
}

func attachUserWrites(cmd *cobra.Command, rt *runtime) {
	addOps(cmd, rt, append(
		restWrites("one user", "/user", "/users/%s", "/users/%s"),
		bulkOp("create-many", "Create multiple users", "POST", "/users", true),
		bulkOp("update-many", "Update multiple users", "PATCH", "/users", true),
		op{Use: "avatar", Short: "Get a user avatar URL", Method: "GET", Path: "/users/%s/avatar", Args: []string{"ID"}},
		op{Use: "avatar-upload", Short: "Upload a user avatar", Method: "POST", Path: "/users/%s/avatar", Args: []string{"ID"}, File: true},
	))
}

func attachRoleWrites(cmd *cobra.Command, rt *runtime) {
	addOps(cmd, rt, append(
		restWrites("one role", "/role", "/roles/%s", ""),
		bulkOp("create-many", "Create multiple roles", "POST", "/roles", true),
		bulkOp("update-many", "Update multiple roles", "PATCH", "/roles", true),
	))
}

func attachUserRoleWrites(cmd *cobra.Command, rt *runtime) {
	addOps(cmd, rt, append(
		restWrites("one user role", "/user_role", "/user_roles/%s", "/user_role/%s"),
		bulkOp("create-many", "Create multiple user roles", "POST", "/user_roles", true),
		bulkOp("update-many", "Update multiple user roles", "PATCH", "/user_roles", true),
	))
}

func attachUserManagerWrites(cmd *cobra.Command, rt *runtime) {
	addOps(cmd, rt, append(
		restWrites("one user manager", "/user_manager", "/user_managers/%s", ""),
		bulkOp("create-many", "Create multiple user managers", "POST", "/user_managers", true),
		bulkOp("update-many", "Update multiple user managers", "PATCH", "/user_managers", true),
	))
}

func attachUserProfileWrites(cmd *cobra.Command, rt *runtime) {
	addOps(cmd, rt, append(
		restWrites("one user profile", "/user_profile", "/user_profiles/%s", "/user_profile/%s"),
		bulkOp("create-many", "Create multiple user profiles", "POST", "/user_profiles", true),
		bulkOp("update-many", "Update multiple user profiles", "PATCH", "/user_profiles", true),
		bulkOp("delete-many", "Delete multiple user profiles", "DELETE", "/user_profiles", true),
	))
}

func attachRoleProfileWrites(cmd *cobra.Command, rt *runtime) {
	addOps(cmd, rt, append(
		restWrites("one role profile", "/role_profile", "/role_profiles/%s", "/role_profile/%s"),
		bulkOp("create-many", "Create multiple role profiles", "POST", "/role_profiles", true),
		bulkOp("update-many", "Update multiple role profiles", "PATCH", "/role_profiles", true),
	))
}

func attachAttributeWrites(cmd *cobra.Command, rt *runtime) {
	addOps(cmd, rt, restWrites("an attribute", "/ne_attributes", "/ne_attributes/%s", "/ne_attributes/%s"))
}

func newProfileTypesCmd(rt *runtime) *cobra.Command {
	cmd := newResourceListGet(rt, "profile-types", "profile type catalog", listProfileTypes, func(rt *runtime, id string) (map[string]any, error) {
		return getPath(rt, "/profile_types", id)
	}, "id")
	list := cmd.Commands()[0]
	list.Flags().String("name", "", "filter by name")
	list.Flags().Bool("archived", false, "filter by archived")
	attachProfileTypeWrites(cmd, rt)
	return cmd
}

func newFormsCmd(rt *runtime) *cobra.Command {
	return newCollection(rt, "forms", "Forms", "/forms", "forms", true, nil, restWrites("a form", "/forms", "/forms/%s", "/forms/%s"))
}

func newFormAttributesCmd(rt *runtime) *cobra.Command {
	return newCollection(rt, "form-attributes", "Form attributes", "/form_attributes", "form_attributes", true, nil, restWrites("a form attribute", "/form_attributes", "/form_attributes/%s", "/form_attributes/%s"))
}

func newPagesCmd(rt *runtime) *cobra.Command {
	cmd := &cobra.Command{Use: "pages", Short: "Profile and workflow pages"}
	addOps(cmd, rt, []op{
		{Use: "create-profile", Short: "Create a profile page", Method: "POST", Path: "/pages/profile_pages", Body: true},
		{Use: "create-workflow", Short: "Create a workflow page", Method: "POST", Path: "/pages/workflow_pages", Body: true},
	})
	return cmd
}

func newPageContentsCmd(rt *runtime) *cobra.Command {
	return newCollection(rt, "page-contents", "Page contents", "/page_contents", "page_contents", true, nil, restWrites("page content", "/page_contents", "/page_contents/%s", "/page_contents/%s"))
}

func newPageTranslationsCmd(rt *runtime) *cobra.Command {
	return newCollection(rt, "page-content-translations", "Page content translations", "/page_content_translations", "page_content_translations", true, nil, restWrites("a page content translation", "/page_content_translations", "/page_content_translations/%s", "/page_content_translations/%s"))
}

func newPageElementsCmd(rt *runtime) *cobra.Command {
	return newCollection(rt, "page-elements", "Page elements", "/page_elements", "page_elements", true, nil, restWrites("a page element", "/page_elements", "/page_elements/%s", "/page_elements/%s"))
}

func newAttributeOptionsCmd(rt *runtime) *cobra.Command {
	return newCollection(rt, "attribute-options", "Attribute option values", "/ne_attribute_options", "ne_attribute_options", true, []flagSpec{
		{name: "ne-attribute-id", api: "ne_attribute_id", help: "filter by attribute id"},
	}, []op{
		{Use: "add", Short: "Add one option value", Method: "POST", Path: "/ne_attribute_option", Body: true},
		{Use: "create-many", Short: "Create multiple option values", Method: "POST", Path: "/ne_attribute_options", Body: true},
		{Use: "update", Short: "Update one option value", Method: "PATCH", Path: "/ne_attribute_options/%s", Args: []string{"ID"}, Body: true},
		{Use: "update-many", Short: "Update multiple option values", Method: "PATCH", Path: "/ne_attribute_options", Body: true},
		{Use: "delete", Short: "Delete one option value", Method: "DELETE", Path: "/ne_attribute_options/%s", Args: []string{"ID"}},
	})
}

func newRiskLevelsCmd(rt *runtime) *cobra.Command {
	return newCollection(rt, "risk-levels", "Risk levels", "/risk_levels", "risk_levels", true, []flagSpec{
		{name: "label", api: "label", help: "filter by label"},
	}, nil)
}

func newRiskScoresCmd(rt *runtime) *cobra.Command {
	return newCollection(rt, "risk-scores", "Risk scores", "/risk_scores", "risk_scores", true, []flagSpec{
		{name: "object-id", api: "object_id", help: "filter by object id"},
		{name: "object-type", api: "object_type", help: "filter by object type"},
		{name: "overall-risk-level-id", api: "overall_risk_level_id", help: "filter by overall risk level id"},
		{name: "impact-risk-level-id", api: "impact_risk_level_id", help: "filter by impact risk level id"},
		{name: "probability-risk-level-id", api: "probability_risk_level_id", help: "filter by probability risk level id"},
	}, nil)
}

func newSystemRolesCmd(rt *runtime) *cobra.Command {
	return newCollection(rt, "system-roles", "System roles", "/system_roles", "system_roles", false, nil, nil)
}

func newISCAccountsCmd(rt *runtime) *cobra.Command {
	return newCollection(rt, "isc-accounts", "Identity Security Cloud account profiles", "/isc/accounts", "profiles", true, []flagSpec{
		{name: "use-schema", api: "use_schema", help: "return schema-mapped field names", kind: "bool"},
		{name: "override-sync-toggle", api: "override_sync_toggle", help: "include profiles regardless of sync status", kind: "bool"},
		{name: "category", api: "category", help: "filter by category"},
		{name: "status", api: "status", help: "filter by status"},
	}, []op{
		{Use: "update", Short: "Update an ISC account profile", Method: "PATCH", Path: "/isc/accounts/%s", Args: []string{"ID"}, Body: true},
	})
}

func newWorkflowActionsCmd(rt *runtime) *cobra.Command {
	cmd := &cobra.Command{Use: "workflow-actions", Short: "Workflow actions"}
	list := &cobra.Command{
		Use:   "list",
		Short: "Get workflow actions",
		RunE: func(cmd *cobra.Command, args []string) error {
			return rawGet(rt, "/workflow_actions", queryFlags(cmd, []flagSpec{
				{name: "workflow-id", api: "workflow_id", help: "workflow id"},
			}))
		},
	}
	registerFlags(list, []flagSpec{{name: "workflow-id", api: "workflow_id", help: "filter by workflow id"}})
	cmd.AddCommand(list)
	creates := []struct{ use, path, short string }{
		{"create-approval", "/workflow_actions/approval_actions", "Create an approval action"},
		{"create-ask-security-question", "/workflow_actions/ask_security_question_actions", "Create an ask security question action"},
		{"create-auto-assign", "/workflow_actions/auto_assign_actions", "Create an auto assign action"},
		{"create-batch-update", "/workflow_actions/batch_update_actions", "Create a batch update action"},
		{"create-close-session", "/workflow_actions/close_session_actions", "Create a close session action"},
		{"create-contributors", "/workflow_actions/contributors_actions", "Create a contributors action"},
		{"create-profile", "/workflow_actions/create_profile_actions", "Create a create profile action"},
		{"create-duplicate-prevention", "/workflow_actions/duplicate_prevention_actions", "Create a duplicate prevention action"},
		{"create-email-verification", "/workflow_actions/email_verification_actions", "Create an email verification action"},
		{"create-fulfillment", "/workflow_actions/fulfillment_actions", "Create a fulfillment action"},
		{"create-identity-proofing", "/workflow_actions/identity_proofing_actions", "Create an identity proofing action"},
		{"create-invitation", "/workflow_actions/invitation_actions", "Create an invitation action"},
		{"create-ldap", "/workflow_actions/ldap_actions", "Create an LDAP action"},
		{"create-notification", "/workflow_actions/notification_actions", "Create a notification action"},
		{"create-password-reset", "/workflow_actions/password_reset_actions", "Create a password reset action"},
		{"create-profile-check", "/workflow_actions/profile_check_actions", "Create a profile check action"},
		{"create-profile-select", "/workflow_actions/profile_select_actions", "Create a profile select action"},
		{"create-request", "/workflow_actions/request_actions", "Create a request action"},
		{"create-rest-api", "/workflow_actions/rest_api_actions", "Create a REST API action"},
		{"create-review", "/workflow_actions/review_actions", "Create a review action"},
		{"create-run-workflow", "/workflow_actions/run_workflow_actions", "Create a run workflow action"},
		{"create-set-attributes", "/workflow_actions/set_attributes_actions", "Create a set attributes action"},
		{"create-set-security-question", "/workflow_actions/set_security_question_actions", "Create a set security question action"},
		{"create-soap-api", "/workflow_actions/soap_api_actions", "Create a SOAP API action"},
		{"create-status-change", "/workflow_actions/status_change_actions", "Create a status change action"},
		{"create-unassign", "/workflow_actions/unassign_actions", "Create an unassign action"},
		{"create-update-profile", "/workflow_actions/update_profile_actions", "Create an update profile action"},
		{"create-username-password", "/workflow_actions/username_password_actions", "Create a username password action"},
	}
	ops := make([]op, 0, len(creates))
	for _, item := range creates {
		ops = append(ops, op{Use: item.use, Short: item.short, Method: "POST", Path: item.path, Body: true})
	}
	addOps(cmd, rt, ops)
	return cmd
}

func workflowTemplateOps() []op {
	templates := []struct{ use, path, short string }{
		{"new-automated", "/workflows/automated_workflows", "Create an automated workflow"},
		{"new-batch", "/workflows/batch_workflows", "Create a batch workflow"},
		{"new-create", "/workflows/create_workflows", "Create a create workflow"},
		{"new-login", "/workflows/login_workflows", "Create a login workflow"},
		{"new-password-reset", "/workflows/password_reset_workflows", "Create a password reset workflow"},
		{"new-registration", "/workflows/registration_workflows", "Create a registration workflow"},
		{"new-update", "/workflows/update_workflows", "Create an update workflow"},
	}
	ops := make([]op, 0, len(templates))
	for _, item := range templates {
		ops = append(ops, op{Use: item.use, Short: item.short, Method: "POST", Path: item.path, Body: true})
	}
	return ops
}

func newIDProxyCmd(rt *runtime) *cobra.Command {
	cmd := &cobra.Command{Use: "idproxy", Short: "Identity proxy consolidation routes"}
	addOps(cmd, rt, []op{
		{Use: "reassign", Short: "Reassign a data record to a master record", Method: "PATCH", Path: "/idproxy/data_records/%s/reassign", Args: []string{"ID"}, Body: true},
		{Use: "delete-identity", Short: "Delete a master record", Method: "DELETE", Path: "/idproxy/identities/%s", Args: []string{"ID"}},
	})
	return cmd
}

func newPermissionsCmd(rt *runtime) *cobra.Command {
	cmd := &cobra.Command{Use: "permissions", Short: "Permissions"}
	addOps(cmd, rt, []op{{Use: "create", Short: "Create a permission", Method: "POST", Path: "/permissions", Body: true}})
	return cmd
}

func newSystemRolePermissionsCmd(rt *runtime) *cobra.Command {
	cmd := &cobra.Command{Use: "system-role-permissions", Short: "System role permissions"}
	addOps(cmd, rt, []op{{Use: "create", Short: "Create a system role permission", Method: "POST", Path: "/system_role_permissions", Body: true}})
	return cmd
}

func newWorkflowActionPerformersCmd(rt *runtime) *cobra.Command {
	cmd := &cobra.Command{Use: "workflow-action-performers", Short: "Workflow action performers"}
	addOps(cmd, rt, []op{{Use: "create", Short: "Create a workflow action performer", Method: "POST", Path: "/workflow_action_performers", Body: true}})
	return cmd
}

func newLanguagesCmd(rt *runtime) *cobra.Command {
	cmd := &cobra.Command{Use: "languages", Short: "Languages"}
	addOps(cmd, rt, []op{{Use: "update", Short: "Update a language", Method: "PATCH", Path: "/languages/%s", Args: []string{"LOCALE"}, Body: true}})
	return cmd
}

func attachSearchOps(cmd *cobra.Command, rt *runtime) {
	list := &cobra.Command{
		Use:   "list",
		Short: "List saved advanced searches",
		RunE: func(cmd *cobra.Command, args []string) error {
			payload, err := listPath(rt, cmd, "/advanced_search", "advanced_search", "", collectionQuery(cmd, nil), nil)
			return handleAPI(rt, payload, err)
		},
	}
	listFlags(list)
	runSaved := &cobra.Command{
		Use:   "run-saved ID",
		Short: "Run a saved advanced search",
		Args:  cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			payload, err := listPath(rt, cmd, "/advanced_search/"+args[0]+"/run", "profiles", "", collectionQuery(cmd, nil), nil)
			return handleAPI(rt, payload, err)
		},
	}
	listFlags(runSaved)
	cmd.AddCommand(list, runSaved)
	addOps(cmd, rt, []op{
		{Use: "save", Short: "Save an advanced search", Method: "POST", Path: "/advanced_search", Body: true},
		{Use: "update", Short: "Update a saved advanced search", Method: "PATCH", Path: "/advanced_search/%s", Args: []string{"ID"}, Body: true},
	})
}
