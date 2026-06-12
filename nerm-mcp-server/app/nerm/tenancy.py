import hashlib


def tenant_partition_key(base_url: str, bearer_token: str) -> str:
    normalized = f"{base_url.strip().lower()}::{bearer_token.strip()}"
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
