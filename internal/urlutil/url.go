package urlutil

import (
	"net/url"
	"strings"
)

func NormalizeBaseURL(baseURL, apiBasePath string) string {
	parsed, err := url.Parse(strings.TrimSpace(baseURL))
	if err != nil || parsed.Scheme == "" || parsed.Host == "" {
		return strings.TrimRight(strings.TrimSpace(baseURL), "/")
	}
	if parsed.Path != "" && parsed.Path != "/" {
		return strings.TrimRight(parsed.String(), "/")
	}
	parsed.Path = "/" + strings.Trim(apiBasePath, "/")
	return strings.TrimRight(parsed.String(), "/")
}

func JoinPath(base, path string) string {
	base = strings.TrimRight(base, "/")
	if !strings.HasPrefix(path, "/") {
		path = "/" + path
	}
	return base + path
}

func EnsureAPISuffix(raw string) string {
	normalized := NormalizeBaseURL(raw, "/api")
	if strings.HasSuffix(normalized, "/api") {
		return normalized
	}
	return normalized + "/api"
}
