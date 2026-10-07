package cli

import (
	"strings"
	"time"

	"github.com/spf13/cobra"

	"github.com/sailpoint-se/nerm-cli/internal/client"
	"github.com/sailpoint-se/nerm-cli/internal/nermapi"
)

func newDelegationsCmd(rt *runtime) *cobra.Command {
	cmd := &cobra.Command{Use: "delegations", Short: "User delegation relationships"}
	listCmd := &cobra.Command{
		Use:   "list",
		Short: "List delegations",
		RunE: func(cmd *cobra.Command, args []string) error {
			c, _, err := rt.client()
			if err != nil {
				return writeJSON(rt, map[string]any{"error": "profile_error", "message": err.Error()})
			}
			query := queryFrom(cmd, "delegate-id", "delegator-id")
			remap(query, map[string]string{"delegate-id": "delegate_id", "delegator-id": "delegator_id"})
			if cmd.Flags().Changed("expired") {
				expired, _ := cmd.Flags().GetBool("expired")
				query["expired"] = expired
			}
			limit, _ := cmd.Flags().GetInt("limit")
			offset, _ := cmd.Flags().GetInt("offset")
			forceAll, _ := cmd.Flags().GetBool("force-all")
			includeUsers, _ := cmd.Flags().GetBool("include-user-details")
			payload, err := nermapi.ListDelegations(c, nermapi.ListOptions{Limit: limit, Offset: offset, ForceAll: forceAll, Query: query}, includeUsers)
			return handleAPI(rt, payload, err)
		},
	}
	listFlags(listCmd)
	listCmd.Flags().String("delegate-id", "", "filter by delegate user id")
	listCmd.Flags().String("delegator-id", "", "filter by delegator user id")
	listCmd.Flags().Bool("expired", false, "filter expired delegations")
	listCmd.Flags().Bool("include-user-details", true, "enrich user identity fields")

	getCmd := &cobra.Command{
		Use:   "get ID",
		Short: "Get one delegation",
		Args:  cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			payload, err := getPath(rt, client.Delegations, args[0])
			return handleAPI(rt, payload, err)
		},
	}

	var createBody, createFile string
	createCmd := &cobra.Command{
		Use:   "create",
		Short: "Create a delegation",
		RunE: func(cmd *cobra.Command, args []string) error {
			body, err := readJSONFlag(createBody, createFile)
			if err != nil {
				return err
			}
			c, _, err := rt.client()
			if err != nil {
				return writeJSON(rt, map[string]any{"error": "profile_error", "message": err.Error()})
			}
			payload, err := nermapi.CreateDelegation(c, body)
			return handleAPI(rt, payload, err)
		},
	}
	createCmd.Flags().StringVar(&createBody, "body", "", "JSON body")
	createCmd.Flags().StringVar(&createFile, "body-file", "", "JSON body file")

	var updateBody, updateFile string
	updateCmd := &cobra.Command{
		Use:   "update ID",
		Short: "Update a delegation",
		Args:  cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			body, err := readJSONFlag(updateBody, updateFile)
			if err != nil {
				return err
			}
			c, _, err := rt.client()
			if err != nil {
				return writeJSON(rt, map[string]any{"error": "profile_error", "message": err.Error()})
			}
			payload, err := nermapi.UpdateDelegation(c, args[0], body)
			return handleAPI(rt, payload, err)
		},
	}
	updateCmd.Flags().StringVar(&updateBody, "body", "", "JSON body")
	updateCmd.Flags().StringVar(&updateFile, "body-file", "", "JSON body file")

	deleteCmd := &cobra.Command{
		Use:   "delete ID",
		Short: "Delete a delegation",
		Args:  cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			c, _, err := rt.client()
			if err != nil {
				return writeJSON(rt, map[string]any{"error": "profile_error", "message": err.Error()})
			}
			payload, err := nermapi.DeleteDelegation(c, args[0])
			return handleAPI(rt, payload, err)
		},
	}

	cmd.AddCommand(listCmd, getCmd, createCmd, updateCmd, deleteCmd)
	return cmd
}

