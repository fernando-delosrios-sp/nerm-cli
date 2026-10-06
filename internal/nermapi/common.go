package nermapi

import (
	"encoding/json"
	"errors"
	"fmt"
	"strings"
	"time"

	"github.com/sailpoint-se/nerm-cli/internal/client"
	"github.com/sailpoint-se/nerm-cli/internal/pagination"
)

func AsErrorJSON(err error) map[string]any {
	var apiErr *client.APIError
	if errors.As(err, &apiErr) {
		return apiErr.JSON()
	}
	return map[string]any{"error": "nerm_api_error", "status": 400, "body": err.Error()}
}

func ListRecords(payload any, preferred ...string) []map[string]any {
	asMap, ok := payload.(map[string]any)
	if !ok {
		return nil
	}
	keys := append(append([]string{}, preferred...), "items")
	for _, key := range keys {
		raw, exists := asMap[key]
		if !exists {
			continue
		}
		items, ok := raw.([]any)
		if !ok {
			continue
		}
		out := make([]map[string]any, 0, len(items))
		for _, item := range items {
			if asItem, ok := item.(map[string]any); ok {
				out = append(out, NormalizeItem(asItem))
			}
		}
		return out
	}
	return nil
}

func NormalizeItem(item map[string]any) map[string]any {
	if item == nil {
		return item
	}
	if id, ok := item["id"]; ok && id != nil {
		item["id"] = fmt.Sprint(id)
	}
	return item
}

func ListResponse(result pagination.Result, limit, offset int) map[string]any {
	if result.ConfirmationNeeded != nil {
		return result.ConfirmationNeeded
	}
	out := map[string]any{
		"items":              result.Items,
		"limit":              limit,
		"offset":             offset,
		"pages_fetched":      result.Pages,
		"pagination_limited": result.PaginationLimited,
		"returned_count":     len(result.Items),
		"unique_item_count":  pagination.UniqueItemCount(result.Items),
	}
	if result.Total != nil {
		out["total"] = *result.Total
	}
	return out
}

type ListOptions struct {
	Limit    int
	Offset   int
	ForceAll bool
	Query    map[string]any
}

func List(c *client.Client, path, preferredKey string, opts ListOptions, emptyBodyContains string) (map[string]any, error) {
	limit, offset, err := pagination.Normalize(defaultInt(opts.Limit, 100), opts.Offset)
	if err != nil {
		return pagination.ValidationJSON(err), nil
	}
	fetch := func(pageOffset, pageLimit, _, _ int) (any, error) {
		params := map[string]any{
			"limit":    pageLimit,
			"offset":   pageOffset,
			"metadata": true,
		}
		for k, v := range opts.Query {
			if v != nil && v != "" {
				params[k] = v
			}
		}
		payload, err := c.Request("GET", path, params, nil, 15*time.Second)
		if err != nil {
			var apiErr *client.APIError
			if errors.As(err, &apiErr) && isEmptyCollection(apiErr, emptyBodyContains) {
				return map[string]any{preferredKey: []any{}}, nil
			}
			return nil, err
		}
		return payload, nil
	}
	result, err := pagination.Collect(limit, offset, opts.ForceAll, fetch, func(payload any) []map[string]any {
		return ListRecords(payload, preferredKey)
	})
	if err != nil {
		return nil, err
	}
	return ListResponse(result, limit, offset), nil
}

func Get(c *client.Client, path, id string) (map[string]any, error) {
	payload, err := c.Request("GET", strings.TrimRight(path, "/")+"/"+id, nil, nil, 15*time.Second)
	if err != nil {
		return nil, err
	}
	if asMap, ok := payload.(map[string]any); ok {
		return NormalizeItem(asMap), nil
	}
	return map[string]any{"result": payload}, nil
}

func isEmptyCollection(err *client.APIError, needle string) bool {
	if err == nil {
		return false
	}
	if err.Status != 400 && err.Status != 404 {
		return false
	}
	body := strings.ToLower(err.Body)
	if needle != "" && strings.Contains(body, strings.ToLower(needle)) {
		return true
	}
	var parsed map[string]any
	if json.Unmarshal([]byte(err.Body), &parsed) == nil {
		if msg, ok := parsed["error"].(string); ok && needle != "" && strings.Contains(strings.ToLower(msg), strings.ToLower(needle)) {
			return true
		}
	}
	return false
}

func defaultInt(value, fallback int) int {
	if value == 0 {
		return fallback
	}
	return value
}

func FilterBoolMap(in map[string]any) map[string]any {
	out := map[string]any{}
	for k, v := range in {
		if v == nil {
			continue
		}
		if s, ok := v.(string); ok && s == "" {
			continue
		}
		out[k] = v
	}
	if len(out) == 0 {
		return nil
	}
	return out
}
