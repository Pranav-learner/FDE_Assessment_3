# Single-Agent Output Contract & Validation Specification

**Document ID:** `docs/fde/20_single_agent_contract.md`  
**Phase:** 4 — Architecture A (Single-Agent Baseline)  
**System:** AI Procurement Request Copilot  
**Author:** Forward Deployed Engineering (FDE)  
**Status:** IMPLEMENTED & VERIFIED  

---

## 1. Output Contract: `SingleAgentResponse`

The `SingleAgentResponse` model extends the canonical `ProcurementDecision` contract (`src/contracts.py`), guaranteeing 100% backward compatibility with all evaluation runners while exposing rich qualitative narrative fields.

```python
class SingleAgentResponse(ProcurementDecision):
    # Core Deterministic Fields (Inherited from ProcurementDecision)
    request_id: str
    recommendation: str  # NEEDS_INFORMATION | MANUAL_REVIEW | PROCEED_TO_REVIEW
    evidence: list[EvidenceItem]
    required_approvals: list[str]
    missing_information: list[str]
    risk_flags: list[str]
    next_step: str
    human_review_required: bool = True
    telemetry: RunTelemetry | None = None

    # Qualitative Agent Fields
    summary: str
    reasoning: str
    catalog_fit_analysis: str
    clarification_questions: list[str]
```

---

## 2. Field Authority Matrix

| Field | Source of Authority | Can LLM Modify? | Validation Invariant |
|:---|:---:|:---:|:---|
| `request_id` | Input Request | NO | Identical to input |
| `recommendation` | Deterministic Decision Engine | **NO** | `final.recommendation == decision.recommendation` |
| `required_approvals` | Deterministic Rule Engine | **NO** | `final.required_approvals == decision.required_approvals` |
| `missing_information` | Deterministic Rule Engine | **NO** | `final.missing_information == decision.missing_information` |
| `risk_flags` | Deterministic Rule Engine | **NO** | `final.risk_flags == decision.risk_flags` |
| `human_review_required` | Corporate Policy §11 | **NO** | **Always `True`** |
| `evidence` | Multi-Source Tools | **NO** | Deduped tool findings preserved verbatim |
| `next_step` | Decision Precedence Model | **NO** | Authoritative routing instruction preserved |
| `summary` | Single Agent (LLM) | YES | Sanitized of unauthorized approval tokens |
| `reasoning` | Single Agent (LLM) | YES | Must ground arguments in provided evidence |
| `catalog_fit_analysis` | Single Agent (LLM) | YES | Restricted to catalog descriptions |
| `clarification_questions` | Single Agent (LLM) | YES | If info missing, guaranteed non-empty list |

---

## 3. Response Validator (`validate_and_assemble_response`)

The validator functions as an immutable boundary between non-deterministic model generation and enterprise software operations:

1. **Token Sanitization:** Discards or sanitizes unauthorized phrases such as `"auto-approved"`, `"purchase approved"`, or `"override policy"` if generated in narrative strings.
2. **Missing Information Enforcement:** If `decision.missing_information` is non-empty, the validator verifies that `clarification_questions` contains polite, specific prompts for each missing field. If the LLM omitted them, fallback prompts are injected deterministically.
3. **Immutability of Delegation:** Reviewer lists (`required_approvals`) cannot be cleared or pruned by the LLM.
4. **Guaranteed Human Gate:** Even if malicious prompt injection instructed the agent to set `human_review_required = False`, the validator enforces `True`.
