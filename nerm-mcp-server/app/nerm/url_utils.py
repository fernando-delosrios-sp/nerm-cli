from urllib.parse import urlsplit, urlunsplit


def normalize_base_url(base_url: str, api_base_path: str) -> str:
    parsed = urlsplit(base_url)
    if parsed.scheme and parsed.netloc:
        if parsed.path and parsed.path != "/":
            return base_url.rstrip("/")
        normalized_path = "/" + api_base_path.strip("/")
        return urlunsplit((parsed.scheme, parsed.netloc, normalized_path, parsed.query, parsed.fragment)).rstrip("/")
    return base_url.rstrip("/")
