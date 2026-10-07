# Architecture B Contracts & Data Schemas

**Document ID:** `docs/fde/24_staged_agent_contracts.md`  
**Phase:** 5 — Architecture B (Staged Two-Agent Architecture)  
**System:** AI Procurement Request Copilot  
**Author:** Forward Deployed Engineering (FDE)  
**Status:** IMPLEMENTED & VERIFIED  

---

## 1. Agent 1 Contract: `IntakeOverlapDossier`

Represents the structured, typed handoff from Agent 1 (Intake & Overlap Specialist) to Agent 2:

```python
class IntakeOverlapDossier(BaseModel):
    request_id: str
    business_need: str = Field(description="Core business objective identified from request")
    intended_workflow: str = Field(description="Operational workflow where tool will be applied")
    user_persona: str = Field(description="Target user profile and department context")
    requested_capabilities: list[str] = Field(default_factory=list, description="Key functional capabilities requested")
    relevant_catalog_matches: list[str] = Field(default_factory=list, description="Existing software catalog tools in same category/vendor")
    existing_tool_overlap: bool = Field(default=False, description="Whether software overlap was detected")
    functional_fit_analysis: str = Field(description="Analysis of whether catalog alternatives meet the need")
    functional_gaps: list[str] = Field(default_factory=list, description="Capabilities not satisfied by existing tools")
    unresolved_questions: list[str] = Field(default_factory=list, description="Intake questions regarding business requirements")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence score in available evidence")
```

---

## 2. Agent 2 Contract: `GovernanceTriageDossier`

Represents the governance synthesis produced by Agent 2 (Governance & Triage Specialist):

```python
class GovernanceTriageDossier(BaseModel):
    request_id: str
    executive_summary: str = Field(description="Concise triage overview for procurement leadership")
    governance_summary: str = Field(description="Summary of all required governance reviews")
    financial_summary: str = Field(description="Budget, spend threshold, and finance governance notes")
    security_summary: str = Field(description="InfoSec review status, data access, and vendor posture")
    privacy_summary: str = Field(description="Data privacy, PII, and regulatory assessment")
    legal_summary: str = Field(description="Contractual terms and new-vendor legal assessment")
    risk_explanation: str = Field(description="Detailed explanation of risk flags for human reviewers")
    recommended_human_actions: list[str] = Field(default_factory=list, description="Specific actions required by human reviewers")
    clarification_questions: list[str] = Field(default_factory=list, description="Commercial/policy clarification questions")
```

---

## 3. Final Output Contract: `StagedAgentResponse`

Extends `ProcurementDecision` (`src/contracts.py`) to guarantee 100% interoperability with evaluation runners while embedding full auditability for both agents:

```python
class StagedAgentResponse(ProcurementDecision):
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

    # Qualitative Synthesized Fields
    summary: str
    reasoning: str
    catalog_fit_analysis: str
    clarification_questions: list[str]

    # Embedded Agent Dossiers
    intake_dossier: IntakeOverlapDossier | None = None
    governance_dossier: GovernanceTriageDossier | None = None
```

---

## 4. Field Authority Matrix

| Field | Source of Truth | Epistemic Authority | Mutability by Agents |
|:---|:---:|:---:|:---:|
| `request_id` | Input Request | Identity | Immutable |
| `recommendation` | Decision Engine | Deterministic Policy | **Immutable** |
| `required_approvals` | Rule Engine | Financial & Governance Matrix | **Immutable** |
| `missing_information` | Rule Engine | Data Completeness Gate | **Immutable** |
| `risk_flags` | Rule Engine | Policy Trigger Taxonomy | **Immutable** |
| `human_review_required` | Corporate Policy §11 | Enterprise Safety Invariant | **Immutable (Always True)** |
| `next_step` | Decision Engine | Precedence Routing Rule | **Immutable** |
| `evidence` | Data Access / Tools | Grounded Fact Inventory | **Immutable** |
| `summary` | Agent 2 | Communication Layer | Sanitized & Merged |
| `reasoning` | Agent 2 | Communication Layer | Sanitized & Merged |
| `catalog_fit_analysis` | Agent 1 | Business Reasoning | Grounded & Validated |
| `clarification_questions` | Agent 1 + Agent 2 | Intake & Policy Support | Deduped with Guaranteed Fallback |
