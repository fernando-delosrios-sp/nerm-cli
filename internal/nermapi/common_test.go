package nermapi

import (
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/sailpoint-se/nerm-cli/internal/client"
)

func TestListProfilesAndRawShape(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/api/profiles" {
			t.Fatalf("path=%s", r.URL.Path)
		}
		_ = json.NewEncoder(w).Encode(map[string]any{
			"profiles": []any{map[string]any{"id": 12, "name": "Acme"}},
			"total":    1,
		})
	}))
	defer server.Close()
	c := client.New(server.URL+"/api", "token")
	payload, err := List(c, client.Profiles, "profiles", ListOptions{Limit: 100}, "no profiles found")
	if err != nil {
		t.Fatal(err)
	}
	items := payload["items"].([]map[string]any)
	if items[0]["id"] != "12" {
		t.Fatalf("id not string: %#v", items[0]["id"])
	}
}

func TestAdvancedSearchRejectsSQLKeys(t *testing.T) {
	c := client.New("https://example.com/api", "t")
	payload, err := RunAdvancedSearch(c, map[string]any{"field": "name", "operator": "="})
	if err != nil {
		t.Fatal(err)
	}
	if payload["error"] != "invalid_advanced_search_spec" {
		t.Fatalf("payload=%v", payload)
	}
}

func TestCreateDelegationValidation(t *testing.T) {
	c := client.New("https://example.com/api", "t")
	payload, err := CreateDelegation(c, map[string]any{"delegate_id": "a"})
	if err != nil {
		t.Fatal(err)
	}
	if payload["error"] != "invalid_delegation_spec" {
		t.Fatalf("payload=%v", payload)
	}
}

func TestAuditInvalidSubject(t *testing.T) {
	c := client.New("https://example.com/api", "t")
	payload, err := QueryAudit(c, map[string]any{"subject_type": "Nope"}, 10, 0, false)
	if err != nil {
		t.Fatal(err)
	}
	if payload["error"] != "invalid_audit_query_spec" {
		t.Fatalf("payload=%v", payload)
	}
}

func TestRawRequestDoesNotEchoToken(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(401)
		_, _ = io.WriteString(w, `{"error":"nope"}`)
	}))
	defer server.Close()
	c := client.New(server.URL+"/api", "secret-value")
	_, err := c.Request("GET", "/users", nil, nil, 0)
	if err == nil {
		t.Fatal("expected error")
	}
	dump, _ := json.Marshal(AsErrorJSON(err))
	if strings.Contains(string(dump), "secret-value") {
		t.Fatalf("token leaked: %s", dump)
	}
}
