from dataclasses import dataclass
import logging

from nerm.config import Settings
from nerm.url_utils import normalize_base_url

logger = logging.getLogger("nerm.auth")


AUTH_HEADERS = (
    "X-NERM-Authorization",
    "X-Amzn-Bedrock-AgentCore-Runtime-Custom-NERM-Authorization",
)
URL_HEADERS = (
    "X-NERM-URL",
    "X-Amzn-Bedrock-AgentCore-Runtime-Custom-NERM-URL",
)


@dataclass
class NermAuthContext:
    base_url: str
    bearer_token: str


def _redact_header_value(header_name: str, value: object) -> str:
    text = str(value).strip()
    if not text:
        return ""
    lower_name = header_name.lower()
    if "authorization" in lower_name or "token" in lower_name or "secret" in lower_name:
        return "<redacted>"
    return text


def resolve_auth(headers: dict[str, str], settings: Settings) -> NermAuthContext:
    normalized_headers = {str(key).lower(): value for key, value in headers.items()}

    observed_headers = {
        str(key): _redact_header_value(str(key), value)
        for key, value in sorted(headers.items(), key=lambda item: str(item[0]).lower())
        if "nerm" in str(key).lower()
    }
    log_level = logging.INFO if settings.nerm_verbose_trace else logging.DEBUG
    logger.log(log_level, "incoming_nerm_headers=%s", observed_headers)

    token = ""
    base_url = ""
    for key in AUTH_HEADERS:
        value = str(normalized_headers.get(key.lower(), "")).strip()
        if value:
            token = value
            break
    for key in URL_HEADERS:
        value = str(normalized_headers.get(key.lower(), "")).strip()
        if value:
            base_url = value
            break
    if not token:
        token = settings.nerm_bearer_token.strip()
    if not base_url:
        base_url = settings.nerm_base_url.strip()
    if base_url:
        base_url = normalize_base_url(base_url, settings.nerm_api_base_path)
    return NermAuthContext(base_url=base_url, bearer_token=token)
