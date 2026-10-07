package client

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"mime/multipart"
	"net/http"
	"net/url"
	"strings"
	"time"

	"github.com/sailpoint-se/nerm-cli/internal/urlutil"
)

type APIError struct {
	Status int
	Body   string
}

func (e *APIError) Error() string {
	return fmt.Sprintf("HTTP %d: %s", e.Status, e.Body)
}

func (e *APIError) JSON() map[string]any {
	return map[string]any{"error": "nerm_api_error", "status": e.Status, "body": e.Body}
}

type Client struct {
	BaseURL    string
	Token      string
	HTTP       *http.Client
	MaxTries   int
	RetrySleep func(attempt int) time.Duration
}

func New(baseURL, token string) *Client {
	return &Client{
		BaseURL:    strings.TrimRight(baseURL, "/"),
		Token:      NormalizeBearer(token),
		HTTP:       &http.Client{Timeout: 120 * time.Second},
		MaxTries:   4,
		RetrySleep: RetryDelay,
	}
}

func NormalizeBearer(token string) string {
	token = strings.TrimSpace(token)
	if token == "" {
		return token
	}
	if strings.HasPrefix(strings.ToLower(token), "bearer ") {
		return "Bearer " + strings.TrimSpace(token[7:])
	}
	return "Bearer " + token
}

func (c *Client) Request(method, path string, query map[string]any, body any, timeout time.Duration) (any, error) {
	var payload []byte
	contentType := ""
	if body != nil {
		var err error
		payload, err = json.Marshal(body)
		if err != nil {
			return nil, err
		}
		contentType = "application/json"
	}
	return c.request(method, path, query, contentType, payload, timeout)
}

func (c *Client) RequestFile(method, path string, query map[string]any, field, filename string, content []byte, timeout time.Duration) (any, error) {
	var buf bytes.Buffer
	writer := multipart.NewWriter(&buf)
	part, err := writer.CreateFormFile(field, filename)
	if err != nil {
		return nil, err
	}
	if _, err := part.Write(content); err != nil {
		return nil, err
	}
	if err := writer.Close(); err != nil {
		return nil, err
	}
	return c.request(method, path, query, writer.FormDataContentType(), buf.Bytes(), timeout)
}

func (c *Client) request(method, path string, query map[string]any, contentType string, payload []byte, timeout time.Duration) (any, error) {
	full := urlutil.JoinPath(c.BaseURL, path)
	if encoded := encodeQuery(query); encoded != "" {
		if strings.Contains(full, "?") {
			full += "&" + encoded
		} else {
			full += "?" + encoded
		}
	}

	tries := c.MaxTries
	if tries <= 0 {
		tries = 1
	}
	var lastErr error
	for attempt := 0; attempt < tries; attempt++ {
		req, err := http.NewRequest(strings.ToUpper(method), full, bytes.NewReader(payload))
		if err != nil {
			return nil, err
		}
		req.Header.Set("Authorization", c.Token)
		req.Header.Set("Accept", "application/json")
		if contentType != "" {
			req.Header.Set("Content-Type", contentType)
		}
		httpClient := c.HTTP
		if timeout > 0 {
			clone := *c.HTTP
			clone.Timeout = timeout
			httpClient = &clone
		}
		resp, err := httpClient.Do(req)
		if err != nil {
			lastErr = &APIError{Status: 502, Body: "transport error: " + err.Error()}
			if attempt < tries-1 {
				time.Sleep(c.sleep(attempt))
				continue
			}
			return nil, lastErr
		}
		raw, _ := io.ReadAll(resp.Body)
		resp.Body.Close()
		if resp.StatusCode < 400 {
			return decodeBody(raw)
		}
		if attempt < tries-1 && ShouldRetry(resp.StatusCode) {
			time.Sleep(c.sleep(attempt))
			continue
		}
		return nil, &APIError{Status: resp.StatusCode, Body: string(raw)}
	}
	if lastErr != nil {
		return nil, lastErr
	}
	return nil, &APIError{Status: 500, Body: "retry loop exhausted"}
}

func (c *Client) sleep(attempt int) time.Duration {
	if c.RetrySleep != nil {
		return c.RetrySleep(attempt)
	}
	return RetryDelay(attempt)
}

func decodeBody(raw []byte) (any, error) {
	trimmed := bytes.TrimSpace(raw)
	if len(trimmed) == 0 {
		return map[string]any{}, nil
	}
	var data any
	if err := json.Unmarshal(trimmed, &data); err != nil {
		return nil, &APIError{Status: 502, Body: "invalid JSON response: " + err.Error()}
	}
	if asMap, ok := data.(map[string]any); ok {
		return asMap, nil
	}
	return map[string]any{"items": data}, nil
}

func encodeQuery(query map[string]any) string {
	if len(query) == 0 {
		return ""
	}
	values := url.Values{}
	for key, value := range query {
		if value == nil {
			continue
		}
		switch typed := value.(type) {
		case string:
			if typed == "" {
				continue
			}
			values.Set(key, typed)
		case bool:
			if typed {
				values.Set(key, "true")
			} else {
				values.Set(key, "false")
			}
		case int:
			values.Set(key, fmt.Sprintf("%d", typed))
		default:
			values.Set(key, fmt.Sprint(typed))
		}
	}
	return values.Encode()
}
