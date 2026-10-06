package profiles

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestAddResolveAndPublicView(t *testing.T) {
	dir := t.TempDir()
	store := NewStore(dir, NewMemoryKeyring())
	profile, err := store.Add(AddOptions{
		Name:  "prod",
		URL:   "https://acme.nonemployee.com",
		Token: "super-secret-token",
		Use:   true,
	})
	if err != nil {
		t.Fatal(err)
	}
	if profile.URL != "https://acme.nonemployee.com/api" {
		t.Fatalf("url=%q", profile.URL)
	}
	conn, err := store.Resolve("")
	if err != nil {
		t.Fatal(err)
	}
	if conn.Token != "super-secret-token" {
		t.Fatalf("token=%q", conn.Token)
	}
	view := PublicView(profile, true)
	encoded := filepath.Join(dir, "config.json")
	raw, _ := os.ReadFile(encoded)
	if strings.Contains(string(raw), "super-secret-token") {
		t.Fatal("token stored in config file")
	}
	if strings.Contains(strings.Join(keys(view), ","), "token") && view["token"] != nil {
		t.Fatal("public view leaked token")
	}
}

func TestTokenEnvFallback(t *testing.T) {
	dir := t.TempDir()
	store := NewStore(dir, NewMemoryKeyring())
	_, err := store.Add(AddOptions{Name: "ci", URL: "https://ci.example.com/api", TokenEnv: "NERM_TEST_TOKEN"})
	if err != nil {
		t.Fatal(err)
	}
	t.Setenv("NERM_TEST_TOKEN", "from-env")
	conn, err := store.Resolve("ci")
	if err != nil {
		t.Fatal(err)
	}
	if conn.Token != "from-env" {
		t.Fatalf("token=%q", conn.Token)
	}
}

func TestMissingKeyringToken(t *testing.T) {
	store := NewStore(t.TempDir(), failingKeyring{})
	_, err := store.Add(AddOptions{Name: "x", URL: "https://x.example.com", Token: "abc"})
	if err == nil || !strings.Contains(err.Error(), "credential store") {
		t.Fatalf("err=%v", err)
	}
}

type failingKeyring struct{}

func (failingKeyring) Set(string, string, string) error { return ErrKeyring }
func (failingKeyring) Get(string, string) (string, error) {
	return "", ErrKeyring
}
func (failingKeyring) Delete(string, string) error { return nil }

func keys(m map[string]any) []string {
	out := make([]string, 0, len(m))
	for k := range m {
		out = append(out, k)
	}
	return out
}
