package urlutil

import "testing"

func TestNormalizeBaseURLAddsAPIPath(t *testing.T) {
	got := NormalizeBaseURL("https://tenant.example.com", "/api")
	if got != "https://tenant.example.com/api" {
		t.Fatalf("got %q", got)
	}
}

func TestNormalizeBaseURLKeepsExistingPath(t *testing.T) {
	got := NormalizeBaseURL("https://tenant.example.com/api", "/api")
	if got != "https://tenant.example.com/api" {
		t.Fatalf("got %q", got)
	}
}

func TestEnsureAPISuffix(t *testing.T) {
	got := EnsureAPISuffix("https://tenant.nonemployee.com")
	if got != "https://tenant.nonemployee.com/api" {
		t.Fatalf("got %q", got)
	}
}
