import json
import os
import ast
import base64
import asyncio

from strands import Agent
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from model.load import load_model
from mcp_client.client import get_streamable_http_mcp_client

app = BedrockAgentCoreApp()
log = app.logger

_agent = None
ENABLE_IMAGE_MARKDOWN_FALLBACK = os.getenv("MCP_IMAGE_MARKDOWN_FALLBACK", "0") == "1"
IMAGE_OUTPUT_MODE = os.getenv("IMAGE_OUTPUT_MODE", "event").strip().lower()
MCP_RECOVERY_RETRIES = max(0, int(os.getenv("MCP_RECOVERY_RETRIES", "1")))
MCP_RECOVERY_BACKOFF_SECONDS = max(0.1, float(os.getenv("MCP_RECOVERY_BACKOFF_SECONDS", "1")))


def _try_parse_json(text: str):
    try:
        return json.loads(text)
    except (TypeError, json.JSONDecodeError):
        return None


def _first_text_block(content_blocks) -> str | None:
    if not isinstance(content_blocks, list):
        return None
    for block in content_blocks:
        if isinstance(block, dict) and block.get("type") == "text":
            text = block.get("text")
            if isinstance(text, str) and text.strip():
                return text
    return None


def _process_mcp_result(data):
    """Normalize MCP tool result handling while preserving all fields."""
    if not isinstance(data, dict):
        return data

    # Pass-through for non-MCP payloads.
    if "isError" not in data and "content" not in data and "structuredContent" not in data:
        return data

    result = dict(data)
    is_error = bool(result.get("isError"))
    content = result.get("content")

    if is_error:
        # Parse first text block JSON and surface concise error details.
        first_text = _first_text_block(content)
        parsed = _try_parse_json(first_text) if first_text else None
        if isinstance(parsed, dict):
            result["mcpError"] = {
                "error": parsed.get("error"),
                "message": parsed.get("message"),
            }
        return result

    # Preserve structuredContent as canonical machine-readable metadata.
    if "structuredContent" in result and isinstance(result["structuredContent"], dict):
        sc = result["structuredContent"]
        result["mcpMeta"] = {
            "chart_type": sc.get("chart_type"),
            "series_count": sc.get("series_count"),
            "png_bytes": sc.get("png_bytes"),
            "size_warning": sc.get("size_warning"),
        }

    # Process content blocks but preserve unknown block types/fields.
    if isinstance(content, list):
        processed_blocks = []
        for block in content:
            if not isinstance(block, dict):
                processed_blocks.append(block)
                continue

            block_type = block.get("type")
            if block_type == "text":
                text = block.get("text")
                parsed = _try_parse_json(text) if isinstance(text, str) else None
                if isinstance(parsed, dict):
                    block = {**block, "parsed": parsed}
            elif block_type == "image":
                # Prefer native MCP image blocks; optional markdown fallback via env flag.
                if ENABLE_IMAGE_MARKDOWN_FALLBACK:
                    mime_type = block.get("mimeType", "image/png")
                    image_data = block.get("data", "")
                    block = {
                        **block,
                        "fallbackMarkdown": f"![chart](data:{mime_type};base64,{image_data})",
                    }

            processed_blocks.append(block)
        result["content"] = processed_blocks

    return result


def _strip_nonserializable_event_fields(value):
    """Drop known runtime-only objects while preserving event structure."""
    if isinstance(value, dict):
        cleaned = {}
        for k, v in value.items():
            if k == "agent":
                continue
            cleaned[k] = _strip_nonserializable_event_fields(v)
        return cleaned
    if isinstance(value, list):
        return [_strip_nonserializable_event_fields(item) for item in value]
    return value


