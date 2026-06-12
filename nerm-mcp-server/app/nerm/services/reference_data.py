from nerm.cache import ReferenceCache


def cached_catalog_fetch(cache: ReferenceCache, base_url: str, token: str, catalog: str, loader: callable) -> object:
    cached = cache.get(base_url=base_url, token=token, catalog=catalog)
    if cached is not None:
        return cached
    loaded = loader()
    cache.set(base_url=base_url, token=token, catalog=catalog, value=loaded)
    return loaded
