import json as pyjson
import logging
import time
from typing import Any

import httpx

from nerm.client.retry import retry_sleep, should_retry
from nerm.config import get_settings
from nerm.errors import NermApiError


class NermHttpClient:
    def __init__(self, base_url: str, bearer_token: str) -> None:
        settings = get_settings()
        self.base_url = base_url.rstrip("/")
        self._headers = {"Authorization": bearer_token}
        self._client = httpx.Client(base_url=self.base_url, headers=self._headers)
        self._logger = logging.getLogger("nerm.http")
        self._debug_log_bodies = settings.nerm_debug_log_bodies
        self._trace_max_bytes = max(128, settings.nerm_trace_max_bytes)
        self._logger.info("tenant_connection base_url=%s", self.base_url)

    def _truncate(self, text: str) -> str:
        if len(text) <= self._trace_max_bytes:
            return text
        return text[: self._trace_max_bytes] + "...<truncated>"

    def _body_preview(self, payload: Any) -> str:
        if not self._debug_log_bodies or payload is None:
            return ""
        try:
            raw = pyjson.dumps(payload, default=str)
        except Exception:  # noqa: BLE001
            raw = str(payload)
        return self._truncate(raw)

    def _redacted_headers(self) -> dict[str, str]:
        redacted: dict[str, str] = {}
        for key, value in self._headers.items():
            if key.lower() == "authorization":
                redacted[key] = "<redacted>"
            else:
                redacted[key] = value
        return redacted

    def _request_url(self, path: str) -> str:
        return str(httpx.URL(self.base_url).join(path))

    def request(
        self,
        method: str,
        path: str,
        timeout: float = 15.0,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        for attempt in range(4):
            start = time.perf_counter()
            try:
                self._logger.info(
                    "request method=%s path=%s url=%s attempt=%s timeout=%s headers=%s params=%s req_body=%s",
                    method,
                    path,
                    self._request_url(path),
                    attempt + 1,
                    timeout,
                    self._redacted_headers(),
                    params,
                    self._body_preview(json),
                )
                response = self._client.request(method, path, timeout=timeout, json=json, params=params)
            except httpx.RequestError as exc:
                elapsed_ms = int((time.perf_counter() - start) * 1000)
                self._logger.warning(
                    "request_error method=%s path=%s attempt=%s elapsed_ms=%s error=%s",
                    method,
                    path,
                    attempt + 1,
                    elapsed_ms,
                    str(exc),
                )
                if attempt < 3:
                    retry_sleep(attempt)
                    continue
                raise NermApiError(status=502, body=f"transport error: {exc}") from exc
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            self._logger.info(
                "response method=%s path=%s attempt=%s status=%s elapsed_ms=%s",
                method,
                path,
                attempt + 1,
                response.status_code,
                elapsed_ms,
            )
            if response.status_code < 400:
                if not response.text.strip():
                    return {}
                try:
                    data = response.json()
                except ValueError as exc:
                    raise NermApiError(status=502, body=f"invalid JSON response: {exc}") from exc
                if self._debug_log_bodies:
                    self._logger.debug(
                        "response_body method=%s path=%s body=%s",
                        method,
                        path,
                        self._truncate(response.text),
                    )
                if isinstance(data, dict):
                    return data
                return {"items": data}
            if attempt < 3 and should_retry(response.status_code):
                retry_sleep(attempt)
                continue
            raise NermApiError(status=response.status_code, body=response.text)
        raise NermApiError(status=500, body="retry loop exhausted")
