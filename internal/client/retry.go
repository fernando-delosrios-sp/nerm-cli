package client

import (
	"math"
	"math/rand"
	"time"
)

func ShouldRetry(status int) bool {
	if status == 401 || status == 403 {
		return false
	}
	return status == 429
}

func RetryDelay(attempt int) time.Duration {
	base := math.Min(math.Pow(2, float64(attempt)), 8)
	jitter := rand.Float64() * 0.25
	return time.Duration((base + jitter) * float64(time.Second))
}
