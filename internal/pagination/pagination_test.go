package pagination

import "testing"

func TestCircuitBreakerWithoutForceAll(t *testing.T) {
	if applyBreaker(MaxPages+1, false) {
		t.Fatal("expected breaker to stop extra pages")
	}
	if !applyBreaker(MaxPages, false) {
		t.Fatal("expected last allowed page")
	}
	if !applyBreaker(MaxPages+20, true) {
		t.Fatal("forceAll should bypass breaker")
	}
}

func TestConfirmLarge(t *testing.T) {
	total := MaxRecords + 1
	got := ConfirmLarge(&total, false)
	if got == nil || got["error"] != "confirmation_required" {
		t.Fatalf("expected confirmation, got %#v", got)
	}
	if ConfirmLarge(&total, true) != nil {
		t.Fatal("forceAll should skip confirmation")
	}
}

func TestCollectStopsOnEmptyPage(t *testing.T) {
	pages := 0
	result, err := Collect(100, 0, false, func(offset, limit, _, _ int) (any, error) {
		pages++
		if offset == 0 {
			return map[string]any{"items": []any{map[string]any{"id": "1"}}, "total": 1}, nil
		}
		return map[string]any{"items": []any{}}, nil
	}, func(payload any) []map[string]any {
		asMap, _ := payload.(map[string]any)
		raw, _ := asMap["items"].([]any)
		out := []map[string]any{}
		for _, item := range raw {
			out = append(out, item.(map[string]any))
		}
		return out
	})
	if err != nil {
		t.Fatal(err)
	}
	if pages != 1 {
		t.Fatalf("pages=%d", pages)
	}
	if result.Total == nil || *result.Total != 1 {
		t.Fatalf("total=%v", result.Total)
	}
}

func TestExtractTotalFromMetadata(t *testing.T) {
	n := ExtractTotal(map[string]any{"_metadata": map[string]any{"total": 12.0}})
	if n == nil || *n != 12 {
		t.Fatalf("got %v", n)
	}
}
