# MCP Compatibility Profile Docs

This folder contains the shared compatibility contract for:
- `tool-nerm-mcp-server` (MCP server)
- `testAgent` (remote/orchestrator agent)
- `ChatClient` (UI client)

## File Ownership

- `v1.0.md`  
  - Owner: Platform Integration (cross-component owners)
  - Purpose: umbrella profile and normative baseline

- `tool-response-contract-v1.0.md`  
  - Primary owner: MCP Server team (`tool-nerm-mcp-server`)
  - Secondary reviewers: `testAgent` + `ChatClient`

- `streamable-http-transport-profile-v1.0.md`  
  - Primary owner: MCP Server team
  - Secondary reviewers: `testAgent` transport/client owners

- `multimodal-compat-guidance-v1.0.md`  
  - Primary owners: MCP Server + ChatClient teams
  - Secondary reviewers: `testAgent`

- `production-logging-profile-v1.0.md`  
  - Primary owner: MCP Server/Platform Ops
  - Secondary reviewers: Security/Compliance + `testAgent`

- `cross-client-release-gates-v1.0.md`  
  - Primary owner: QA/Release Engineering
  - Secondary reviewers: all three component teams

## Version Bump Process

### Patch/Clarification update (non-breaking)

- Keep same major/minor profile line (e.g., `v1.0` docs).
- Update wording/examples only; no behavior contract changes.
- Add changelog note in PR description.

### Minor update (backward-compatible behavior additions)

- Create new files with next minor version (e.g., `v1.1`).
- Keep prior version docs in place for consumers not yet upgraded.
- Document additive changes and migration notes.

### Major update (breaking changes)

- Create next major version docs (e.g., `v2.0`).
- Include explicit breaking-change section and cutover plan.
- Require sign-off from all three component owners before adoption.

## Required PR Checklist for Contract Changes

- [ ] Identify version type (patch/minor/major)
- [ ] Update relevant profile docs
- [ ] Add migration notes (if minor/major)
- [ ] Confirm release-gate test impacts
- [ ] Obtain reviewer sign-off from each component owner
