package nermapi

import (
	"fmt"
	"strings"
	"time"

	"github.com/sailpoint-se/nerm-cli/internal/client"
)

func ListDelegations(c *client.Client, opts ListOptions, includeUserDetails bool) (map[string]any, error) {
	result, err := List(c, client.Delegations, "delegations", opts, "no delegations found")
	if err != nil || result["error"] != nil || !includeUserDetails {
		return result, err
	}
	items, _ := result["items"].([]map[string]any)
	if len(items) == 0 {
		if raw, ok := result["items"].([]any); ok {
			items = mapsFromAny(raw)
		}
	}
	if len(items) == 0 {
		return result, nil
	}
	ids := map[string]struct{}{}
	for _, item := range items {
		ids[fmt.Sprint(item["delegator_id"])] = struct{}{}
		ids[fmt.Sprint(item["delegate_id"])] = struct{}{}
	}
	users := fetchUsers(c, ids)
	for _, item := range items {
		enrichDelegation(item, users)
	}
	result["items"] = items
	return result, nil
}

func CreateDelegation(c *client.Client, payload map[string]any) (map[string]any, error) {
	delegation, errJSON := normalizeDelegationWrite(payload, false)
	if errJSON != nil {
		return errJSON, nil
	}
	if msg := validateFutureExpiration(delegation); msg != nil {
		return msg, nil
	}
	result, err := c.Request("POST", client.Delegations, nil, map[string]any{"delegation": delegation}, 30*time.Second)
	if err != nil {
		if mapped := mapExpirationError(err); mapped != nil {
			return mapped, nil
		}
		return nil, err
	}
	return wrapDelegation(result), nil
}

func UpdateDelegation(c *client.Client, id string, payload map[string]any) (map[string]any, error) {
	delegation, errJSON := normalizeDelegationWrite(payload, true)
	if errJSON != nil {
		return errJSON, nil
	}
	if len(delegation) == 0 {
		return map[string]any{
			"error":   "invalid_delegation_spec",
			"message": "delegation payload must include at least one updatable field.",
		}, nil
	}
	if msg := validateFutureExpiration(delegation); msg != nil {
		return msg, nil
	}
	result, err := c.Request("PATCH", client.Delegations+"/"+id, nil, map[string]any{"delegation": delegation}, 30*time.Second)
	if err != nil {
		if mapped := mapExpirationError(err); mapped != nil {
			return mapped, nil
		}
		return nil, err
	}
	return wrapDelegation(result), nil
}

func DeleteDelegation(c *client.Client, id string) (map[string]any, error) {
	result, err := c.Request("DELETE", client.Delegations+"/"+id, nil, nil, 30*time.Second)
	if err != nil {
		return nil, err
	}
	if asMap, ok := result.(map[string]any); ok {
		return asMap, nil
	}
	return map[string]any{"message": fmt.Sprint(result)}, nil
}

func wrapDelegation(result any) map[string]any {
	asMap, ok := result.(map[string]any)
	if !ok {
		return map[string]any{"delegation": result}
	}
	if inner, ok := asMap["delegation"].(map[string]any); ok {
		return map[string]any{"delegation": NormalizeItem(inner)}
	}
	return map[string]any{"delegation": NormalizeItem(asMap)}
}

func normalizeDelegationWrite(payload map[string]any, update bool) (map[string]any, map[string]any) {
	if inner, ok := payload["delegation"].(map[string]any); ok {
		payload = inner
	}
	out := map[string]any{}
	if v := firstString(payload, "delegator_id", "delegator_user_id"); v != "" {
		out["delegator_id"] = v
	}
	if v := firstString(payload, "delegate_id", "delegate_user_id", "delegatee_id"); v != "" {
		out["delegate_id"] = v
	}
	if v := firstString(payload, "expiration", "expiration_date", "expires_at", "end_date"); v != "" {
		out["expiration"] = v
	}
	if !update {
		if out["delegator_id"] == nil || out["delegate_id"] == nil {
			return nil, map[string]any{
				"error":   "invalid_delegation_spec",
				"message": "delegation payload requires delegator_id and delegate_id.",
			}
		}
	}
	return out, nil
}

func validateFutureExpiration(payload map[string]any) map[string]any {
	raw, _ := payload["expiration"].(string)
	if strings.TrimSpace(raw) == "" {
		return nil
	}
	parsed, err := time.Parse(time.RFC3339, strings.ReplaceAll(raw, "Z", "+00:00"))
	if err != nil {
		if day, dayErr := time.Parse("2006-01-02", raw); dayErr == nil {
			now := time.Now().UTC()
			parsed = time.Date(day.Year(), day.Month(), day.Day(), now.Hour(), now.Minute(), now.Second(), now.Nanosecond(), time.UTC)
			payload["expiration"] = parsed.Format(time.RFC3339Nano)
		} else {
			return map[string]any{
				"error":   "invalid_delegation_spec",
				"message": "Delegation expiration must be a valid ISO-8601 date-time string.",
			}
		}
	}
	if !parsed.After(time.Now().UTC()) {
		return map[string]any{
			"error":   "invalid_delegation_spec",
			"message": "Delegation expiration must be after today.",
		}
	}
	return nil
}

