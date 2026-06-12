import random
import time


def retryable_status(status_code: int) -> bool:
    return status_code == 429


def should_retry(status_code: int) -> bool:
    if status_code in (401, 403):
        return False
    return retryable_status(status_code)


def retry_sleep(attempt: int) -> None:
    base = min(2**attempt, 8)
    jitter = random.uniform(0, 0.25)
    time.sleep(base + jitter)
