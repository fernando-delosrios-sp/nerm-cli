from nerm.cache import ReferenceCache


def test_multi_tenant_cache_isolated() -> None:
    cache = ReferenceCache(ttl_seconds=60)
    cache.set("https://tenant-a", "token-a", "profile_types", ["A"])
    cache.set("https://tenant-b", "token-b", "profile_types", ["B"])
    assert cache.get("https://tenant-a", "token-a", "profile_types") == ["A"]
    assert cache.get("https://tenant-b", "token-b", "profile_types") == ["B"]
