package cli

import (
	"fmt"
	"sort"
	"strings"

	"github.com/spf13/cobra"

	"github.com/sailpoint-se/nerm-cli/internal/client"
	"github.com/sailpoint-se/nerm-cli/internal/nermapi"
)

type getter func(rt *runtime, id string) (map[string]any, error)
type lister func(rt *runtime, cmd *cobra.Command) (map[string]any, error)

func newResourceListGet(rt *runtime, use, short string, list lister, get getter, idName string) *cobra.Command {
	cmd := &cobra.Command{Use: use, Short: short}
	listCmd := &cobra.Command{
		Use:   "list",
		Short: "List " + use,
		RunE: func(cmd *cobra.Command, args []string) error {
			payload, err := list(rt, cmd)
			return handleAPI(rt, payload, err)
		},
	}
	listFlags(listCmd)
	getCmd := &cobra.Command{
		Use:   "get " + strings.ToUpper(idName),
		Short: "Get one " + use + " record",
		Args:  cobra.ExactArgs(1),
		RunE: func(cmd *cobra.Command, args []string) error {
			payload, err := get(rt, args[0])
			return handleAPI(rt, payload, err)
		},
	}
	cmd.AddCommand(listCmd, getCmd)
	return cmd
}

func newProfilesCmd(rt *runtime) *cobra.Command {
	cmd := newResourceListGet(rt, "profiles", "Profile records", func(rt *runtime, cmd *cobra.Command) (map[string]any, error) {
		return listPath(rt, cmd, client.Profiles, "profiles", "no profiles found", queryFrom(cmd, "order", "name", "profile-type-id", "status", "after-id", "updated-after"), map[string]string{
			"profile-type-id": "profile_type_id",
			"after-id":        "after_id",
			"updated-after":   "updated_after",
		})
	}, func(rt *runtime, id string) (map[string]any, error) {
		return getPath(rt, client.Profiles, id)
	}, "id")
	list := cmd.Commands()[0]
	list.Flags().String("name", "", "filter by name")
	list.Flags().String("profile-type-id", "", "filter by profile type id")
	list.Flags().String("status", "", "filter by profile status")
	list.Flags().String("after-id", "", "filter after profile id")
	list.Flags().String("updated-after", "", "filter by updated_after")
	list.Flags().Bool("exclude-attributes", false, "exclude attributes")
	attachProfileWrites(cmd, rt)
	return cmd
}

func newUsersCmd(rt *runtime) *cobra.Command {
	cmd := newResourceListGet(rt, "users", "Lifecycle and portal users", func(rt *runtime, cmd *cobra.Command) (map[string]any, error) {
		c, _, err := rt.client()
		if err != nil {
			return nil, err
		}
		limit, _ := cmd.Flags().GetInt("limit")
		offset, _ := cmd.Flags().GetInt("offset")
		forceAll, _ := cmd.Flags().GetBool("force-all")
		name, _ := cmd.Flags().GetString("name")
		login, _ := cmd.Flags().GetString("login")
		email, _ := cmd.Flags().GetString("email")
		query := queryFrom(cmd, "order", "name", "login", "title", "user-status", "type", "email", "sailpoint-identity-id")
		remap(query, map[string]string{"user-status": "user_status", "sailpoint-identity-id": "sailpoint_identity_id"})
		return nermapi.ListUsers(c, nermapi.ListOptions{Limit: limit, Offset: offset, ForceAll: forceAll, Query: query}, name, login, email)
	}, func(rt *runtime, id string) (map[string]any, error) {
		return getPath(rt, client.Users, id)
	}, "id")
	list := cmd.Commands()[0]
	list.Flags().String("name", "", "filter by name")
	list.Flags().String("login", "", "filter by login")
	list.Flags().String("title", "", "filter by title")
	list.Flags().String("user-status", "", "Active, Pending, or Disabled")
	list.Flags().String("type", "", "NeprofileUser or NeaccessUser")
	list.Flags().String("email", "", "filter by email")
	list.Flags().String("sailpoint-identity-id", "", "filter by ISC identity id")
	attachUserWrites(cmd, rt)
	return cmd
}

