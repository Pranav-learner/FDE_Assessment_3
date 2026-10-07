from __future__ import annotations

from enum import Enum
from typing import Any
from pydantic import BaseModel, Field

from src.contracts import EvidenceItem, ProcurementDecision, RunTelemetry
from src.tools.procurement_policy import get_procurement_policy
from src.tools.request_context import get_request_context
from src.tools.rule_engine import POLICY_REFERENCE_DATE, evaluate_procurement_rules
from src.tools.software_catalog import search_software_catalog
from src.tools.vendor_risk import get_vendor_risk


class RecommendationState(str, Enum):
    """Controlled recommendation vocabulary for deterministic decisions."""
    NEEDS_INFORMATION = "NEEDS_INFORMATION"
    MANUAL_REVIEW = "MANUAL_REVIEW"
    PROCEED_TO_REVIEW = "PROCEED_TO_REVIEW"


class DecisionTraceStep(BaseModel):
    """Audit step documenting the path from raw evidence to final recommendation."""
    rule_or_phase: str
    evaluated_condition: str
    outcome: str
    evidence_references: list[str] = Field(default_factory=list)


class DeterministicDecisionResult(BaseModel):
    """Complete decision envelope containing standard contract and audit trace."""
    decision: ProcurementDecision
    state: RecommendationState
    trace: list[DecisionTraceStep] = Field(default_factory=list)


def _deduplicate_evidence(evidence_list: list[EvidenceItem]) -> list[EvidenceItem]:
    """Deduplicate equivalent evidence items preserving chronological insertion order."""
    seen: set[tuple[str, str, str | None]] = set()
    deduped: list[EvidenceItem] = []
    for item in evidence_list:
        key = (item.source.strip().lower(), item.finding.strip(), item.reference)
        if key not in seen:
            seen.add(key)
            deduped.append(item)
    return deduped


def make_procurement_decision(request_id: str) -> ProcurementDecision:
    """Execute end-to-end deterministic procurement decision pipeline.

    Gathers evidence across tools, applies deterministic rules, aggregates
    policy findings, and returns an advisory ProcurementDecision.
    """
    result = make_procurement_decision_with_trace(request_id)
    return result.decision