func newWorkflowsCmd(rt *runtime) *cobra.Command {
	cmd := &cobra.Command{Use: "workflows", Short: "Workflow sessions and jobs"}
	sessions := &cobra.Command{
		Use:   "sessions",
		Short: "List workflow sessions",
		RunE: func(cmd *cobra.Command, args []string) error {
			payload, err := listPath(rt, cmd, client.WorkflowSessions, "workflow_sessions", "", queryFrom(cmd, "order", "profile-id", "uid", "workflow-id", "requester-id", "status"), map[string]string{
				"profile-id":   "profile_id",
				"workflow-id":  "workflow_id",
				"requester-id": "requester_id",
			})
			return handleAPI(rt, payload, err)
		},
	}
	listFlags(sessions)
	sessions.Flags().String("profile-id", "", "filter by profile id")
	sessions.Flags().String("uid", "", "filter by uid")
	sessions.Flags().String("workflow-id", "", "filter by workflow id")
	sessions.Flags().String("requester-id", "", "filter by requester id")
	sessions.Flags().String("status", "", "filter by workflow status")

	session := &cobra.Command{
		Use:   "session ID",
		Short: "Get one workflow session",
		Args:  cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			payload, err := getPath(rt, client.WorkflowSessions, args[0])
			return handleAPI(rt, payload, err)
		},
	}

	statuses := &cobra.Command{
		Use:   "statuses",
		Short: "List distinct workflow session statuses",
		RunE: func(cmd *cobra.Command, args []string) error {
			payload, err := listPath(rt, cmd, client.WorkflowSessions, "workflow_sessions", "", queryFrom(cmd, "order", "profile-id", "uid", "workflow-id", "requester-id"), map[string]string{
				"profile-id":   "profile_id",
				"workflow-id":  "workflow_id",
				"requester-id": "requester_id",
			})
			if err != nil || payload["error"] != nil {
				return handleAPI(rt, payload, err)
			}
			return writeJSON(rt, nermapi.WorkflowStatuses(payload))
		},
	}
	listFlags(statuses)
	statuses.Flags().String("profile-id", "", "filter by profile id")
	statuses.Flags().String("uid", "", "filter by uid")
	statuses.Flags().String("workflow-id", "", "filter by workflow id")
	statuses.Flags().String("requester-id", "", "filter by requester id")

	var submitBody, submitFile string
	submit := &cobra.Command{
		Use:   "submit",
		Short: "Submit a workflow session",
		RunE: func(cmd *cobra.Command, args []string) error {
			body, err := readJSONFlag(submitBody, submitFile)
			if err != nil {
				return err
			}
			c, _, err := rt.client()
			if err != nil {
				return writeJSON(rt, map[string]any{"error": "profile_error", "message": err.Error()})
			}
			payload, err := nermapi.SubmitWorkflow(c, body, boolPtr(cmd, "run"))
			return handleAPI(rt, payload, err)
		},
	}
	submit.Flags().StringVar(&submitBody, "body", "", "JSON body")
	submit.Flags().StringVar(&submitFile, "body-file", "", "JSON body file")
	submit.Flags().Bool("run", false, "run the session after a successful create")

	job := &cobra.Command{
		Use:   "job ID",
		Short: "Get asynchronous job status",
		Args:  cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			c, _, err := rt.client()
			if err != nil {
				return writeJSON(rt, map[string]any{"error": "profile_error", "message": err.Error()})
			}
			payload, err := c.Request("GET", client.JobStatus, map[string]any{"job_id": args[0]}, nil, 15*time.Second)
			if err != nil {
				return handleAPI(rt, nil, err)
			}
			asMap, _ := payload.(map[string]any)
			if asMap == nil {
				asMap = map[string]any{"result": payload}
			}
			asMap["requested_job_id"] = args[0]
			return writeJSON(rt, asMap)
		},
	}

	cmd.AddCommand(sessions, session, statuses, submit, job)
	addOps(cmd, rt, []op{
		{Use: "update", Short: "Update a workflow session", Method: "PATCH", Path: "/workflow_sessions/%s", Args: []string{"ID"}, Body: true, Query: []flagSpec{{name: "run", api: "run", help: "run the session after a successful update", kind: "bool"}}},
		{Use: "attachment", Short: "Get a workflow session attachment URL", Method: "GET", Path: "/workflow_sessions/%s/upload/%s", Args: []string{"ID", "ATTRIBUTE_ID"}},
		{Use: "attachment-upload", Short: "Upload a workflow session attachment", Method: "POST", Path: "/workflow_sessions/%s/upload/%s", Args: []string{"ID", "ATTRIBUTE_ID"}, File: true},
	})
	addOps(cmd, rt, workflowTemplateOps())
	return cmd
}

