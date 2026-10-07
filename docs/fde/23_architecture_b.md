# Architecture B: Staged Two-Agent Architecture Specification

**Document ID:** `docs/fde/23_architecture_b.md`  
**Phase:** 5 — Architecture B (Staged Two-Agent Architecture)  
**System:** AI Procurement Request Copilot  
**Author:** Forward Deployed Engineering (FDE)  
**Status:** IMPLEMENTED & VERIFIED  

---

## 1. Architectural Overview & Rationale

Architecture B introduces a **staged, specialized multi-agent pipeline** comprising exactly two logical LLM agents:

1. **Agent 1: Intake & Overlap Specialist (`src/agents/intake_overlap_agent.py`)**  
   Focuses on user intent, business justification, workflow requirements, and functional comparison against existing active software inventory in the corporate catalog.
2. **Agent 2: Governance & Triage Specialist (`src/agents/governance_triage_agent.py`)**  
   Consumes Agent 1's structured dossier alongside verified vendor risk status, departmental budgets, and authoritative policy decisions to synthesize an executive governance brief for human approvers.

```
                        USER REQUEST
                             │
                             ▼
                ┌────────────────────────┐
                │       AGENT 1          │
                │ Intake & Overlap       │
                │ Specialist             │
                └────────────┬───────────┘
                             │
                     IntakeOverlapDossier
                     (Structured Handoff)
                             │
                             ▼
                ┌────────────────────────┐
                │       AGENT 2          │
                │ Governance & Triage    │
                │ Specialist             │
                └────────────┬───────────┘
                             │
                             ▼
                 DETERMINISTIC FOUNDATION
                 (Rule Engine + Decision Engine)
                             │
                             ▼
                  AUTHORITATIVE DECISION
                 (ProcurementDecision Model)
                             │
                             ▼
                 DETERMINISTIC VALIDATOR
                 (Enforces policy invariants,
                  blocks any hallucinations)
                             │
                             ▼
                    StagedAgentResponse
                (human_review_required = True)
```

---

## 2. Why Two Agents? (Architectural Division)

In Architecture A, a single prompt was responsible for parsing untrusted user justifications, searching the catalog for software overlap, evaluating multi-threshold financial delegations, interpreting vendor security certificates, and synthesizing executive communications. This context crowding increased vulnerability to subtle hallucination, missed workflow nuances, and diluted prompt instructions.

Architecture B separates concerns into two distinct epistemic stages:
- **Separation of Concerns:** Business and functional fit analysis is completely decoupled from governance, compliance, and risk routing.
- **Cognitive Specialization:** Agent 1 evaluates *need and functionality*; Agent 2 evaluates *risk, compliance, and process*.
- **Structured Handoff:** Communication between agents occurs via a typed, auditable Pydantic contract (`IntakeOverlapDossier`), preventing free-form conversational drift.

---

## 3. Layer Responsibilities & Authority

| Responsibility | Handled By | Epistemic Authority |
|:---|:---|:---:|
| **Intake Extraction & User Persona** | Agent 1 (`IntakeOverlapAgent`) | LLM Reasoning |
| **Catalog Overlap Analysis** | Agent 1 (`IntakeOverlapAgent`) | LLM Reasoning (Grounded) |
| **Functional Gap Identification** | Agent 1 (`IntakeOverlapAgent`) | LLM Reasoning (Grounded) |
| **Financial Delegation Calculation** | Deterministic Rule Engine | **Deterministic Code** |
| **Security & Privacy Policy Gates** | Deterministic Rule Engine | **Deterministic Code** |
| **Vendor Risk Outage Trap (503)** | Deterministic Decision Engine | **Deterministic Code** |
| **Decision Precedence (1 to 4)** | Deterministic Decision Engine | **Deterministic Code** |
| **Governance Risk Synthesis** | Agent 2 (`GovernanceTriageAgent`) | LLM Communication |
| **Reviewer Action Formulation** | Agent 2 (`GovernanceTriageAgent`) | LLM Communication |
| **Final Assembly & Policy Invariants** | Deterministic Response Validator | **Deterministic Code** |
| **Final Spend & Legal Authorization** | Human Approver | **Human Authority** |

---

## 4. Execution Data Flow

1. **Intake & Dispatch:** `src/solution.py::handle_request(request_id, architecture="staged")` calls `run_staged_agents(request_id)`.
2. **Deterministic Baseline Execution:** The pipeline invokes `make_procurement_decision_with_trace(request_id)`, executing all tools and policy rules deterministically.
3. **Shared Tool Context Extraction:** Tool results (`request_context`, `software_catalog`, `vendor_risk`) are shared between agents without duplicate queries.
4. **Agent 1 Execution:** Agent 1 parses intent and catalog alternatives, outputting an `IntakeOverlapDossier`. Telemetry records 1 LLM call.
5. **Structured Handoff:** The `IntakeOverlapDossier` is injected directly into Agent 2's prompt alongside verified policy facts.
6. **Agent 2 Execution:** Agent 2 synthesizes governance and risk implications, outputting a `GovernanceTriageDossier`. Telemetry records 2nd LLM call.
7. **Deterministic Validation & Merge:** `validate_and_assemble_staged_response()` combines both dossiers with the authoritative `ProcurementDecision`, enforces policy invariants, and emits a verified `StagedAgentResponse`.

---

## 5. Failure Handling and Deterministic Fallback

Architecture B implements **hierarchical fault tolerance**:
- **Agent 1 Failure (Timeout / Malformed JSON / Outage):** If Agent 1 fails, a safe deterministic fallback `IntakeOverlapDossier` is synthesized from catalog tool data. The pipeline continues without crashing.
- **Agent 2 Failure (Timeout / Malformed JSON / Outage):** If Agent 2 fails, a safe deterministic fallback `GovernanceTriageDossier` is synthesized directly from the `ProcurementDecision`.
- **Policy Invariant:** In no event can an LLM timeout, malformed string, or provider outage cause a request to become falsely approved or bypass human governance.
