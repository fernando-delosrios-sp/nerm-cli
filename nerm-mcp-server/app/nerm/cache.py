from cachetools import TTLCache

from nerm.tenancy import tenant_partition_key


class ReferenceCache:
    def __init__(self, ttl_seconds: int) -> None:
        self._cache = TTLCache(maxsize=2048, ttl=ttl_seconds)

    def _key(self, base_url: str, token: str, catalog: str) -> str:
        tenant_key = tenant_partition_key(base_url=base_url, bearer_token=token)
        return f"{tenant_key}:{catalog}"

    def get(self, base_url: str, token: str, catalog: str) -> object | None:
        return self._cache.get(self._key(base_url, token, catalog))

    def set(self, base_url: str, token: str, catalog: str, value: object) -> None:
        self._cache[self._key(base_url, token, catalog)] = value
