package nermapi

import (
	"fmt"
	"strings"
	"sync"

	"github.com/sailpoint-se/nerm-cli/internal/client"
	"github.com/sailpoint-se/nerm-cli/internal/pagination"
)

const catalogPageSize = 200

type catalogKey struct {
	baseURL string
	catalog string
}

var catalogCache sync.Map

func FetchCatalog(c *client.Client, path, preferredKey string) ([]map[string]any, error) {
	key := catalogKey{baseURL: c.BaseURL, catalog: path}
	if cached, ok := catalogCache.Load(key); ok {
		return cached.([]map[string]any), nil
	}
	all := []map[string]any{}
	offset := 0
	for {
		payload, err := c.Request("GET", path, map[string]any{"limit": catalogPageSize, "offset": offset}, nil, 0)
		if err != nil {
			if apiErr, ok := err.(*client.APIError); ok && isEmptyCollection(apiErr, "no "+strings.ReplaceAll(strings.Trim(path, "/"), "_", " ")+" found") {
				break
			}
			return nil, err
		}
		page := ListRecords(payload, preferredKey)
		all = append(all, page...)
		if len(page) < catalogPageSize {
			break
		}
		offset += catalogPageSize
	}
	catalogCache.Store(key, all)
	return all, nil
}

func SliceCatalog(items []map[string]any, limit, offset int, metadata *bool) map[string]any {
	boundedLimit, boundedOffset, err := pagination.NormalizeCatalog(limit, offset)
	if err != nil {
		return pagination.ValidationJSON(err)
	}
	end := boundedOffset + boundedLimit
	if boundedOffset > len(items) {
		boundedOffset = len(items)
	}
	if end > len(items) {
		end = len(items)
	}
	sliced := items[boundedOffset:end]
	out := map[string]any{
		"items":  sliced,
		"limit":  boundedLimit,
		"offset": boundedOffset,
		"total":  len(items),
	}
	if metadata != nil && !*metadata {
		delete(out, "total")
	}
	return out
}

func FindByID(items []map[string]any, id string) (map[string]any, error) {
	for _, item := range items {
		if fmt.Sprint(item["id"]) == id {
			return item, nil
		}
	}
	return nil, &client.APIError{Status: 404, Body: "resource " + id + " not found"}
}

func ContainsFold(haystack, needle string) bool {
	return strings.Contains(strings.ToLower(haystack), strings.ToLower(strings.TrimSpace(needle)))
}