def make_procurement_decision_with_trace(
    request_id: str,
    vendor_risk_simulate_failure: str | None = None,
) -> DeterministicDecisionResult:
    """Execute end-to-end decision pipeline with complete audit decision trace.

    Precedence order:
    Priority 1: Material required information missing -> NEEDS_INFORMATION
    Priority 2: Material evidence unavailable or conflicting -> MANUAL_REVIEW
    Priority 3: Evidence sufficient, additional governance reviews required -> PROCEED_TO_REVIEW
    Priority 4: No blocking issues, standard approval path -> PROCEED_TO_REVIEW
    """
    trace: list[DecisionTraceStep] = []
    accumulated_evidence: list[EvidenceItem] = []
    tool_names: list[str] = []
    tool_calls_count = 0

    # -------------------------------------------------------------
    # STEP 1: GATHER REQUEST CONTEXT (requests, employees, budgets)
    # -------------------------------------------------------------
    tool_names.append("get_request_context")
    tool_calls_count += 1
    context_res = get_request_context(request_id)
    accumulated_evidence.extend(context_res.evidence)

    if not context_res.success or not context_res.data:
        trace.append(
            DecisionTraceStep(
                rule_or_phase="Context Intake",
                evaluated_condition=f"Fetch request {request_id}",
                outcome="FAILED",
                evidence_references=[request_id],
            )
        )
        decision = ProcurementDecision(
            request_id=request_id,
            recommendation=RecommendationState.NEEDS_INFORMATION.value,
            evidence=accumulated_evidence,
            required_approvals=["Procurement"],
            missing_information=["valid request record"],
            risk_flags=["missing_information"],
            next_step=f"Investigate missing or invalid request ID: '{request_id}'.",
            human_review_required=True,
            telemetry=RunTelemetry(llm_calls=0, tool_calls=tool_calls_count, tool_names=tool_names),
        )
        return DeterministicDecisionResult(
            decision=decision,
            state=RecommendationState.NEEDS_INFORMATION,
            trace=trace,
        )

    context_data = context_res.data
    req = context_data.get("request", {})
    product_name = req.get("product_name")
    vendor_name = req.get("vendor_name", "")
    category = req.get("category")

    trace.append(
        DecisionTraceStep(
            rule_or_phase="Context Intake",
            evaluated_condition=f"Request {request_id} for '{product_name}' by '{req.get('requester_id')}' in '{context_data.get('department')}'",
            outcome="SUCCESS",
            evidence_references=[request_id, context_data.get("department", "")],
        )
    )

    # -------------------------------------------------------------
    # STEP 2: SEARCH SOFTWARE CATALOG
    # -------------------------------------------------------------
    tool_names.append("search_software_catalog")
    tool_calls_count += 1
    catalog_res = search_software_catalog(
        product_name=product_name,
        vendor_name=vendor_name,
        category=category,
    )
    accumulated_evidence.extend(catalog_res.evidence)
    catalog_data = catalog_res.data or {}
    has_overlap = catalog_data.get("has_overlap", False)

    trace.append(
        DecisionTraceStep(
            rule_or_phase="Catalog Search",
            evaluated_condition=f"Search catalog for product='{product_name}', vendor='{vendor_name}', category='{category}'",
            outcome=f"Overlap detected: {has_overlap}",
            evidence_references=["software_catalog.csv"],
        )
    )

    # -------------------------------------------------------------
    # STEP 3: QUERY EXTERNAL VENDOR RISK
    # -------------------------------------------------------------
    tool_names.append("get_vendor_risk")
    tool_calls_count += 1
    vendor_risk_res = get_vendor_risk(
        vendor_name=vendor_name,
        simulate_failure=vendor_risk_simulate_failure,
    )
    accumulated_evidence.extend(vendor_risk_res.evidence)
    vendor_risk_verified = vendor_risk_res.data.get("verified", False) if vendor_risk_res.data else False

    trace.append(
        DecisionTraceStep(
            rule_or_phase="Vendor Risk Query",
            evaluated_condition=f"Query vendor risk API for '{vendor_name}'",
            outcome=f"Verified: {vendor_risk_verified}, Success: {vendor_risk_res.success}",
            evidence_references=[vendor_name],
        )
    )

    # -------------------------------------------------------------
    # STEP 4: FETCH PROCUREMENT POLICY
    # -------------------------------------------------------------
    tool_names.append("get_procurement_policy")
    tool_calls_count += 1
    policy_res = get_procurement_policy()
    accumulated_evidence.extend(policy_res.evidence)

    trace.append(
        DecisionTraceStep(
            rule_or_phase="Policy Retrieval",
            evaluated_condition="Load authoritative policy text and rules",
            outcome=f"Version: 2026.09, Reference Date: {POLICY_REFERENCE_DATE}",
            evidence_references=["procurement_policy.md"],
        )
    )

    # -------------------------------------------------------------
    # STEP 5: EVALUATE DETERMINISTIC RULES (Phase 2 Rule Engine)
    # -------------------------------------------------------------
    tool_names.append("evaluate_procurement_rules")
    tool_calls_count += 1
    rule_res = evaluate_procurement_rules(
        context=context_data,
        catalog_result=catalog_res,
        vendor_risk=vendor_risk_res,
    )
    accumulated_evidence.extend(rule_res.evidence)

    # -------------------------------------------------------------
    # STEP 6: DECISION PRECEDENCE & RECOMMENDATION AGGREGATION
    # -------------------------------------------------------------
    missing_info = rule_res.missing_information
    risk_flags = rule_res.risk_flags
    required_approvals = rule_res.required_approvals

    # PRIORITY 1: Material required information missing
    if missing_info:
        rec_state = RecommendationState.NEEDS_INFORMATION
        missing_fields_str = ", ".join(missing_info)
        next_step = f"Request the missing {missing_fields_str} from the requester before proceeding with procurement triage."
        trace.append(
            DecisionTraceStep(
                rule_or_phase="Decision Precedence: Priority 1",
                evaluated_condition="Material required information check (Policy §1)",
                outcome=f"BLOCKED: Missing {missing_fields_str}",
                evidence_references=["Section 1"],
            )
        )

    # PRIORITY 2: Material evidence unavailable or conflicting
    elif "vendor_risk_unavailable" in risk_flags:
        rec_state = RecommendationState.MANUAL_REVIEW
        next_step = f"Obtain current vendor security evidence for '{vendor_name}' and route to Security and Finance for manual risk review."
        trace.append(
            DecisionTraceStep(
                rule_or_phase="Decision Precedence: Priority 2",
                evaluated_condition="Vendor risk API availability check (Policy §10)",
                outcome="MANUAL_REVIEW: Vendor risk API unavailable",
                evidence_references=[vendor_name, "Section 10"],
            )
        )

    elif "conflicting_vendor_evidence" in risk_flags:
        rec_state = RecommendationState.MANUAL_REVIEW
        next_step = f"Reconcile conflicting vendor security records for '{vendor_name}' and route to Security for manual verification."
        trace.append(
            DecisionTraceStep(
                rule_or_phase="Decision Precedence: Priority 2",
                evaluated_condition="Vendor evidence consistency check (Policy §5)",
                outcome="MANUAL_REVIEW: Conflicting internal vs external vendor evidence",
                evidence_references=[vendor_name, "Section 5"],
            )
        )

    # PRIORITY 3: Governance / Security / Privacy / Legal / Budget reviews required
    elif (
        "budget_insufficient" in risk_flags
        or "security_review_required" in risk_flags
        or "privacy_review_required" in risk_flags
        or "legal_review_required" in risk_flags
        or "vendor_review_expired" in risk_flags
        or "existing_tool_overlap" in risk_flags
        or "prompt_injection_detected" in risk_flags
        or any(r in required_approvals for r in ["Security", "Privacy", "Legal", "Finance", "CFO"])
    ):
        rec_state = RecommendationState.PROCEED_TO_REVIEW
        approvers_str = ", ".join(required_approvals)
        next_step = f"Route the request to {approvers_str} for the required governance reviews and approvals."
        trace.append(
            DecisionTraceStep(
                rule_or_phase="Decision Precedence: Priority 3",
                evaluated_condition="Specialized governance review triggers (Policy §§2, 3, 5, 6, 7)",
                outcome=f"PROCEED_TO_REVIEW: Additional governance reviews required: {approvers_str}",
                evidence_references=required_approvals,
            )
        )

    # PRIORITY 4: Standard approval path without special governance triggers
    else:
        rec_state = RecommendationState.PROCEED_TO_REVIEW
        approvers_str = ", ".join(required_approvals)
        next_step = f"Route the request to {approvers_str} for standard business approval."
        trace.append(
            DecisionTraceStep(
                rule_or_phase="Decision Precedence: Priority 4",
                evaluated_condition="Standard approval path check (Policy §4)",
                outcome=f"PROCEED_TO_REVIEW: Standard approvals required: {approvers_str}",
                evidence_references=required_approvals,
            )
        )

    # Trace final decision state
    trace.append(
        DecisionTraceStep(
            rule_or_phase="Final Aggregation",
            evaluated_condition="Aggregate final ProcurementDecision",
            outcome=f"Recommendation: {rec_state.value}, Approvals: {required_approvals}, Risk flags: {risk_flags}",
            evidence_references=[request_id],
        )
    )

    # Deduplicate all accumulated evidence items
    deduped_evidence = _deduplicate_evidence(accumulated_evidence)

    # Build compliant ProcurementDecision
    decision = ProcurementDecision(
        request_id=request_id,
        recommendation=rec_state.value,
        evidence=deduped_evidence,
        required_approvals=required_approvals,
        missing_information=missing_info,
        risk_flags=risk_flags,
        next_step=next_step,
        human_review_required=True,  # STRICT POLICY RULE §11: Always True
        telemetry=RunTelemetry(
            llm_calls=0,  # Deterministic engine: exactly 0 LLM calls
            tool_calls=tool_calls_count,
            tool_names=tool_names,
        ),
    )

    return DeterministicDecisionResult(
        decision=decision,
        state=rec_state,
        trace=trace,
    )
