import os
import logging
from mcp.client.streamable_http import streamablehttp_client
from strands.tools.mcp.mcp_client import MCPClient

logger = logging.getLogger(__name__)

DEFAULT_MCP_ENDPOINT = "http://localhost:8080/mcp"


def _resolved_mcp_config() -> tuple[str, dict[str, str]]:
    endpoint = os.getenv("MCP_ENDPOINT", DEFAULT_MCP_ENDPOINT).strip()
    target_url = os.getenv("MCP_TARGET_URL", "").strip()
    authorization = os.getenv("MCP_AUTHORIZATION", "").strip()

    headers: dict[str, str] = {}
    if target_url:
        headers["X-NERM-URL"] = target_url
    if authorization:
        headers["X-NERM-Authorization"] = authorization

    # Never log token values; only endpoint + header keys.
    logger.info(
        "Resolved MCP config endpoint=%s header_keys=%s",
        endpoint,
        sorted(headers.keys()),
    )
    return endpoint, headers

def get_streamable_http_mcp_client() -> MCPClient:
    """Returns an MCP Client compatible with Strands"""
    endpoint, headers = _resolved_mcp_config()
    return MCPClient(lambda: streamablehttp_client(endpoint, headers=headers))
