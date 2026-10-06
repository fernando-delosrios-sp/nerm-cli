package cli

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/sailpoint-se/nerm-cli/internal/profiles"
)

func TestCLIListProfilesJSON(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/api/profiles" {
			http.NotFound(w, r)
			return
		}
		_ = json.NewEncoder(w).Encode(map[string]any{
			"profiles": []any{map[string]any{"id": "p1", "name": "Nexus"}},
			"total":    1,
		})
	}))
	defer server.Close()

	store := profiles.NewStore(t.TempDir(), profiles.NewMemoryKeyring())
	if _, err := store.Add(profiles.AddOptions{Name: "lab", URL: server.URL, Token: "secret-token", Use: true}); err != nil {
		t.Fatal(err)
	}

	stdout := &bytes.Buffer{}
	stderr := &bytes.Buffer{}
	if err := Run([]string{"--compact", "profiles", "list", "--limit", "10"}, stdout, stderr, store); err != nil {
		t.Fatalf("err=%v out=%s", err, stdout.String())
	}
	if strings.Contains(stdout.String(), "secret-token") || strings.Contains(stderr.String(), "secret-token") {
		t.Fatal("token leaked")
	}
	var payload map[string]any
	if err := json.Unmarshal(stdout.Bytes(), &payload); err != nil {
		t.Fatal(err)
	}
	if int(payload["returned_count"].(float64)) != 1 {
		t.Fatalf("payload=%s", stdout.String())
	}
}

func TestConnectionShowOmitsToken(t *testing.T) {
	store := profiles.NewStore(t.TempDir(), profiles.NewMemoryKeyring())
	if _, err := store.Add(profiles.AddOptions{Name: "lab", URL: "https://lab.nonemployee.com", Token: "secret-token", Use: true}); err != nil {
		t.Fatal(err)
	}
	stdout := &bytes.Buffer{}
	if err := Run([]string{"--compact", "connection", "show", "lab"}, stdout, &bytes.Buffer{}, store); err != nil {
		t.Fatal(err)
	}
	if strings.Contains(stdout.String(), "secret-token") {
		t.Fatalf("leaked: %s", stdout.String())
	}
	if !strings.Contains(stdout.String(), "https://lab.nonemployee.com/api") {
		t.Fatalf("out=%s", stdout.String())
	}
}

func TestAPIRequestQuery(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Query().Get("query[limit]") != "1" {
			t.Fatalf("query=%s", r.URL.RawQuery)
		}
		_ = json.NewEncoder(w).Encode(map[string]any{"ok": true})
	}))
	defer server.Close()
	store := profiles.NewStore(t.TempDir(), profiles.NewMemoryKeyring())
	_, _ = store.Add(profiles.AddOptions{Name: "lab", URL: server.URL, Token: "t", Use: true})
	stdout := &bytes.Buffer{}
	if err := Run([]string{"--compact", "api", "request", "GET", "/profile_types", "--query", "query[limit]=1"}, stdout, &bytes.Buffer{}, store); err != nil {
		t.Fatal(err)
	}
}

func TestWriteErrorExit(t *testing.T) {
	store := profiles.NewStore(t.TempDir(), profiles.NewMemoryKeyring())
	err := Run([]string{"profiles", "list"}, &bytes.Buffer{}, &bytes.Buffer{}, store)
	if err == nil {
		t.Fatal("expected profile error")
	}
}
