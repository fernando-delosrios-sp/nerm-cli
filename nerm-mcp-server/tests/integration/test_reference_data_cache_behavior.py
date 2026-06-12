from nerm.cache import ReferenceCache


def test_reference_cache_reuses_value() -> None:
    cache = ReferenceCache(ttl_seconds=120)
    cache.set("https://tenant", "token", "attributes", ["x"])
    assert cache.get("https://tenant", "token", "attributes") == ["x"]
