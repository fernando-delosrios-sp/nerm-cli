# Multimodal Compatibility Guidance v1.0

Status: Published  
Scope: text+image interoperability across MCP server, remote agents, and UI clients.

## Primary Policy

- Producers SHOULD emit native MCP content blocks:
  - `{"type":"text","text":"..."}`
  - `{"type":"image","mimeType":"image/png","data":"<base64>"}`
- Consumers SHOULD render native `image` blocks directly.

## Markdown Fallback Policy

- Markdown data URL fallback SHOULD be used only when explicitly requested by downstream client capability.
- Fallback example:
  - `![NERM chart](data:image/png;base64,...)`
- Avoid duplicate large payloads unless compatibility requires it.

## When to Request Markdown Fallback

- Request markdown fallback if the downstream client:
  - cannot render MCP `image` content blocks
  - only supports markdown/text rendering
  - strips non-text content blocks in intermediate hops

## Size and Limits

- Producers SHOULD apply adaptive controls:
  - downsampling
  - dpi reduction
  - metadata warnings (`png_bytes`, target size)
- If payload remains large, prefer warning + best-effort response over hard crash.

## Minimum Consumer Behavior

- MUST support `text`.
- SHOULD support `image`.
- MUST provide explicit fallback behavior for unsupported block types.