func newAuditCmd(rt *runtime) *cobra.Command {
	cmd := &cobra.Command{Use: "audit", Short: "Audit event queries"}
	query := &cobra.Command{
		Use:   "query",
		Short: "Query audit events",
		RunE: func(cmd *cobra.Command, args []string) error {
			c, _, err := rt.client()
			if err != nil {
				return writeJSON(rt, map[string]any{"error": "profile_error", "message": err.Error()})
			}
			filters := map[string]any{}
			addFilter := func(flag, key string) {
				value, _ := cmd.Flags().GetString(flag)
				if value != "" {
					filters[key] = value
				}
			}
			addFilter("subject-type", "subject_type")
			addFilter("event-type", "type")
			addFilter("subject-id", "subject_id")
			addFilter("workflow-name", "workflow_name")
			addFilter("workflow-uid", "workflow_uid")
			addFilter("workflow-profile-type", "workflow_profile_type")
			addFilter("profile-type", "profile_type")
			limit, _ := cmd.Flags().GetInt("limit")
			offset, _ := cmd.Flags().GetInt("offset")
			forceAll, _ := cmd.Flags().GetBool("force-all")
			payload, err := nermapi.QueryAudit(c, filters, limit, offset, forceAll)
			return handleAPI(rt, payload, err)
		},
	}
	query.Flags().Int("limit", 100, "page size / retrieval window")
	query.Flags().Int("offset", 0, "result offset")
	query.Flags().Bool("force-all", true, "retrieve the full audit trail from offset")
	query.Flags().String("subject-type", "", "audit subject type")
	query.Flags().String("event-type", "", "audit event type (maps to type)")
	query.Flags().String("subject-id", "", "subject id")
	query.Flags().String("workflow-name", "", "workflow name")
	query.Flags().String("workflow-uid", "", "workflow uid")
	query.Flags().String("workflow-profile-type", "", "workflow profile type")
	query.Flags().String("profile-type", "", "profile type")
	cmd.AddCommand(query)
	return cmd
}

func newSearchCmd(rt *runtime) *cobra.Command {
	cmd := &cobra.Command{Use: "search", Short: "Advanced profile search"}
	var body, bodyFile string
	run := &cobra.Command{
		Use:   "run",
		Short: "Run an advanced search",
		RunE: func(cmd *cobra.Command, args []string) error {
			payload, err := readJSONFlag(body, bodyFile)
			if err != nil {
				return err
			}
			c, _, err := rt.client()
			if err != nil {
				return writeJSON(rt, map[string]any{"error": "profile_error", "message": err.Error()})
			}
			result, err := nermapi.RunAdvancedSearch(c, payload)
			return handleAPI(rt, result, err)
		},
	}
	run.Flags().StringVar(&body, "body", "", "JSON body")
	run.Flags().StringVar(&bodyFile, "body-file", "", "JSON body file")
	cmd.AddCommand(run)
	attachSearchOps(cmd, rt)
	return cmd
}

func newAPICmd(rt *runtime) *cobra.Command {
	cmd := &cobra.Command{Use: "api", Short: "Raw NERM REST escape hatch"}
	var body, bodyFile string
	var query []string
	request := &cobra.Command{
		Use:   "request METHOD PATH",
		Short: "Call a NERM REST path under the profile /api base",
		Args:  cobra.ExactArgs(2),
		RunE: func(cmd *cobra.Command, args []string) error {
			method := strings.ToUpper(args[0])
			path := args[1]
			if strings.HasPrefix(path, "/api/") || path == "/api" {
				return writeJSON(rt, map[string]any{"error": "invalid_request", "message": "path must be a resource under /api, for example /profiles"})
			}
			var payload map[string]any
			var err error
			if cmd.Flags().Changed("body") || cmd.Flags().Changed("body-file") || (method != "GET" && method != "DELETE") {
				payload, err = readJSONFlag(body, bodyFile)
				if err != nil {
					return err
				}
			}
			params := map[string]any{}
			for _, item := range query {
				key, value, ok := strings.Cut(item, "=")
				if !ok {
					return writeJSON(rt, map[string]any{"error": "invalid_request", "message": "query must be key=value: " + item})
				}
				params[key] = value
			}
			c, _, err := rt.client()
			if err != nil {
				return writeJSON(rt, map[string]any{"error": "profile_error", "message": err.Error()})
			}
			var reqBody any
			if payload != nil && len(payload) > 0 {
				reqBody = payload
			}
			result, err := c.Request(method, path, params, reqBody, 120*time.Second)
			if err != nil {
				return handleAPI(rt, nil, err)
			}
			if asMap, ok := result.(map[string]any); ok {
				return writeJSON(rt, asMap)
			}
			return writeJSON(rt, map[string]any{"result": result})
		},
	}
	request.Flags().StringVar(&body, "body", "", "JSON body")
	request.Flags().StringVar(&bodyFile, "body-file", "", "JSON body file")
	request.Flags().StringArrayVar(&query, "query", nil, "query parameter key=value (repeatable)")
	cmd.AddCommand(request)
	return cmd
}