func newUserRolesCmd(rt *runtime) *cobra.Command {
	cmd := newResourceListGet(rt, "user-roles", "User-to-role mappings", func(rt *runtime, cmd *cobra.Command) (map[string]any, error) {
		payload, err := listPath(rt, cmd, client.UserRoles, "user_roles", "no roles found", queryFrom(cmd, "order", "user-id", "role-id"), map[string]string{"user-id": "user_id", "role-id": "role_id"})
		if err != nil || payload["error"] != nil {
			return payload, err
		}
		includeUser, _ := cmd.Flags().GetBool("include-user-details")
		includeRole, _ := cmd.Flags().GetBool("include-role-details")
		if !includeUser && !includeRole {
			return payload, nil
		}
		c, _, err := rt.client()
		if err != nil {
			return nil, err
		}
		items := itemsAsMaps(payload["items"])
		payload["items"] = nermapi.EnrichUserRoles(c, items, includeUser, includeRole)
		return payload, nil
	}, func(rt *runtime, id string) (map[string]any, error) {
		return getPath(rt, client.UserRoles, id)
	}, "id")
	list := cmd.Commands()[0]
	list.Flags().String("user-id", "", "filter by user id")
	list.Flags().String("role-id", "", "filter by role id")
	list.Flags().Bool("include-user-details", true, "enrich user fields")
	list.Flags().Bool("include-role-details", true, "enrich role fields")
	attachUserRoleWrites(cmd, rt)
	return cmd
}

func newUserManagersCmd(rt *runtime) *cobra.Command {
	cmd := newResourceListGet(rt, "user-managers", "User-manager mappings", func(rt *runtime, cmd *cobra.Command) (map[string]any, error) {
		return listPath(rt, cmd, client.UserManagers, "user_managers", "", queryFrom(cmd, "order", "user-id", "manager-id"), map[string]string{"user-id": "user_id", "manager-id": "manager_id"})
	}, func(rt *runtime, id string) (map[string]any, error) {
		return getPath(rt, client.UserManagers, id)
	}, "id")
	list := cmd.Commands()[0]
	list.Flags().String("user-id", "", "filter by user id")
	list.Flags().String("manager-id", "", "filter by manager id")
	attachUserManagerWrites(cmd, rt)
	return cmd
}

func newUserProfilesCmd(rt *runtime) *cobra.Command {
	cmd := newResourceListGet(rt, "user-profiles", "User-to-profile relationship mappings", func(rt *runtime, cmd *cobra.Command) (map[string]any, error) {
		return listPath(rt, cmd, client.UserProfiles, "user_profiles", "", queryFrom(cmd, "order", "user-id", "ne-attribute-id", "profile-id", "relationship-type"), map[string]string{
			"user-id":           "user_id",
			"ne-attribute-id":   "ne_attribute_id",
			"profile-id":        "profile_id",
			"relationship-type": "relationship_type",
		})
	}, func(rt *runtime, id string) (map[string]any, error) {
		return getPath(rt, client.UserProfiles, id)
	}, "id")
	list := cmd.Commands()[0]
	list.Flags().String("user-id", "", "filter by user id")
	list.Flags().String("profile-id", "", "filter by profile id")
	list.Flags().String("ne-attribute-id", "", "filter by relationship attribute id")
	list.Flags().String("relationship-type", "", "owner or contributor")
	attachUserProfileWrites(cmd, rt)
	return cmd
}

func newRolesCmd(rt *runtime) *cobra.Command {
	cmd := newResourceListGet(rt, "roles", "Role catalog", func(rt *runtime, cmd *cobra.Command) (map[string]any, error) {
		return listPath(rt, cmd, client.Roles, "roles", "no roles found", queryFrom(cmd, "order", "type"), nil)
	}, func(rt *runtime, id string) (map[string]any, error) {
		return getPath(rt, client.Roles, id)
	}, "id")
	cmd.Commands()[0].Flags().String("type", "", "NeprofileRole, NeaccessRole, or IdproxyRole")
	attachRoleWrites(cmd, rt)
	return cmd
}

func newRoleProfilesCmd(rt *runtime) *cobra.Command {
	cmd := newResourceListGet(rt, "role-profiles", "Role-to-profile mappings", func(rt *runtime, cmd *cobra.Command) (map[string]any, error) {
		return listPath(rt, cmd, client.RoleProfiles, "role_profiles", "", queryFrom(cmd, "order", "role-id", "profile-id"), map[string]string{"role-id": "role_id", "profile-id": "profile_id"})
	}, func(rt *runtime, id string) (map[string]any, error) {
		return getPath(rt, client.RoleProfiles, id)
	}, "id")
	list := cmd.Commands()[0]
	list.Flags().String("role-id", "", "filter by role id")
	list.Flags().String("profile-id", "", "filter by profile id")
	attachRoleProfileWrites(cmd, rt)
	return cmd
}

