from nerm.client.retry import should_retry


def test_retry_policy() -> None:
    assert should_retry(429) is True
    assert should_retry(401) is False
    assert should_retry(403) is False
