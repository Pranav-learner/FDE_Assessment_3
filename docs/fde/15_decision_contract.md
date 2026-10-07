# 15. Decision Contract & Vocabulary Specification: AI Procurement Request Copilot

**Document Version:** 1.0.0  
**Phase:** Phase 3 (Decision Contract & Schema)  
**Author:** Forward Deployed Engineering (FDE)

---

## 1. Overview & Contract Alignment

The deterministic decision engine emits output conforming directly to the canonical `ProcurementDecision` contract defined in `src/contracts.py`.

The decision contract provides a structured, typed, and auditable payload for consumption by procurement specialists, downstream workflow engines, and the public evaluation harness (`evals/run_public_evals.py`).

---

## 2. Controlled Recommendation Vocabulary

To eliminate ambiguity, prevent autonomous execution, and maintain strict advisory boundaries, the decision engine restricts its recommendation values to three mutually exclusive states:

```python
class RecommendationState(str, Enum):
    NEEDS_INFORMATION = "NEEDS_INFORMATION"
    MANUAL_REVIEW = "MANUAL_REVIEW"
    PROCEED_TO_REVIEW = "PROCEED_TO_REVIEW"
```

### Semantic Definitions

| State Name | Operational Meaning | When Triggered | Downstream Action |
|---|---|---|---|
| **`NEEDS_INFORMATION`** | Request is incomplete and cannot be evaluated safely. | Mandatory fields (`cost`, `user_count`, `data_access_level`) are null, missing, or unknown. | Hold ticket; request specific missing details from employee. |
| **`MANUAL_REVIEW`** | Material evidence is missing, failed, or conflicting. | Vendor risk API returns 503/timeout, or internal registry conflicts with external risk score. | Route to InfoSec or Procurement specialist for manual investigation. |
| **`PROCEED_TO_REVIEW`** | Request is complete and evidence is verified; ready for designated human signoffs. | All evidence gathered; financial threshold and governance review triggers determined. | Route request to the exact roster in `required_approvals`. |

### Forbidden States
The engine **strictly forbids** and never produces:
* `APPROVED`
* `AUTO_APPROVED`
* `PURCHASED`
* `PURCHASE_NOW`
* `REJECTED` (Overlap or deficits require human review, not automated rejection).

---

## 3. The `ProcurementDecision` Contract

```python
class ProcurementDecision(BaseModel):
    request_id: str = Field(description="Unique request identifier")
    recommendation: str = Field(description="Controlled recommendation state (NEEDS_INFORMATION, MANUAL_REVIEW, PROCEED_TO_REVIEW)")
    evidence: list[EvidenceItem] = Field(default_factory=list, description="Verifiable evidence findings")
    required_approvals: list[str] = Field(default_factory=list, description="Ordered roster of required human approvers and reviewers")
    missing_information: list[str] = Field(default_factory=list, description="List of missing material fields")
    risk_flags: list[str] = Field(default_factory=list, description="Active governance and policy risk flags")
    next_step: str = Field(description="Actionable, deterministic next-step instruction")
    human_review_required: bool = Field(default=True, description="Strictly True; human authority preserved")
    telemetry: RunTelemetry | None = Field(default=None, description="Observability counts for LLM and tool calls")
```

---

## 4. Extended Contract: `DeterministicDecisionResult` & Decision Trace

For internal auditing, governance logging, and test verification, the decision engine provides an extended envelope:

```python
class DecisionTraceStep(BaseModel):
    rule_or_phase: str
    evaluated_condition: str
    outcome: str
    evidence_references: list[str] = Field(default_factory=list)

class DeterministicDecisionResult(BaseModel):
    decision: ProcurementDecision
    state: RecommendationState
    trace: list[DecisionTraceStep] = Field(default_factory=list)
```

### Trace Step Anatomy
Each trace step records:
* `rule_or_phase`: The policy section, intake phase, or precedence rule evaluated.
* `evaluated_condition`: The specific boolean condition or parameter checked.
* `outcome`: Factual determination (e.g., `"BLOCKED: Missing annual_cost_usd"`, `"Overlap detected: True"`).
* `evidence_references`: Links back to underlying data sources or approver roles.
