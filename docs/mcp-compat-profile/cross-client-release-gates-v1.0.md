# Cross-Client Interoperability Release Gates v1.0

Status: Published  
Purpose: Add release-gate verification beyond unit tests.

## Gate Scope

Validate interoperability across:
- MCP server (`tool-nerm-mcp-server`)
- Remote/orchestrator agent (`nermTestAgent`)
- UI consumer (`ChatClient`)

## Mandatory Release Gates

### Gate 1: Tool Error Semantics

- Verify success tool calls return `isError=false`.
- Verify failure tool calls return `isError=true`.
- Verify intermediaries preserve `isError` and do not flatten to plain text only.

### Gate 2: Multimodal Content Delivery

- Verify chart tool returns:
  - at least one `type:"text"` block
  - at least one `type:"image"` block
- Verify consumers render image or apply documented fallback.

### Gate 3: Stream Framing Robustness

- Validate SSE parser with:
  - multi-line `data:` frames
  - named `event:` frames
  - reconnect/replay scenarios

### Gate 4: Session Lifecycle

- Validate expected streamable-http behavior:
  - init/start session
  - normal tool calls
  - invalid session recovery
  - session termination

### Gate 5: Logging Safety

- Validate logs include tool name and args/output summary.
- Validate sensitive keys are redacted.
- Validate image data is masked (`<base64_image len=...>`).

## Exit Criteria

- All mandatory gates pass in CI or pre-release validation run.
- Any waived gate requires documented risk acceptance.
