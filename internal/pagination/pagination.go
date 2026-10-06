package pagination

const (
	MaxRecords = 5000
	PageSize   = 100
	MaxPages   = MaxRecords / PageSize
)

type FetchPage func(offset, limit, pages, collected int) (any, error)
type ParsePage func(payload any) []map[string]any

type Result struct {
	Items              []map[string]any
	Pages              int
	PaginationLimited  bool
	Total              *int
	ConfirmationNeeded map[string]any
}

func Normalize(limit, offset int) (int, int, error) {
	if limit < 1 {
		return 0, 0, errPagination("limit must be >= 1")
	}
	if offset < 0 {
		return 0, 0, errPagination("offset must be >= 0")
	}
	return limit, offset, nil
}

func NormalizeCatalog(limit, offset int) (int, int, error) {
	if limit < 0 {
		return 0, 0, errPagination("limit must be >= 0")
	}
	if offset < 0 {
		return 0, 0, errPagination("offset must be >= 0")
	}
	return limit, offset, nil
}

type paginationError string

func (e paginationError) Error() string { return string(e) }

func errPagination(msg string) error { return paginationError(msg) }

func IsValidation(err error) bool {
	_, ok := err.(paginationError)
	return ok
}

func ValidationJSON(err error) map[string]any {
	return map[string]any{
		"error":   "invalid_pagination_spec",
		"message": "Invalid pagination values for limit/offset.",
		"details": err.Error(),
	}
}

func ExtractTotal(payload any) *int {
	asMap, ok := payload.(map[string]any)
	if !ok {
		return nil
	}
	if n := coerceCount(asMap["total"]); n != nil {
		return n
	}
	for _, key := range []string{"total_count", "count"} {
		if n := coerceCount(asMap[key]); n != nil {
			return n
		}
	}
	for _, containerKey := range []string{"metadata", "meta", "pagination", "_metadata"} {
		container, ok := asMap[containerKey].(map[string]any)
		if !ok {
			continue
		}
		for _, key := range []string{"total", "total_count", "count"} {
			if n := coerceCount(container[key]); n != nil {
				return n
			}
		}
	}
	return nil
}

func UniqueItemCount(items []map[string]any) int {
	seen := map[string]struct{}{}
	withoutID := 0
	for _, item := range items {
		if id, ok := item["id"]; ok && id != nil {
			seen[stringify(id)] = struct{}{}
		} else {
			withoutID++
		}
	}
	return len(seen) + withoutID
}

func ConfirmLarge(total *int, forceAll bool) map[string]any {
	if forceAll || total == nil || *total <= MaxRecords {
		return nil
	}
	return map[string]any{
		"error": "confirmation_required",
		"message": "This query matches " + itoa(*total) + " records, which exceeds the automatic retrieval cap of " +
			itoa(MaxRecords) + ". Ask the user if they want all data.",
		"total": *total,
		"guidance": map[string]any{
			"next_step": "If user confirms, retry with --force-all to retrieve all records.",
		},
	}
}

func Collect(limit, offset int, forceAll bool, fetch FetchPage, parse ParsePage) (Result, error) {
	collected := []map[string]any{}
	currentOffset := offset
	pages := 0
	var expectedWindow *int
	var total *int

	for len(collected) < limit && applyBreaker(pages+1, forceAll) {
		if expectedWindow != nil && currentOffset >= (offset+*expectedWindow) {
			break
		}
		pageLimit := min(PageSize, limit-len(collected))
		payload, err := fetch(currentOffset, pageLimit, pages, len(collected))
		if err != nil {
			return Result{}, err
		}
		if pages == 0 {
			total = ExtractTotal(payload)
			if total != nil {
				remaining := max(*total-offset, 0)
				window := min(limit, remaining)
				expectedWindow = &window
			}
			if confirm := ConfirmLarge(total, forceAll); confirm != nil {
				return Result{Pages: pages, Total: total, ConfirmationNeeded: confirm}, nil
			}
		}
		pageItems := parse(payload)
		collected = append(collected, pageItems...)
		pages++
		if len(pageItems) == 0 {
			break
		}
		currentOffset += len(pageItems)
		if expectedWindow != nil && len(collected) >= *expectedWindow {
			break
		}
		if expectedWindow == nil && len(pageItems) < PageSize {
			break
		}
	}

	if total == nil && !forceAll && offset == 0 && len(collected) == limit && limit > 0 {
		counted := len(collected)
		probeOffset := currentOffset
		probePages := pages
		for applyBreaker(probePages+1, forceAll) {
			payload, err := fetch(probeOffset, PageSize, probePages, counted)
			if err != nil {
				return Result{}, err
			}
			pageItems := parse(payload)
			probePages++
			if len(pageItems) == 0 {
				break
			}
			counted += len(pageItems)
			probeOffset += len(pageItems)
			if len(pageItems) < PageSize {
				break
			}
		}
		total = &counted
		pages = probePages
	}

	effective := limit
	if expectedWindow != nil {
		effective = min(effective, *expectedWindow)
	}
	returned := collected
	if len(returned) > effective {
		returned = returned[:effective]
	}
	limited := !forceAll && pages >= MaxPages && len(returned) < effective
	return Result{
		Items:             returned,
		Pages:             pages,
		PaginationLimited: limited,
		Total:             total,
	}, nil
}

func applyBreaker(pagesRequested int, forceAll bool) bool {
	if forceAll {
		return true
	}
	return pagesRequested <= MaxPages
}

func coerceCount(value any) *int {
	switch typed := value.(type) {
	case int:
		if typed >= 0 {
			return &typed
		}
	case int64:
		if typed >= 0 {
			n := int(typed)
			return &n
		}
	case float64:
		if typed >= 0 {
			n := int(typed)
			return &n
		}
	case jsonNumber:
		n := typed.Int()
		if n >= 0 {
			return &n
		}
	case string:
		n, ok := atoi(typed)
		if ok {
			return &n
		}
	}
	return nil
}

type jsonNumber interface{ Int() int }

func stringify(v any) string {
	return itoaValue(v)
}