func newIdentityProofingCmd(rt *runtime) *cobra.Command {
	cmd := &cobra.Command{Use: "identity-proofing", Short: "Identity proofing results"}
	listCmd := &cobra.Command{
		Use:   "list",
		Short: "List identity proofing results",
		RunE: func(cmd *cobra.Command, args []string) error {
			payload, err := listPath(rt, cmd, client.IdentityProofingResults, "identity_proofing_results", "", queryFrom(cmd, "order", "profile-id", "workflow-session-id", "result"), map[string]string{
				"profile-id":          "profile_id",
				"workflow-session-id": "workflow_session_id",
			})
			return handleAPI(rt, payload, err)
		},
	}
	listFlags(listCmd)
	listCmd.Flags().String("profile-id", "", "filter by profile id")
	listCmd.Flags().String("workflow-session-id", "", "filter by workflow session id")
	listCmd.Flags().String("result", "", "pass or fail")
	cmd.AddCommand(listCmd)
	return cmd
}

func newAttributesCmd(rt *runtime) *cobra.Command {
	cmd := newResourceListGet(rt, "attributes", "Attribute catalog", func(rt *runtime, cmd *cobra.Command) (map[string]any, error) {
		c, _, err := rt.client()
		if err != nil {
			return nil, err
		}
		catalog, err := nermapi.FetchCatalog(c, client.Attributes, "ne_attributes")
		if err != nil {
			return nil, err
		}
		label, _ := cmd.Flags().GetString("label")
		dataType, _ := cmd.Flags().GetString("data-type")
		filtered := []map[string]any{}
		for _, item := range catalog {
			if label != "" && !nermapi.ContainsFold(fmtString(item["label"])+fmtString(item["name"]), label) {
				continue
			}
			if dataType != "" && !strings.EqualFold(fmtString(firstValue(item, "data_type", "type")), dataType) {
				continue
			}
			filtered = append(filtered, item)
		}
		order, _ := cmd.Flags().GetString("order")
		if order != "" {
			sortBy(filtered, order)
		}
		limit, _ := cmd.Flags().GetInt("limit")
		offset, _ := cmd.Flags().GetInt("offset")
		return nermapi.SliceCatalog(filtered, limit, offset, boolPtr(cmd, "metadata")), nil
	}, func(rt *runtime, id string) (map[string]any, error) {
		return getPath(rt, client.Attributes, id)
	}, "id")
	list := cmd.Commands()[0]
	list.Flags().String("label", "", "filter by label or name")
	list.Flags().String("data-type", "", "filter by data type")
	attachAttributeWrites(cmd, rt)
	return cmd
}

func listPath(rt *runtime, cmd *cobra.Command, path, key, emptyNeedle string, query map[string]any, names map[string]string) (map[string]any, error) {
	c, _, err := rt.client()
	if err != nil {
		return nil, err
	}
	remap(query, names)
	if cmd.Flags().Changed("exclude-attributes") {
		value, _ := cmd.Flags().GetBool("exclude-attributes")
		query["exclude_attributes"] = value
	}
	limit, _ := cmd.Flags().GetInt("limit")
	offset, _ := cmd.Flags().GetInt("offset")
	forceAll, _ := cmd.Flags().GetBool("force-all")
	return nermapi.List(c, path, key, nermapi.ListOptions{Limit: limit, Offset: offset, ForceAll: forceAll, Query: query}, emptyNeedle)
}

func getPath(rt *runtime, path, id string) (map[string]any, error) {
	c, _, err := rt.client()
	if err != nil {
		return nil, err
	}
	return nermapi.Get(c, path, id)
}

func queryFrom(cmd *cobra.Command, names ...string) map[string]any {
	out := map[string]any{}
	for _, name := range names {
		if !cmd.Flags().Changed(name) && name != "order" {
			if value, err := cmd.Flags().GetString(name); err == nil && value != "" {
				out[name] = value
			}
			continue
		}
		if value, err := cmd.Flags().GetString(name); err == nil && value != "" {
			out[name] = value
		}
	}
	return out
}

func remap(query map[string]any, names map[string]string) {
	for from, to := range names {
		if value, ok := query[from]; ok {
			query[to] = value
			delete(query, from)
		}
	}
}

func itemsAsMaps(raw any) []map[string]any {
	if items, ok := raw.([]map[string]any); ok {
		return items
	}
	list, _ := raw.([]any)
	out := []map[string]any{}
	for _, item := range list {
		if asMap, ok := item.(map[string]any); ok {
			out = append(out, asMap)
		}
	}
	return out
}

func sortBy(items []map[string]any, key string) {
	sort.SliceStable(items, func(i, j int) bool {
		return fmt.Sprint(items[i][key]) < fmt.Sprint(items[j][key])
	})
}

func toString(v any) string { return fmt.Sprint(v) }

func firstValue(item map[string]any, keys ...string) any {
	for _, key := range keys {
		if v, ok := item[key]; ok && v != nil {
			return v
		}
	}
	return nil
}
