package client

import (
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"strings"
	"sync/atomic"
	"testing"
	"time"
)

func TestRetryOn429(t *testing.T) {
	var hits atomic.Int32
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Header.Get("Authorization") == "" {
			t.Error("missing authorization")
		}
		n := hits.Add(1)
		if n < 3 {
			w.WriteHeader(429)
			_, _ = w.Write([]byte(`{"error":"slow down"}`))
			return
		}
		_ = json.NewEncoder(w).Encode(map[string]any{"profiles": []any{}})
	}))
	defer server.Close()

	c := New(server.URL+"/api", "secret-token")
	c.RetrySleep = func(int) time.Duration { return 0 }
	payload, err := c.Request("GET", "/profiles", map[string]any{"limit": 1}, nil, time.Second)
	if err != nil {
		t.Fatal(err)
	}
	if hits.Load() != 3 {
		t.Fatalf("hits=%d", hits.Load())
	}
	asMap := payload.(map[string]any)
	if _, ok := asMap["profiles"]; !ok {
		t.Fatalf("payload=%v", payload)
	}
}

func TestDoesNotRetry401(t *testing.T) {
	var hits atomic.Int32
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		hits.Add(1)
		w.WriteHeader(401)
		_, _ = io.WriteString(w, `{"error":"unauthorized"}`)
	}))
	defer server.Close()
	c := New(server.URL, "tok")
	c.RetrySleep = func(int) time.Duration { return 0 }
	_, err := c.Request("GET", "/users", nil, nil, time.Second)
	if err == nil {
		t.Fatal("expected error")
	}
	if hits.Load() != 1 {
		t.Fatalf("hits=%d", hits.Load())
	}
	if strings.Contains(err.Error(), "tok") {
		t.Fatalf("token leaked in error: %v", err)
	}
}

func TestNormalizeBearer(t *testing.T) {
	if got := NormalizeBearer("abc"); got != "Bearer abc" {
		t.Fatalf("got %q", got)
	}
	if got := NormalizeBearer("Bearer abc"); got != "Bearer abc" {
		t.Fatalf("got %q", got)
	}
}
