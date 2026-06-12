from nerm.cache import ReferenceCache


def test_cache_set_get() -> None:
    cache = ReferenceCache(ttl_seconds=60)
    cache.set("https://tenant", "token", "profile_types", [{"id": "pt-1"}])
    assert cache.get("https://tenant", "token", "profile_types") == [{"id": "pt-1"}]