func mapExpirationError(err error) map[string]any {
	apiErr, ok := err.(*client.APIError)
	if !ok || apiErr.Status != 400 {
		return nil
	}
	if !strings.Contains(apiErr.Body, "Expiration must be after today") {
		return nil
	}
	return map[string]any{
		"error":   "invalid_delegation_spec",
		"message": "Delegation expiration must be after today.",
		"details": apiErr.Body,
	}
}

func firstString(payload map[string]any, keys ...string) string {
	for _, key := range keys {
		if v, ok := payload[key]; ok && v != nil {
			return strings.TrimSpace(fmt.Sprint(v))
		}
	}
	return ""
}

func mapsFromAny(raw []any) []map[string]any {
	out := make([]map[string]any, 0, len(raw))
	for _, item := range raw {
		if asMap, ok := item.(map[string]any); ok {
			out = append(out, asMap)
		}
	}
	return out
}

func fetchUsers(c *client.Client, ids map[string]struct{}) map[string]map[string]any {
	out := map[string]map[string]any{}
	for id := range ids {
		if id == "" || id == "<nil>" {
			continue
		}
		payload, err := c.Request("GET", client.Users+"/"+id, nil, nil, 15*time.Second)
		if err != nil {
			continue
		}
		asMap, ok := payload.(map[string]any)
		if !ok {
			continue
		}
		out[id] = extractIdentity(asMap, "user", "users")
	}
	return out
}

func extractIdentity(payload map[string]any, singular, plural string) map[string]any {
	if inner, ok := payload[singular].(map[string]any); ok {
		return NormalizeItem(inner)
	}
	if list, ok := payload[plural].([]any); ok && len(list) > 0 {
		if inner, ok := list[0].(map[string]any); ok {
			return NormalizeItem(inner)
		}
	}
	return NormalizeItem(payload)
}

func enrichDelegation(item map[string]any, users map[string]map[string]any) {
	delegator := users[fmt.Sprint(item["delegator_id"])]
	delegate := users[fmt.Sprint(item["delegate_id"])]
	item["delegator_name"] = firstNonEmpty(delegator, "name", "full_name", "display_name")
	item["delegator_login"] = firstNonEmpty(delegator, "login", "uid", "username")
	item["delegator_email"] = firstNonEmpty(delegator, "email", "mail")
	item["delegate_name"] = firstNonEmpty(delegate, "name", "full_name", "display_name")
	item["delegate_login"] = firstNonEmpty(delegate, "login", "uid", "username")
	item["delegate_email"] = firstNonEmpty(delegate, "email", "mail")
}

func firstNonEmpty(item map[string]any, keys ...string) any {
	for _, key := range keys {
		if v, ok := item[key]; ok && v != nil && fmt.Sprint(v) != "" {
			return v
		}
	}
	return nil
}

func EnrichUserRoles(c *client.Client, items []map[string]any, includeUser, includeRole bool) []map[string]any {
	userIDs := map[string]struct{}{}
	roleIDs := map[string]struct{}{}
	for _, item := range items {
		if includeUser {
			userIDs[fmt.Sprint(item["user_id"])] = struct{}{}
		}
		if includeRole {
			roleIDs[fmt.Sprint(item["role_id"])] = struct{}{}
		}
	}
	users := map[string]map[string]any{}
	roles := map[string]map[string]any{}
	if includeUser {
		users = fetchUsers(c, userIDs)
	}
	if includeRole {
		for id := range roleIDs {
			payload, err := c.Request("GET", client.Roles+"/"+id, nil, nil, 15*time.Second)
			if err != nil {
				continue
			}
			if asMap, ok := payload.(map[string]any); ok {
				roles[id] = extractIdentity(asMap, "role", "roles")
			}
		}
	}
	for _, item := range items {
		if includeUser {
			user := users[fmt.Sprint(item["user_id"])]
			item["user_name"] = firstNonEmpty(user, "name")
			item["user_login"] = firstNonEmpty(user, "login", "uid", "username")
			item["user_email"] = firstNonEmpty(user, "email", "mail")
			item["user_status"] = firstNonEmpty(user, "status")
			item["user_type"] = firstNonEmpty(user, "type")
		}
		if includeRole {
			role := roles[fmt.Sprint(item["role_id"])]
			item["role_name"] = firstNonEmpty(role, "name")
			item["role_uid"] = firstNonEmpty(role, "uid")
			item["role_private"] = firstNonEmpty(role, "private_role")
			item["role_groups"] = firstNonEmpty(role, "groups")
		}
	}
	return items
}
