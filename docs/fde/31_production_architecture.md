# 31. Production Architecture & Systems Blueprint

## 1. Architectural Overview & System Flow

The **AI Procurement Request Copilot** implements a tripartite architecture separating untrusted business inputs, authoritative deterministic policy enforcement, and qualitative LLM synthesis.

```
                              INBOUND PURCHASE REQUEST
                         (CLI, REST API, Streamlit Web UI)
                                        │
                                        ▼
                         ┌─────────────────────────────┐
                         │   APPLICATION CONTROLLER    │
                         │      (src/solution.py)      │
                         └──────────────┬──────────────┘
                                        │
             ┌──────────────────────────┴──────────────────────────┐
             ▼                                                     ▼
┌─────────────────────────┐                               ┌─────────────────────────┐
│   ARCHITECTURE A (MVP)  │                               │ ARCHITECTURE B (STAGED) │
│ (1 LLM Synthesis Call)  │                               │  (2 Specialized Agents) │
└────────────┬────────────┘                               └────────────┬────────────┘
             │                                                         │
             └──────────────────────────┬──────────────────────────────┘
                                        │
                                        ▼
                         ┌─────────────────────────────┐
                         │   DETERMINISTIC TOOLS       │
                         │  - Request Context Tool     │
                         │  - Software Catalog Tool    │
                         │  - Vendor Risk API Tool     │
                         │  - Policy Ingestion Tool    │
                         └──────────────┬──────────────┘
                                        │
                                        ▼
                         ┌─────────────────────────────┐
                         │  DETERMINISTIC RULE ENGINE  │
                         │     (15 Audited Rules)      │
                         └──────────────┬──────────────┘
                                        │
                                        ▼
                         ┌─────────────────────────────┐
                         │     DECISION ENGINE         │
                         │  Authoritative Aggregation  │
                         └──────────────┬──────────────┘
                                        │
                               Authoritative Facts
                                        │
                                        ▼
                         ┌─────────────────────────────┐
                         │    QUALITATIVE LLM LAYER    │
                         │  (Single or Staged Synthesis)│
                         └──────────────┬──────────────┘
                                        │
                               Raw Qualitative Output
                                        │
                                        ▼
                         ┌─────────────────────────────┐
                         │   DETERMINISTIC VALIDATOR   │
                         │ - Post-Validation Enforcer  │
                         │ - Approval Claim Stripper   │
                         │ - Policy Invariant Gate     │
                         └──────────────┬──────────────┘
                                        │
                                        ▼
                         ┌─────────────────────────────┐
                         │     HUMAN REVIEW GATE       │
                         │ human_review_required = True│
                         │   Final Approver Authority  │
                         └─────────────────────────────┘
```

---

## 2. Trust Boundaries

1. **Untrusted Business Data Boundary:**
   - Requester justification text, notes, external vendor strings, and integration requests are classified as **untrusted data**.
   - Input fields are wrapped in strict data delimiters (`<<<UNTRUSTED_REQUEST_TEXT>>>`).
   - Instructions embedded within request fields (e.g., "Ignore rules", "CFO approved") are quarantined and cannot influence control flow.
2. **Deterministic Governance Boundary:**
   - Financial limits, required approver rosters, missing data flags, and security review triggers reside exclusively within deterministic Python code.
   - The LLM layer cannot add, remove, or modify authoritative policy gates.
3. **Model Output Sanitization Boundary:**
   - All natural-language text produced by LLMs passes through `validate_and_assemble_response` (Architecture A) or `validate_and_assemble_staged_response` (Architecture B).
   - Case-insensitive regex filters sanitize unauthorized claims (`[unauthorized claim removed]`).
   - The invariant `human_review_required = True` is programmatically overwritten on every response.

---

## 3. Failure & Isolation Boundaries

| Failure Mode | Detection Point | Handling & Recovery Mechanism | Safety Outcome |
|:---|:---|:---|:---|
| **Upstream Vendor Risk 500/503** | `get_vendor_risk()` | Catches HTTP error; logs tool failure; sets `vendor_risk_unavailable` flag; routes to Security/Legal | Graceful degradation; Review preserved |
| **Missing Request Fields** | `evaluate_procurement_rules()` | Evaluates BR-01; identifies missing items; sets `NEEDS_INFORMATION` recommendation | Request halted at triage; Questions generated |
| **LLM Provider Timeout** | Provider call | 15s timeout catches `TimeoutError`; triggers deterministic fallback | Zero crash; Policy intact; Review preserved |
| **LLM Malformed JSON** | JSON decoder | Catches `JSONDecodeError`; triggers deterministic fallback | Clean response assembled from rule facts |
| **Agent 1 Failure (Arch B)** | Orchestrator | Fallback `IntakeOverlapDossier` synthesized from catalog tool data | Agent 2 executes; No pipeline break |
| **Agent 2 Failure (Arch B)** | Orchestrator | Fallback `GovernanceTriageDossier` synthesized from rule results | Final response compliant with policy |

---

## 4. Configuration & Observability

### Configuration:
- `VENDOR_RISK_BASE_URL`: Base URL for external vendor risk REST endpoint (default: `http://127.0.0.1:8001`).
- `LLM_MODE`: `mock` (deterministic offline engine) or `live` (networked LLM API).
- `DEFAULT_ARCHITECTURE`: Defaults to `single` (Core Production MVP).
- `LLM_TIMEOUT_SECONDS`: 15.0 seconds.
- `VENDOR_API_TIMEOUT_SECONDS`: 5.0 seconds.

### Telemetry (`RunTelemetry`):
Every execution produces structured telemetry tracked in `ProcurementDecision.telemetry`:
- `llm_calls`: Number of LLM invocations (1 for Architecture A, 2 for Architecture B).
- `tool_calls`: Number of deterministic tool invocations (5 for both architectures).
- `tool_names`: List of tools queried during evidence gathering.
- `agent_names`: List of active agents (`["intake_overlap", "governance_triage"]` for Architecture B).

---

## 5. Deployment Models

1. **CLI / Batch Mode:** Standalone Python execution via `python app.py --request-id <ID> [--json]` for developer automation, scripting, and offline triage.
2. **Containerized REST API:** Docker container running FastAPI on port 8001 exposing `/health`, `/ready`, and `/procurement/evaluate`.
3. **Interactive Web UI:** Streamlit application running on port 8501 for procurement specialists and stakeholders.
