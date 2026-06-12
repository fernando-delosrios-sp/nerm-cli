# Tool Response Contract v1.0

Status: Published  
Applies to: MCP tools exposed by `tool-nerm-mcp-server`

## Objective

Standardize tool response semantics across all tools so clients can reliably interpret success/failure and multimodal payloads.

## Required Contract

- Tools MUST return MCP `CallToolResult`-compatible payloads.
- Success responses MUST set `isError: false`.
- Error responses MUST set `isError: true`.
- `content` MUST be an array of typed content blocks.

## Success Shape

- MUST include at least one `text` or non-text block.
- Text metadata SHOULD be JSON string in a `text` block for broad compatibility.
- `structuredContent` MAY be used for machine-readable payloads.

Example:

```json
{
  "content": [
    { "type": "text", "text": "{\"status\":\"success\",\"tool\":\"nerm_generate_chart\"}" }
  ],
  "isError": false
}
```

## Error Shape

- MUST include a `text` block with JSON error payload.
- Error JSON SHOULD include:
  - `status: "error"`
  - `error: <stable_code>`
  - `message: <human_message>`

Example:

```json
{
  "content": [
    {
      "type": "text",
      "text": "{\"status\":\"error\",\"error\":\"invalid_chart_spec\",\"message\":\"No plottable numeric series found.\"}"
    }
  ],
  "isError": true
}
```

## Compatibility Rules

- Clients MUST NOT infer success/failure from text alone when `isError` is present.
- Intermediaries MUST preserve `isError`, `content`, and `structuredContent` if present.
- Tools MUST NOT return custom non-serializable Python objects directly in wire payloads.
