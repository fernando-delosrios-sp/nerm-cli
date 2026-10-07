package cli

import (
	"bytes"
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"os"
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

func TestSingularRoutes(t *testing.T) {
	var gotMethod, gotPath, gotQuery, contentType string
	var gotBody string
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		gotMethod = r.Method
		gotPath = r.URL.Path
		gotQuery = r.URL.RawQuery
		contentType = r.Header.Get("Content-Type")
		raw, _ := io.ReadAll(r.Body)
		gotBody = string(raw)
		_ = json.NewEncoder(w).Encode(map[string]any{"ok": true})
	}))
	defer server.Close()
	store := profiles.NewStore(t.TempDir(), profiles.NewMemoryKeyring())
	_, _ = store.Add(profiles.AddOptions{Name: "lab", URL: server.URL, Token: "t", Use: true})

	cases := []struct {
		args       []string
		method     string
		path       string
		queryPart  string
		bodyPart   string
		fileUpload bool
	}{
		{args: []string{"profile-types", "get", "pt1"}, method: "GET", path: "/api/profile_types/pt1"},
		{args: []string{"attributes", "get", "attr1"}, method: "GET", path: "/api/ne_attributes/attr1"},
		{args: []string{"workflows", "session", "ws1"}, method: "GET", path: "/api/workflow_sessions/ws1"},
		{args: []string{"profiles", "create", "--body", `{"profile":{"name":"A"}}`}, method: "POST", path: "/api/profile", bodyPart: `"name":"A"`},
		{args: []string{"user-roles", "delete", "ur1"}, method: "DELETE", path: "/api/user_role/ur1"},
		{args: []string{"role-profiles", "delete", "rp1"}, method: "DELETE", path: "/api/role_profile/rp1"},
		{args: []string{"user-profiles", "delete", "up1"}, method: "DELETE", path: "/api/user_profile/up1"},
		{args: []string{"pages", "create-profile", "--body", `{"page":{"name":"Org"}}`}, method: "POST", path: "/api/pages/profile_pages", bodyPart: `"name":"Org"`},
		{args: []string{"workflows", "submit", "--run", "--body", `{"workflow_id":"wf1"}`}, method: "POST", path: "/api/workflow_sessions", queryPart: "run=true"},
	}
	for _, tc := range cases {
		t.Run(strings.Join(tc.args, " "), func(t *testing.T) {
			gotMethod, gotPath, gotQuery, gotBody = "", "", "", ""
			stdout := &bytes.Buffer{}
			if err := Run(append([]string{"--compact"}, tc.args...), stdout, &bytes.Buffer{}, store); err != nil {
				t.Fatalf("err=%v out=%s", err, stdout.String())
			}
			if gotMethod != tc.method || gotPath != tc.path {
				t.Fatalf("got %s %s query=%s body=%s", gotMethod, gotPath, gotQuery, gotBody)
			}
			if tc.queryPart != "" && !strings.Contains(gotQuery, tc.queryPart) {
				t.Fatalf("query=%s", gotQuery)
			}
			if tc.bodyPart != "" && !strings.Contains(gotBody, tc.bodyPart) {
				t.Fatalf("body=%s", gotBody)
			}
		})
	}

	t.Run("attachment upload", func(t *testing.T) {
		dir := t.TempDir()
		file := dir + "/note.txt"
		if err := os.WriteFile(file, []byte("hello"), 0o600); err != nil {
			t.Fatal(err)
		}
		stdout := &bytes.Buffer{}
		args := []string{"--compact", "profiles", "attachment-upload", "p1", "a1", "--file", file}
		if err := Run(args, stdout, &bytes.Buffer{}, store); err != nil {
			t.Fatalf("err=%v out=%s", err, stdout.String())
		}
		if gotMethod != "POST" || gotPath != "/api/profiles/p1/upload/a1" {
			t.Fatalf("got %s %s", gotMethod, gotPath)
		}
		if !strings.HasPrefix(contentType, "multipart/form-data") || !strings.Contains(gotBody, "hello") || !strings.Contains(gotBody, `name="file"`) {
			t.Fatalf("content-type=%s body=%s", contentType, gotBody)
		}
	})
}

func TestWriteErrorExit(t *testing.T) {
	store := profiles.NewStore(t.TempDir(), profiles.NewMemoryKeyring())
	err := Run([]string{"profiles", "list"}, &bytes.Buffer{}, &bytes.Buffer{}, store)
	if err == nil {
		t.Fatal("expected profile error")
	}
}
