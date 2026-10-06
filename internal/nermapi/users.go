package nermapi

import (
	"strings"
	"time"

	"github.com/sailpoint-se/nerm-cli/internal/client"
	"github.com/sailpoint-se/nerm-cli/internal/pagination"
)

func ListUsers(c *client.Client, opts ListOptions, name, login, email string) (map[string]any, error) {
	limit, offset, err := pagination.Normalize(defaultInt(opts.Limit, 100), opts.Offset)
	if err != nil {
		return pagination.ValidationJSON(err), nil
	}
	active := copyQuery(opts.Query)
	fallbacks := userFallbacks(name, login, email)
	fetch := func(pageOffset, pageLimit, pages, collected int) (any, error) {
		params := map[string]any{"limit": pageLimit, "offset": pageOffset, "metadata": true}
		for k, v := range active {
			params[k] = v
		}
		payload, err := c.Request("GET", client.Users, params, nil, 15*time.Second)
		if err == nil {
			return payload, nil
		}
		apiErr, ok := err.(*client.APIError)
		if !ok || !isEmptyCollection(apiErr, "no users found") {
			return nil, err
		}
		if !(pages == 0 && pageOffset == offset && collected == 0) {
			return map[string]any{"users": []any{}}, nil
		}
		for _, fallback := range fallbacks {
			fallbackParams := map[string]any{"limit": pageLimit, "offset": pageOffset}
			for k, v := range fallback {
				fallbackParams[k] = v
			}
			payload, ferr := c.Request("GET", client.Users, fallbackParams, nil, 15*time.Second)
			if ferr == nil {
				active = fallback
				return payload, nil
			}
			if fapi, ok := ferr.(*client.APIError); ok && isEmptyCollection(fapi, "no users found") {
				continue
			}
			return nil, ferr
		}
		return map[string]any{"users": []any{}}, nil
	}
	result, err := pagination.Collect(limit, offset, opts.ForceAll, fetch, func(payload any) []map[string]any {
		return ListRecords(payload, "users")
	})
	if err != nil {
		return nil, err
	}
	return ListResponse(result, limit, offset), nil
}

func copyQuery(in map[string]any) map[string]any {
	out := map[string]any{}
	for k, v := range in {
		if v != nil && v != "" {
			out[k] = v
		}
	}
	return out
}

func userFallbacks(name, login, email string) []map[string]any {
	var out []map[string]any
	seen := map[string]struct{}{}
	add := func(key, value string) {
		if value == "" {
			return
		}
		pair := key + "=" + value
		if _, ok := seen[pair]; ok {
			return
		}
		seen[pair] = struct{}{}
		out = append(out, map[string]any{key: value})
	}
	if name != "" && login == "" {
		add("login", normalizeLoginCandidate(name))
		add("name", strings.TrimSpace(name))
	}
	if email != "" && !strings.Contains(email, "@") && login == "" {
		add("login", normalizeLoginCandidate(email))
	}
	return out
}

func normalizeLoginCandidate(value string) string {
	text := strings.TrimSpace(value)
	replacer := strings.NewReplacer("@", " ", "_", " ", "-", " ", ".", " ")
	parts := strings.Fields(replacer.Replace(text))
	if len(parts) == 0 {
		return text
	}
	for i, part := range parts {
		parts[i] = strings.ToLower(part)
	}
	return strings.Join(parts, ".")
}
