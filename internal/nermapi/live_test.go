package nermapi_test

import (
	"os"
	"testing"

	"github.com/sailpoint-se/nerm-cli/internal/client"
	"github.com/sailpoint-se/nerm-cli/internal/nermapi"
	"github.com/sailpoint-se/nerm-cli/internal/urlutil"
)

func TestLiveTenantProfileTypes(t *testing.T) {
	base := os.Getenv("NERM_BASE_URL")
	token := os.Getenv("NERM_BEARER_TOKEN")
	if token == "" {
		token = os.Getenv("NERM_API_TOKEN")
	}
	if base == "" || token == "" {
		t.Skip("set NERM_BASE_URL and NERM_BEARER_TOKEN for live tenant smoke")
	}
	c := client.New(urlutil.EnsureAPISuffix(base), token)
	items, err := nermapi.FetchCatalog(c, client.ProfileTypes, "profile_types")
	if err != nil {
		t.Fatal(err)
	}
	if len(items) == 0 {
		t.Fatal("expected at least one profile type")
	}
}
