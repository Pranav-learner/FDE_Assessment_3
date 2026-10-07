# Architecture A: Single-Agent Baseline Specification

**Document ID:** `docs/fde/19_architecture_a.md`  
**Phase:** 4 — Architecture A (Single-Agent Baseline)  
**System:** AI Procurement Request Copilot  
**Author:** Forward Deployed Engineering (FDE)  
**Status:** IMPLEMENTED & VERIFIED  

---

## 1. Architectural Overview

Architecture A establishes the baseline single-agent implementation for the AI Procurement Request Copilot. In accordance with the fundamental architectural principle of this system:

> **The LLM is a reasoning and communication layer. The deterministic foundation is the policy authority.**

The single agent does not act as an autonomous policy maker. Instead, it coordinates evidence gathering through structured tools, invokes the deterministic procurement decision engine as authoritative ground truth, performs qualitative reasoning regarding software catalog overlap and business fit, and synthesizes clear, structured explanations for stakeholders and human reviewers.

```
                    ┌───────────────────────────────────┐
                    │      INCOMING PURCHASE REQUEST    │
                    │        (request_id via API)       │
                    └─────────────────┬─────────────────┘
                                      │
                                      ▼
                    ┌───────────────────────────────────┐
                    │           SINGLE AGENT            │
                    │   (src/agents/single_agent.py)    │
                    └─────────────────┬─────────────────┘
                                      │
         ┌────────────────────────────┴───────────────────────────┐
         │                                                        │
         ▼                                                        ▼
┌───────────────────┐                                  ┌────────────────────┐
│   TOOL CONTEXT    │                                  │ DETERMINISTIC BASE │
│   - Context Tool  │                                  │ - Rule Engine      │
│   - Catalog Tool  │                                  │ - Decision Engine  │
│   - Vendor API    │                                  │ - 4-Tier Precedence│
└────────┬──────────┘                                  └─────────┬──────────┘
         │                                                       │
         │                AUTHORITATIVE DETERMINATION            │
         └────────────────────────────┬──────────────────────────┘
                                      │
                                      ▼
                    ┌───────────────────────────────────┐
                    │     LLM REASONING & SYNTHESIS     │
                    │     - Business fit reasoning      │
                    │     - Catalog overlap analysis    │
                    │     - Clarification questions     │
                    │     - Stakeholder summary         │
                    └─────────────────┬─────────────────┘
                                      │
                                      ▼
                    ┌───────────────────────────────────┐
                    │     DETERMINISTIC VALIDATOR       │
                    │  (Enforces policy invariants,     │
                    │   overrides any hallucinations)   │
                    └─────────────────┬─────────────────┘
                                      │
                                      ▼
                    ┌───────────────────────────────────┐
                    │       SingleAgentResponse         │
                    │   (human_review_required = True)  │
                    └───────────────────────────────────┘
```

---

## 2. Core Responsibilities & Boundaries

| Responsibility | Handled By | Rationale |
|:---|:---|:---|
| **Request & Profile Lookup** | `get_request_context` | Deterministic CSV/JSON parsing from system of record. |
| **Catalog Overlap Search** | `search_software_catalog` | Structured inventory matching against active tools. |
| **Vendor Risk Verification** | `get_vendor_risk` | REST call to external mock vendor-risk service. |
| **Financial Threshold Routing** | Deterministic Rule Engine | Exact delegation brackets ($\le\$1\text{k}, \$10\text{k}, \$25\text{k}$). |
| **Security / Privacy / Legal Triggers** | Deterministic Rule Engine | Strict policy compliance; zero LLM drift or override. |
| **Decision Precedence (1 to 4)** | Deterministic Decision Engine | Rigorous conflict resolution (Missing Info $\to$ Manual Review $\to$ Governance $\to$ Standard). |
| **Business Fit Analysis** | Single Agent (LLM) | Evaluates whether catalog alternative satisfies stated workflow. |
| **Clarification Questions** | Single Agent (LLM) | Formulates polite, targeted follow-up prompts for missing information. |
| **Response Assembly & Guardrails** | Deterministic Response Validator | Ensures policy-sensitive fields cannot be altered by LLM output. |
| **Final Purchase Authorization** | Human Reviewer | AI is purely advisory; `human_review_required = True` is invariant. |

---

## 3. Data Flow & Execution Lifecycle

1. **Intake & Dispatch:** `src/solution.py::handle_request(request_id, architecture="single")` dispatches to `run_single_agent(request_id)`.
2. **Deterministic Evaluation:** The agent immediately runs `make_procurement_decision_with_trace(request_id)`, executing:
   - Request intake (`get_request_context`)
   - Software catalog search (`search_software_catalog`)
   - Vendor risk status query (`get_vendor_risk`)
   - Policy retrieval (`get_procurement_policy`)
   - Deterministic rule engine evaluation (`evaluate_procurement_rules`)
3. **Prompt Construction:** The agent injects structured tool context and the authoritative `ProcurementDecision` into the user prompt alongside `SINGLE_AGENT_SYSTEM_PROMPT`.
4. **LLM Inference:** The agent calls `BaseLLMClient.generate()` requesting structured JSON.
5. **Validation & Assembly:** `validate_and_assemble_response()` copies deterministic fields verbatim, verifies prompt injection defenses, normalizes clarification questions, and returns a verified `SingleAgentResponse`.
6. **Telemetry Recording:** Records `llm_calls = 1`, `tool_calls = 5`, tool names, and end-to-end latency.

---

## 4. Error Handling and Deterministic Fallback

If the LLM client encounters an unrecoverable condition:
- Network timeout (`timeout > 12.0s`)
- Provider API error (HTTP 4xx, 5xx, quota exhaustion)
- Missing environment API key (`OPENAI_API_KEY` / `GEMINI_API_KEY` not configured)
- Malformed / non-parseable JSON response

The agent executes the **Deterministic Fallback**:
- Discards malformed LLM output without failing the request.
- Uses `ProcurementDecision` as the sole basis of the final response.
- Generates high-quality deterministic summaries, risk explanations, and clarification questions.
- Retains all required approvals, risk flags, missing information items, and `human_review_required = True`.
- Ensures zero downtime and complete evaluation stability.