def _markdown_image_chunks(data) -> list[str]:
    """Create markdown image chunks from MCP image blocks for text-only clients."""
    if not isinstance(data, dict):
        return []
    content = data.get("content")
    if not isinstance(content, list):
        return []

    def _to_base64_payload(raw):
        if isinstance(raw, (bytes, bytearray)):
            return base64.b64encode(bytes(raw)).decode("ascii")
        if not isinstance(raw, str) or not raw:
            return None
        raw = raw.strip()
        if not raw:
            return None
        # Already base64-like payload
        if not raw.startswith("b'") and not raw.startswith('b"'):
            # Best-effort safety: if this does not look like base64,
            # treat it as raw string data and base64-encode it.
            if any(ch not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=\n\r" for ch in raw):
                return base64.b64encode(raw.encode("utf-8")).decode("ascii")
            return raw
        # Python bytes literal string from MCP payload preview:
        # e.g. "b'\\x89PNG...'"
        try:
            literal = ast.literal_eval(raw)
            if isinstance(literal, (bytes, bytearray)):
                return base64.b64encode(bytes(literal)).decode("ascii")
        except (SyntaxError, ValueError):
            # Fallback parser for malformed bytes-literal strings.
            inner = raw[2:-1] if len(raw) >= 3 else ""
            try:
                decoded = inner.encode("utf-8").decode("unicode_escape").encode("latin1")
                return base64.b64encode(decoded).decode("ascii")
            except Exception:
                return None
        return None

    def _find_nested_value(value, keys: tuple[str, ...]):
        if isinstance(value, dict):
            for key in keys:
                candidate = value.get(key)
                if candidate not in (None, ""):
                    return candidate
            for nested in value.values():
                found = _find_nested_value(nested, keys)
                if found not in (None, ""):
                    return found
        elif isinstance(value, list):
            for nested in value:
                found = _find_nested_value(nested, keys)
                if found not in (None, ""):
                    return found
        return None

    chunks: list[str] = []
    for block in content:
        if not isinstance(block, dict):
            continue

        # Support both MCP block shapes:
        # 1) {"type":"image","mimeType":"...","data":"..."}
        # 2) {"image":{"mimeType":"...","data":"..."}}
        image_payload = None
        if block.get("type") == "image":
            image_payload = block
        elif isinstance(block.get("image"), dict):
            image_payload = block.get("image")

        if not isinstance(image_payload, dict):
            continue

        mime_type = image_payload.get("mimeType") or image_payload.get("media_type")
        image_data = image_payload.get("data")

        # Some MCP servers return image bytes in nested source objects.
        if not isinstance(image_data, str):
            source = image_payload.get("source")
            if isinstance(source, dict):
                image_data = source.get("data") or source.get("bytes")
                mime_type = mime_type or source.get("mimeType") or source.get("media_type")
            image_format = image_payload.get("format") or (source.get("format") if isinstance(source, dict) else None)
            if not mime_type and isinstance(image_format, str):
                mime_type = f"image/{image_format.lower()}"

        # Some responses put payload keys directly on the outer block.
        if not isinstance(image_data, str):
            image_data = block.get("data")
        if not isinstance(mime_type, str):
            mime_type = block.get("mimeType") or block.get("media_type")

        # Last-resort recursive lookup for providers with deeply nested image payloads.
        if image_data in (None, ""):
            image_data = _find_nested_value(image_payload, ("bytes", "data", "base64"))
        if not isinstance(mime_type, str):
            mime_type = _find_nested_value(image_payload, ("mimeType", "media_type"))
        if not isinstance(mime_type, str):
            fmt = _find_nested_value(image_payload, ("format",))
            if isinstance(fmt, str) and fmt:
                mime_type = f"image/{fmt.lower()}"

        encoded = _to_base64_payload(image_data)
        if isinstance(mime_type, str) and isinstance(encoded, str) and encoded:
            chunks.append(f"![chart](data:{mime_type};base64,{encoded})")
        else:
            log.info(
                "Skipping markdown image block mime_type=%s image_data_type=%s encoded=%s block_keys=%s",
                mime_type,
                type(image_data).__name__,
                bool(encoded),
                sorted(block.keys()),
            )
    return chunks


def _text_chunks_from_mcp_content(data) -> list[str]:
    """Extract readable text from MCP content blocks."""
    if not isinstance(data, dict):
        return []
    content = data.get("content")
    if not isinstance(content, list):
        return []

    chunks: list[str] = []
    for block in content:
        if not isinstance(block, dict):
            continue

        # Support both MCP block shapes:
        # 1) {"type":"text","text":"..."}
        # 2) {"text":"..."} OR {"text":{"text":"..."}}
        text = None
        if block.get("type") == "text":
            text = block.get("text")
        elif isinstance(block.get("text"), str):
            text = block.get("text")
        elif isinstance(block.get("text"), dict):
            text = block.get("text", {}).get("text")

        if isinstance(text, str) and text.strip():
            chunks.append(text)
    return chunks


def _summarize_mcp_content_for_logs(data):
    """Return a compact, log-safe summary of MCP content blocks."""
    if not isinstance(data, dict):
        return None
    content = data.get("content")
    if not isinstance(content, list):
        return None

    summary = []
    for idx, block in enumerate(content):
        if not isinstance(block, dict):
            summary.append({"index": idx, "type": type(block).__name__})
            continue

        block_type = block.get("type")
        entry = {"index": idx, "type": block_type}

        if block_type == "text":
            text = block.get("text")
            if isinstance(text, str):
                entry["text_preview"] = text[:200]
                entry["text_len"] = len(text)
        elif block_type == "image":
            mime_type = block.get("mimeType")
            image_data = block.get("data")
            if isinstance(mime_type, str):
                entry["mimeType"] = mime_type
            if isinstance(image_data, str):
                entry["base64_len"] = len(image_data)
        else:
            # Keep unknown block shapes visible for debugging.
            entry["keys"] = sorted(block.keys())

        summary.append(entry)
    return summary


def _extract_mcp_payload(event: dict):
    """Best-effort extraction of MCP tool result payload from stream events."""
    candidates = []

    data = event.get("data")
    if isinstance(data, dict):
        candidates.append(data)

    for key in ("result", "tool_result", "current_tool_result"):
        value = event.get(key)
        if isinstance(value, dict):
            candidates.append(value)

    delta = event.get("delta")
    if isinstance(delta, dict):
        for key in ("toolResult", "tool_result", "result"):
            value = delta.get(key)
            if isinstance(value, dict):
                candidates.append(value)

    # Bedrock content-block style envelopes.
    for key in ("contentBlockStart", "contentBlockDelta", "contentBlockStop"):
        value = event.get(key)
        if isinstance(value, dict):
            candidates.append(value)
            for nested in value.values():
                if isinstance(nested, dict):
                    candidates.append(nested)

    # Message envelope can contain toolResult blocks with MCP payload.
    message = event.get("message")
    if isinstance(message, dict):
        content = message.get("content")
        if isinstance(content, list):
            for block in content:
                if not isinstance(block, dict):
                    continue
                tool_result = block.get("toolResult")
                if isinstance(tool_result, dict):
                    candidates.append(tool_result)
                    result_content = tool_result.get("content")
                    if isinstance(result_content, list):
                        for nested in result_content:
                            if isinstance(nested, dict):
                                candidates.append(nested)

    for candidate in candidates:
        if any(k in candidate for k in ("content", "structuredContent", "isError")):
            return candidate
    return None


def _unwrap_stream_event(event: dict) -> dict:
    """Bedrock/Strands can wrap the real event inside an 'event' field."""
    inner = event.get("event")
    if isinstance(inner, dict):
        return inner
    return event


def _compact_preview(value, max_len: int = 600) -> str:
    """JSON-ish preview for debug logs without flooding output."""
    try:
        text = json.dumps(value, default=str)
    except Exception:
        text = str(value)
    if len(text) > max_len:
        return text[:max_len] + "...(truncated)"
    return text


def _is_connection_error(exc: Exception) -> bool:
    """Heuristic matcher for recoverable MCP connection failures."""
    name = type(exc).__name__.lower()
    text = f"{name}: {str(exc).lower()}"
    markers = (
        "connect",
        "connection",
        "reset by peer",
        "broken pipe",
        "eof",
        "timeout",
        "temporarily unavailable",
        "service unavailable",
        "refused",
        "session terminated",
        "404 not found",
        "mcp",
    )
    return any(marker in text for marker in markers)


def _mcp_error_text(payload: dict) -> str:
    """Best-effort extraction of human-readable MCP error text."""
    content = payload.get("content")
    if not isinstance(content, list):
        return ""

    chunks: list[str] = []
    for block in content:
        if not isinstance(block, dict):
            continue
        text = block.get("text")
        if isinstance(text, str):
            chunks.append(text)
    return " ".join(chunks).strip()


def _is_recoverable_mcp_payload_error(payload: dict) -> bool:
    """
    Detect MCP payload errors that indicate stale/terminated sessions and
    should trigger client/agent re-initialization.
    """
    if not isinstance(payload, dict):
        return False

    status = str(payload.get("status", "")).lower()
    is_error = bool(payload.get("isError")) or status == "error"
    if not is_error:
        return False

    text = _mcp_error_text(payload).lower()
    if not text:
        return False

    recoverable_markers = (
        "session terminated",
        "session expired",
        "connection reset",
        "broken pipe",
        "eof",
        "temporarily unavailable",
        "service unavailable",
        "404 not found",
    )
    return any(marker in text for marker in recoverable_markers)


def _build_tools():
    """Rebuild tools so MCP client is recreated after failures/restarts."""
    runtime_tools = []
    mcp_client = get_streamable_http_mcp_client()
    if mcp_client:
        runtime_tools.append(mcp_client)
    return runtime_tools


def _reset_agent():
    global _agent
    _agent = None

def get_or_create_agent():
    global _agent
    if _agent is None:
        _agent = Agent(
            model=load_model(),
            system_prompt="""
                You are a helpful assistant. Use tools when appropriate.
            """,
            tools=_build_tools()
        )
    return _agent


@app.entrypoint
async def invoke(payload, context):
    log.info("Invoking Agent.....")
    prompt = payload.get("prompt")

    async def _stream_once():
        agent = get_or_create_agent()
        stream = agent.stream_async(prompt)
        probe_remaining = 120

        async for event in stream:
            raw_event = _unwrap_stream_event(event) if isinstance(event, dict) else event

            if probe_remaining > 0:
                if isinstance(raw_event, str):
                    log.info("stream_probe kind=str len=%s preview=%s", len(raw_event), raw_event[:80])
                elif isinstance(raw_event, dict):
                    log.info(
                        "stream_probe kind=dict keys=%s type=%s",
                        sorted(raw_event.keys()),
                        raw_event.get("type"),
                    )
                    if "contentBlockDelta" in raw_event:
                        log.info(
                            "stream_probe contentBlockDelta=%s",
                            _compact_preview(raw_event.get("contentBlockDelta")),
                        )
                        cbd = raw_event.get("contentBlockDelta")
                        if isinstance(cbd, dict):
                            delta = cbd.get("delta")
                            if isinstance(delta, dict) and "text" not in delta:
                                log.info(
                                    "stream_probe non_text_delta=%s",
                                    _compact_preview(delta),
                                )
                    if "contentBlockStart" in raw_event:
                        log.info(
                            "stream_probe contentBlockStart=%s",
                            _compact_preview(raw_event.get("contentBlockStart")),
                        )
                    if "contentBlockStop" in raw_event:
                        log.info(
                            "stream_probe contentBlockStop=%s",
                            _compact_preview(raw_event.get("contentBlockStop")),
                        )
                    if {"agent", "data", "delta"}.issubset(set(raw_event.keys())):
                        log.info(
                            "stream_probe detailed data_type=%s delta_keys=%s data_preview=%s delta_preview=%s",
                            type(raw_event.get("data")).__name__,
                            sorted(raw_event.get("delta", {}).keys()) if isinstance(raw_event.get("delta"), dict) else [],
                            _compact_preview(raw_event.get("data")),
                            _compact_preview(raw_event.get("delta")),
                        )
                else:
                    log.info("stream_probe kind=%s", type(raw_event).__name__)
                probe_remaining -= 1

            # Never stream raw internal event objects to the chat client.
            if isinstance(raw_event, str):
                yield raw_event
                continue

            if not isinstance(raw_event, dict):
                continue

            event_type = raw_event.get("type")
            if event_type == "tool_use_stream":
                continue

            data = raw_event.get("data")
            mcp_payload = _extract_mcp_payload(raw_event)

            # Emit assistant token text, but do not short-circuit delta parsing.
            if isinstance(data, str):
                yield data

            raw_payload = mcp_payload if mcp_payload is not None else (data if data is not None else raw_event)
            processed_for_fallback = _process_mcp_result(
                _strip_nonserializable_event_fields(raw_payload)
            )

            # Some MCP failures arrive as tool-result payloads instead of raised exceptions.
            # Promote recoverable session/connection errors so the outer retry loop can re-init.
            if (
                isinstance(mcp_payload, dict)
                and _is_recoverable_mcp_payload_error(mcp_payload)
            ):
                error_text = _mcp_error_text(mcp_payload) or "unknown MCP session error"
                raise RuntimeError(f"Recoverable MCP payload error: {error_text}")

            if isinstance(processed_for_fallback, dict):
                content = processed_for_fallback.get("content")
                if isinstance(content, list):
                    block_types = [
                        block.get("type")
                        for block in content
                        if isinstance(block, dict) and "type" in block
                    ]
                    if block_types:
                        log.info(
                            "MCP content block types=%s isError=%s hasStructuredContent=%s",
                            block_types,
                            bool(processed_for_fallback.get("isError")),
                            "structuredContent" in processed_for_fallback,
                        )
                elif isinstance(raw_event.get("delta"), dict):
                    log.info(
                        "delta_event keys=%s delta_keys=%s has_mcp_payload=%s",
                        sorted(raw_event.keys()),
                        sorted(raw_event.get("delta", {}).keys()) if isinstance(raw_event.get("delta"), dict) else [],
                        mcp_payload is not None,
                    )

                # Avoid duplicating already-streamed assistant token text from data.
                if not isinstance(data, str):
                    for text_chunk in _text_chunks_from_mcp_content(processed_for_fallback):
                        yield text_chunk

                summary = _summarize_mcp_content_for_logs(processed_for_fallback)
                if summary is not None:
                    log.info("MCP content summary=%s", summary)
                    log.info("MCP payload preview=%s", _compact_preview(processed_for_fallback, 1200))

            # Extra visibility for nested message events that carry tool results.
            if isinstance(raw_event.get("message"), dict):
                log.info(
                    "message_event keys=%s has_mcp_payload=%s",
                    sorted(raw_event.get("message", {}).keys()),
                    mcp_payload is not None,
                )

            # Markdown fallback for chat clients that do not render native MCP image blocks.
            if IMAGE_OUTPUT_MODE in {"markdown", "event"}:
                image_chunks = _markdown_image_chunks(processed_for_fallback)
                if image_chunks:
                    log.info("Emitting %s markdown image chunk(s)", len(image_chunks))
                for image_markdown in image_chunks:
                    yield image_markdown

    for attempt in range(MCP_RECOVERY_RETRIES + 1):
        try:
            async for chunk in _stream_once():
                yield chunk
            return
        except Exception as exc:
            recoverable = _is_connection_error(exc)
            if attempt >= MCP_RECOVERY_RETRIES or not recoverable:
                log.exception(
                    "Agent stream failed (recoverable=%s, attempt=%s/%s)",
                    recoverable,
                    attempt + 1,
                    MCP_RECOVERY_RETRIES + 1,
                )
                raise

            delay = MCP_RECOVERY_BACKOFF_SECONDS * (2**attempt)
            log.warning(
                "Recoverable MCP/connection error detected. Resetting agent and retrying in %.2fs (attempt %s/%s): %s",
                delay,
                attempt + 1,
                MCP_RECOVERY_RETRIES + 1,
                exc,
            )
            _reset_agent()
            await asyncio.sleep(delay)


if __name__ == "__main__":
    app.run(port=8085, host="0.0.0.0")
