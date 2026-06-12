from collections.abc import Callable, Sequence

from nerm.cache import ReferenceCache
from nerm.client.http_client import NermHttpClient
from nerm.config import get_settings
from nerm.errors import NermApiError
from nerm.url_utils import normalize_base_url

DEFAULT_PAGE_SIZE = 200
CATALOG_PROFILE_TYPES = "profile_types"
CATALOG_ATTRIBUTES = "attributes"

_reference_cache: ReferenceCache | None = None


def get_reference_cache() -> ReferenceCache:
    global _reference_cache
    if _reference_cache is None:
        settings = get_settings()
        _reference_cache = ReferenceCache(ttl_seconds=settings.nerm_static_reference_cache_ttl_sec)
    return _reference_cache


def resolve_connection(
    nerm_base_url: str | None = None,
    nerm_bearer_token: str | None = None,
) -> tuple[str, str]:
    settings = get_settings()
    base_url_raw = (nerm_base_url or settings.nerm_base_url).strip()
    bearer_token = (nerm_bearer_token or settings.nerm_bearer_token).strip()
    if not base_url_raw or not bearer_token:
        raise ValueError("NERM base URL and bearer token are required.")
    base_url = normalize_base_url(base_url_raw, settings.nerm_api_base_path)
    return base_url, bearer_token


def _extract_items(payload: dict) -> list[dict]:
    return extract_list_records(payload)


def _list_key_from_path(path: str) -> str:
    return path.strip("/").split("/", 1)[0]


def extract_list_records(payload: dict, preferred_keys: Sequence[str] = ()) -> list[dict]:
    for key in [*preferred_keys, "items"]:
        if key not in payload:
            continue
        items = payload.get(key)
        if isinstance(items, list):
            return [item for item in items if isinstance(item, dict)]
    return []


def fetch_full_catalog(
    client: NermHttpClient,
    path: str,
    request_timeout_sec: float = 15.0,
) -> list[dict]:
    def _is_no_catalog_items_error(exc: NermApiError) -> bool:
        if exc.status not in {400, 404}:
            return False
        body = str(exc.body or "").lower()
        list_key = _list_key_from_path(path).replace("_", " ")
        relaxed_key = list_key.replace("ne ", "")
        return (
            f"no {list_key} found" in body
            or f"no {relaxed_key} found" in body
        )

    all_items: list[dict] = []
    offset = 0
    while True:
        try:
            payload = client.request(
                "GET",
                path,
                timeout=request_timeout_sec,
                params={"limit": DEFAULT_PAGE_SIZE, "offset": offset},
            )
        except NermApiError as exc:
            if _is_no_catalog_items_error(exc):
                break
            raise
        page_items = extract_list_records(payload, preferred_keys=(_list_key_from_path(path),))
        all_items.extend(page_items)
        if len(page_items) < DEFAULT_PAGE_SIZE:
            break
        offset += DEFAULT_PAGE_SIZE
    return all_items


def get_catalog_cached(
    catalog_name: str,
    path: str,
    nerm_base_url: str | None = None,
    nerm_bearer_token: str | None = None,
) -> list[dict]:
    base_url, bearer_token = resolve_connection(nerm_base_url=nerm_base_url, nerm_bearer_token=nerm_bearer_token)
    cache = get_reference_cache()
    cached = cache.get(base_url=base_url, token=bearer_token, catalog=catalog_name)
    if isinstance(cached, list):
        return cached
    client = NermHttpClient(base_url=base_url, bearer_token=bearer_token)
    loaded = fetch_full_catalog(client=client, path=path)
    cache.set(base_url=base_url, token=bearer_token, catalog=catalog_name, value=loaded)
    return loaded


def execute_with_nerm_error_json(run: Callable[[], dict]) -> dict:
    try:
        return run()
    except NermApiError as exc:
        return exc.as_error_json()
    except ValueError as exc:
        return {"error": "nerm_api_error", "status": 400, "body": str(exc)}
    except Exception as exc:  # noqa: BLE001
        return {"error": "nerm_api_error", "status": 500, "body": f"unexpected error: {exc}"}
