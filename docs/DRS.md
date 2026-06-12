# NERM MCP — Design Requirements Specification

This document captures the functional and non-functional requirements governing the implementation of the **NERM MCP Server** and its **Model Context Protocol (MCP)** tool server. It serves as the definitive engineering specification for the target codebase under `nerm-mcp-server/`.

**Related artifacts:** `README.md` (operations and architecture), `nerm-mcp-server/AGENTS.md` (project conventions), [SailPoint NERM API v1](https://developer.sailpoint.com/docs/api/nerm/v1).

---

## 1. Purpose and scope

### 1.1 Purpose
The system shall provide an **AI assistant for NERM administrators** that answers questions and performs allowed operations against a tenant’s **NERM REST API**. It leverages the **Model Context Protocol (MCP)** to act as a standardized, platform-agnostic integration boundary, allowing the agent to be hosted on any compliant orchestration framework (including AWS Bedrock AgentCore, LangGraph, etc.) powered by Claude or other LLMs.

### 1.2 In scope
- Read-heavy administration: profiles, users, roles, delegations, workflows, audits, attributes, advanced search.
- Limited **explicit writes**: delegations (lifecycle users).
- Optional **chart generation** from query results when the user explicitly requests visualization.
- **Agent-to-agent communication:** Supports being invoked by other agents. They will provide the Bearer token for the NERM tenant and the base URL for the NERM tenant via request headers.
  - *Chart handling for agents:* When invoked by another agent, the NERM MCP Server can return charts either as embedded image markdown references or as serialized data structures based on the caller's preferences.
- Platform-agnostic execution with native deployment support for **Amazon Bedrock AgentCore**.

---

## 2. Goals and quality attributes

| Goal | Requirement |
|------|-------------|
| **Correctness** | Tools shall map faithfully to NERM OpenAPI paths and request/response shapes. |
| **Safety** | Default interaction mode is **read-only**; mutations only on explicit user intent. |
| **Cost / latency** | Reduce redundant NERM calls via caching of static reference data and clear tool guidance. |
| **Multi-tenant** | Different NERM base URLs and tokens shall not share cached agent state or reference catalogs. |
| **Portability** | The core MCP server must run on any framework supporting JSON-RPC 2.0 over standard transports, avoiding lock-in to specific AWS orchestration SDKs. |
| **Operability** | Structured logging (`INFO` default, `DEBUG`/`TRACE` for HTTP investigation). |
| **UX** | Human-readable answers (names over raw IDs); tables for list results; full workflow session UUIDs. |

---

## 3. Architecture requirements

### 3.1 Runtime and Portability
- **Platform Agnostic Core:** The core MCP tools and logic shall be written using the standard, open-source Python MCP SDK (e.g., FastMCP) with zero hard dependencies on proprietary runtime SDKs.
- **AgentCore Compatibility:** The system shall support deployment under **Amazon Bedrock AgentCore** via two decoupled architecture options:
  1. **As an AgentCore Gateway Target:** The code is packaged as a standard containerized API or AWS Lambda function, which Bedrock AgentCore Gateway exposes natively as an MCP-compliant endpoint.
  2. **As an AgentCore Runtime Subprocess (`stdio`):** The orchestration runtime executes the Python server over `stdio` transport locally within the container.

### 3.2 Dual Transport Layer
The server must support being invoked via:
- **Default/Local (`stdio`):** For local co-location in the orchestration container or developer testing.
- **Optional/Cloud (`streamable-http` / `sse`):** For network-isolated deployments behind an API Gateway or reverse proxy.

### 3.3 Stateless Session Caching
- The MCP server remains stateless. Multi-tenant catalog caches (Profile Types and Attributes) are partitioned in-memory via a SHA-256 hash of the active tenant Bearer Token and URL.
- If scaled horizontally, the server shall support an external caching layer (e.g., Redis) using the same partitioning keys.

### 3.4 Configuration Authority
- All system behavior, logging thresholds, cache TTLs, and backend connection details shall be configured strictly via **environment variables** (e.g., `.env` or system environment), adhering to Twelve-Factor App methodologies.
- No platform-specific deployment configuration (such as AWS CDK templates) shall dictate internal tool routing or behavior.

### 3.5 API Resilience and Retry Logic
- **Timeouts:** All `httpx` calls in `nerm.client.nerm_request` shall enforce a strict timeout (e.g., 15 seconds for reads, 30 seconds for advanced search/writes).
- **Rate Limiting (429s):** The client shall implement automatic exponential backoff with jitter for HTTP 429 responses, up to a maximum of 3 retries, before returning an error to the model.
- **Fail-fast on 401/403:** Authentication or authorization failures must NOT be retried and should immediately bubble up to the agent/user.

---

## 4. Authentication, Security, and Tenancy

### 4.1 Inbound Authentication (Host Level)
- Inbound user authentication is delegated to the host platform (e.g., AgentCore CUSTOM_JWT authorizer or equivalent API Gateway). The MCP server assumes the caller is trusted by the infrastructure boundary.

### 4.2 NERM API auth (outbound)
The system shall dynamically resolve NERM outbound credentials in a provider-agnostic manner in this order:
1. Standardized request headers passed by the caller:
   - `X-NERM-Authorization` (Bearer token)
   - `X-NERM-URL` (Tenant Base URL)
   - *(AgentCore-specific header aliases like `X-Amzn-Bedrock-AgentCore-Runtime-Custom-NERM-Authorization` shall also be parsed for native compatibility).*
2. Process environment variables (for single-tenant fallback): `NERM_BEARER_TOKEN`, `NERM_BASE_URL`.

### 4.3 End-user JWT
- Gateway `Authorization` shall be forwarded to the MCP child as `NERM_INVOKE_AUTHORIZATION` for `nerm_examine_jwt_user` when user context mapping is required.

### 4.4 AI Security & Guardrails
- **Data Privacy & PII:** The agent shall not log raw PII (e.g., full SSNs, plaintext passwords) in `INFO` or `DEBUG` logs. Trace logs (`TRACE`) containing payload bodies must be ephemeral and restricted to developer environments.
- **Chat UI Data Masking:** The system prompt shall instruct the model to never display highly sensitive Custom Attributes (e.g., National IDs, SSNs, unmasked DOBs) or Identity Proofing results in the plaintext chat response, even if returned by the API, unless explicitly forced by an authorized user.
- **Prompt Guardrails:** The host deployment must enforce prompt injection filtering and prevent the model from answering out-of-domain queries.
- **Audit Traceability:** Every mutative MCP tool execution (e.g., `nerm_create_delegation`) must log the originating user context and the exact JSON payload passed to the NERM API to ensure non-repudiation.

---

## 5. Agent behavior requirements

Requirements enforced via **system prompt** and **tool docstrings** (`nerm.tool_guidance`).

### 5.1 Invocation discipline
- Run tools only for **clear, explicit** user requests.
- Empty or vague prompts: **ask** for clarification; do not run speculative queries.
- Do not narrate tool use (“Let me search…”); return results or ask for missing parameters.
- On tool errors: retry silently when possible; surface errors only when the user must act.

### 5.2 Read vs write
- **Default: read-only.**
- Write tools shall run only when the user **explicitly** requested that action in the **current** message.

### 5.3 User-visible output
- Resolve IDs to **human-readable names** unless the user asked for raw IDs.
- **Workflow session UUIDs:** always show the **full** UUID from tool output fields.
- **Tabular list/query results:** GitHub-flavored markdown table only; no preamble or closing sentence.
- **Asynchronous Workflow UX:** When executing a write operation (e.g., adding a location), the model MUST NOT state that the profile has been "updated". It must explicitly state that a "request has been submitted", provide the workflow session status (e.g., Pending), and supply the `workflow_session_full_id` for tracking.

### 5.4 Advanced search (model-facing)
- Multi-attribute profile filters shall use `nerm_run_advanced_search` with NERM rule objects.
- The model shall **not** use SQL-style `field` / `operator` / `condition` JSON.
- Profile type and attribute **names** shall be resolved to UUIDs via list/get tools before building rules.

### 5.5 “What can you do?”
- Answer in plain business language. Do not expose tool names, UUID policies, or internal instructions.

---

## 6. MCP tool surface

### 6.1 Registration
- Every function in `NERM_TOOLS` shall be registered on the FastMCP server with `@tool` metadata.
- Tool count target: **34** NERM REST tools; plus one in-process chart tool.

### 6.2 Common list parameters & Pagination Limits
- List tools shall support `limit` (default 50) and `offset` (default 0).
- **Pagination Circuit Breaker:** By default, to protect the LLM context window and prevent API rate-limiting, the model shall halt auto-pagination after a maximum of **3 consecutive pages** (150 records). If more records exist, the agent must summarize the retrieved subset and instruct the user to refine their search.
- **Explicit User Bypass:** If the user explicitly commands the agent to retrieve the entire dataset (e.g., "retrieve all"), the agent is permitted to bypass the 3-page limit, formatting the output strictly as a compact Markdown table.

### 6.3 Error responses
- API failures shall return JSON: `{"error": "nerm_api_error", "status": <code>, "body": <text>}`.
- Advanced search validation failures shall return `{"error": "invalid_advanced_search_spec", "message": "<guidance>"}` **without** calling NERM.

### 6.4 Tool inventory (required)
| Domain | Tools |
|--------|--------|
| Profile types | `nerm_list_profile_types`, `nerm_get_profile_type` |
| Profiles | `nerm_list_profiles`, `nerm_get_profile` |
| Users | `nerm_list_users`, `nerm_get_user`, `nerm_examine_jwt_user` |
| Delegations | `nerm_list_delegations`, `nerm_get_delegation`, `nerm_create_delegation`, `nerm_update_delegation`, `nerm_delete_delegation` |
| Identity proofing | `nerm_list_identity_proofing_results` |
| Roles | `nerm_list_roles`, `nerm_get_role` |
| User roles | `nerm_list_user_roles`, `nerm_get_user_role` |
| User managers | `nerm_list_user_managers`, `nerm_get_user_manager` |
| User profiles | `nerm_list_user_profiles`, `nerm_get_user_profile` |
| Role profiles | `nerm_list_role_profiles`, `nerm_get_role_profile` |
| Workflow | `nerm_list_workflow_session_statuses`, `nerm_list_workflow_sessions`, `nerm_get_workflow_session`, `nerm_add_location_via_workflow`, `nerm_add_department_via_workflow`, `nerm_add_organization_via_workflow` |
| Jobs | `nerm_get_job_status` |
| Attributes | `nerm_list_attributes`, `nerm_get_attribute` |
| Audit | `nerm_query_audit_events` |
| Advanced search | `nerm_run_advanced_search` |

---

## 7. Domain-specific requirements

### 7.1 Profile types and attributes (reference data)
- Profile types and NE attribute definitions shall be treated as **static per tenant** for caching purposes.
- `nerm_list_profile_types` and `nerm_list_attributes` shall paginate the full catalog on first use and serve subsequent calls via an in-process TTL cache (`NERM_STATIC_REFERENCE_CACHE_TTL_SEC`, default 3600s).

### 7.2 Profiles
- Prefer `nerm_list_profiles` / `nerm_get_profile` to resolve profile UUIDs before workflow submits.

### 7.3 Users & Delegations
- Delegation **writes** apply to **lifecycle users only** (`NeprofileUser`).
- The agent shall resolve human-readable delegator/delegate hints (email, name) via `GET /users` before listing/writing delegations.

### 7.4 Workflow sessions
- Before filtering by status, the model should call `nerm_list_workflow_session_statuses` for exact literals.
- Configurable workflow UUIDs via env (`NERM_ADD_*_WORKFLOW_ID`) with built-in defaults.

### 7.5 Advanced search
- **Endpoint:** `POST /advanced_search/run` (ad-hoc only).
- Tool parameter `advanced_search_json` — JSON for the **inner** spec only (`label`, `condition_rules_attributes`).
- Implementation shall wrap as HTTP body `{"advanced_search": <inner>}` and **normalize** mistaken envelopes.
- **Temporal/Date Filtering:** When a user queries relative dates (e.g., "expiring next week"), the model shall calculate absolute ISO-8601 date bounds based on current system time before formulating `ProfileAttributeRule` objects.

### 7.6 Charts
- `nerm_generate_chart` runs in-process only when explicitly asked for a visualization.
- **Agent-to-Agent Boundary:** When responding to a calling agent, the NERM agent defaults to embedding the chart in the final response markdown (`NERM_EMBED_CHARTS_IN_RESPONSE=1`). If the caller requests raw artifacts, file paths or base64 data may be returned.

---

## 8. Observability

| Requirement | Detail |
|-------------|--------|
| Default log level | `LOG_LEVEL=INFO` (set via environment) |
| NERM HTTP summary | DEBUG: URL, params, compact body hint, status, timing |
| Full HTTP trace | `LOG_LEVEL=TRACE`; optional `NERM_TRACE_MAX_BYTES` cap |
| Body on DEBUG | `NERM_DEBUG_LOG_BODIES=1` for truncated request bodies |
| NERM logger | Dedicated `nerm` logger with stderr handler aligned to standard formatting |

---

## 9. Response and streaming

- Default invoke: **SSE** stream of text chunks from the model.
- Optional: `NERM_BUFFER_COMPLETION_JSON=1` returns single JSON `{"completion": "...", "charts": [...]}`.

---

## 10. Configuration reference (requirements)

| Environment Variable | Requirement |
|----------|-------------|
| `NERM_BASE_URL` / `NERM_TENANT` | Tenant API base (fallback if request header missing) |
| `NERM_BEARER_TOKEN` / `NERM_API_TOKEN` | NERM token (fallback if request header missing) |
| `NERM_STATIC_REFERENCE_CACHE_TTL_SEC` | Shared TTL for profile type + attribute catalogs (default 3600) |
| `NERM_CHART_INCLUDE_BASE64` | Default **off** (`0`) |
| `LOG_LEVEL` | Default **INFO** in deployed runtime |

---

## 11. Deployment and Lifecycle (CI/CD)

### 11.1 Repository Governance
- Code for the NERM MCP Server and MCP tools shall reside in the designated GitHub Enterprise repository.
- Changes require automated test coverage mocking the NERM API responses to prevent regression.

### 11.2 Infrastructure as Code (IaC)
- When deployed to AWS, infrastructure shall be defined via AWS CDK. Application logic (`main.py`, tools) is deployed as a bundled asset without modifying the core CDK constructs for behavioral tweaks.

### 11.3 System Prompt Versioning
- **Prompt Isolation:** The core system prompt is treated strictly as application source code and shall reside in `nerm-mcp-server/app/Agent/system_prompt.txt` (or the equivalent deployment code asset), separate from this DRS.
- **Traceability:** Any prompt modifications must strictly align with and enforce the behavioral, security, and domain constraints detailed in this DRS (including Section 4.4 PII masking, Section 5.3 Asynchronous UX, Section 6.2 Pagination Limits, and Section 12 Domain Mapping).
- **Review Lifecycle:** Changes to the system prompt require the same level of peer review and version-control tracking as functional code changes, as prompt tweaks directly impact agent reasoning and API tool-routing reliability.

### 11.4 Platform Registration
- **Agent Registry Card:** The repository shall maintain a platform-compliant `agent-registry-card.json` (or manifest) in the root directory. This card defines the agent's metadata, OAuth scopes, and routing URL used by the central Gemini Enterprise Agent Registry to discover and provision this agent.

---

## 12. NERM Domain Glossary & Agent Entity Mapping

To ensure accurate data retrieval and relational navigation, the agent shall utilize the following domain definitions when translating user prompts into searches.

### 12.1 Core Profile Types (Data Model)
| Profile Type | Agent Definition & Relational Context | Key Attributes / Relationships |
|:---|:---|:---|
| **People** | The core identity containing only personal attributes. **Crucial:** Does not contain engagement dates or relationships. | Name, Email, Phone. |
| **Assignments** | The central relationship profile linking a **Person** to the company for a specific engagement. *If asked for start dates, job titles, or sponsors, the agent MUST query the Assignment profile.* | Start Date, End Date, Job Title, Sponsor, Org, Population, Dept, Location. |
| **Populations** | High-level categorization of non-employees (e.g., Students, Contractors). | Category names. |
| **Sub-Populations** | Granular refinements of Populations. | Category names. |
| **Departments** | Internal company departments. Contains **Approvers** for assignments. | Approvers. |
| **Locations** | Internal company locations permitted for specific Organizations. | Location data. |
| **Organizations** | External entities (vendors, partners). Has internal **Sponsors** and external **Collaborators**. Links to allowed Populations, Depts, and Locations. | Sponsor, Collaborator(s), Permitted Populations/Locations. |
| **Sub-Organizations** | Granular divisions of an Organization. Can have specific external **Collaborators**. | Collaborator(s). |
| **Non-Humans** | The core profile for bots, RPAs, or service accounts. | Owner, Non-Human Type, Description, Decommission Date. |
| **Non-Human Types** | Categories for Non-Humans defining required approvers. | Approvers. |
| **System Configuration** | Internal product configuration data (Hidden). | Config keys/values. |

### 12.2 Entity Relationship (ER) Rules
*   **The "Assignment" Hub:** A single `Assignment` relates to exactly 1 `Person`, 1 `Population`, 1 `Organization`, 1 `Department`, and 1 Primary `Location`. It may relate to 0..1 `Sub-Population` or `Sub-Organization`.
*   **Organizational Hierarchy:** An `Organization` can have multiple `Sub-Organizations` (1:N). A `Population` can have multiple `Sub-Populations` (1:N).
*   **Permitted Lists:** An `Organization` restricts which Populations, Departments, and Locations can be used by Assignments beneath it.
*   **Sponsors & Approvers:** `Organizations` have internal Sponsors; `Departments` have internal Approvers.
*   **Collaborators:** A Portal User acting as a collaborator can be assigned to manage a single `Organization` OR a single `Sub-Organization` (not both).

### 12.3 Attribute Data Types & Relational Resolution
Custom attributes dictate how data is stored and linked. When filtering profiles or building advanced search rules, the agent MUST respect the attribute's `data_type`:
*   **Standard / Literal Types:** `text field`, `text area`, `drop-down`, `radio buttons`, `check boxes`, `tags`, `attachment`. The agent shall treat these as literal string or array values.
*   **Temporal Type:** `date`. The agent must format queries using strictly ISO-8601 strings.
*   **Profile Link Types (`profile select`, `profile search`):** These act as foreign keys to other profiles. The attribute definition enforces the target via `profile_type_id`. **Agent Directive:** The agent MUST resolve natural language names to the target's Profile UUID (via `nerm_list_profiles`) before executing the search.
*   **User Link Types (`owner select`, `owner search`, `contributor select`, `contributor search`):** These act as foreign keys to NERM Users. **Agent Directive:** The agent MUST resolve natural language names to the target's User UUID (via `nerm_list_users`) before executing the search.

### 12.4 Industry-Specific Business Models (Terminology Mapping)
Administrators will frequently use industry-specific language. The agent must seamlessly translate these terms into the correct underlying Baseline Profile Type.

| Baseline NERM Object | Franchise Model Alias | Manufacturing / Supply-Chain Alias | Healthcare Alias |
| :--- | :--- | :--- | :--- |
| **Organization** | Property Company, Franchisee, Supplier | Supplier | Organization |
| **Sub-Organization** | Property, Franchisee Facility | Supplier Group | Sub-Organization |
| **Population** | Suppliers, Associates, Vendors | Suppliers, Associates, Vendors | Consultant, Clinician, Vendor, Student |
| **Sub-Population** | Franchise Supplier, Onsite Vendor, Housekeeping | (Varies by manufacturing site) | Travel Nurse, Nursing Intern, IT Staff Aug |
| **Department** | Department (Customer Specific) | Projects, Divisions | Projects, Divisions, Wards |
| **Location** | Location (Corporate or Franchisee) | Site, Plant | Hospital, Clinic, Facility |

---

## 13. Acceptance criteria (summary)

1. **Agent Independence:** The MCP server operates statelessly and can run on any platform supporting standard MCP transports, while maintaining native AWS Bedrock AgentCore deployment support.
2. **Operations:** Administrator can ask natural-language questions; agent uses MCP tools against the correct tenant URL and token securely.
3. **Multi-agent Orchestration:** Other agents can call this agent successfully by passing NERM credentials via headers, receiving markdown or data-serialized charts as requested.
4. **Resilience & Caching:** Repeated profile-type or attribute lookups within TTL do not re-fetch full catalogs from NERM. Rate limits trigger backoffs. Pagination does not exceed circuit-breaker limits unless forced.
5. **Safety:** Advanced search rejects SQL-style payloads. Writes occur only for explicit requests. PII is masked from chat output. Asynchronous workflows do not falsely report immediate completion.
6. **Data Isolation:** Different tokens/URLs do not share agent sessions or reference-data cache partitions.
7. **Semantic Accuracy:** The agent successfully uses the ER rules, Attribute Data Types, and Industry Aliases to dynamically resolve UUIDs and query the correct database Profiles.

---

## Document history

| Version | Summary |
|---------|---------|
| 1.0 | Initial requirements specification for the platform-agnostic NERM MCP Server + MCP tool server. |
| 1.1 | Updated to support platform-agnostic architecture, agent-to-agent communication, and enhanced security/resilience controls. |
| 1.2 | Added comprehensive NERM Domain Glossary, Entity Relationship Maps, and industry-specific alias routing logic. Added safety checks for pagination and PII. Refined document structure for production readiness. |
| 1.3 | Added Section 12.3 detailing Attribute Data Types (`profile select`, `owner search`, etc.) and the mandatory UUID resolution logic for relational attributes. |