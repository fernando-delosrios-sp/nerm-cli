package pagination

import (
	"fmt"
	"strconv"
	"strings"
)

func itoa(n int) string {
	return strconv.Itoa(n)
}

func atoi(text string) (int, bool) {
	text = strings.TrimSpace(text)
	if text == "" {
		return 0, false
	}
	n, err := strconv.Atoi(text)
	if err != nil || n < 0 {
		return 0, false
	}
	return n, true
}

func itoaValue(v any) string {
	return fmt.Sprint(v)
}
