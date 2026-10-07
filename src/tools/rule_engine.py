from __future__ import annotations

from datetime import date
import re
from typing import Any

from src.contracts import EvidenceItem
from src.data_access import load_vendors
from src.tools.contracts import (
    CatalogSearchResult,
    RequestContext,
    RuleEvaluationResult,
    ToolResult,
    VendorRiskProfile,
)

# Canonical reference date per policy specification (Section 2026.09)
POLICY_REFERENCE_DATE = date(2026, 9, 30)

# Sensitive data levels requiring Security review
SECURITY_SENSITIVE_DATA_LEVELS = {
    "source_code",
    "production_telemetry",
    "confidential_documents",
    "credentials",
    "secrets",
    "employee_pii",
    "customer_pii",
}

# Integrations requiring Security review
SECURITY_SENSITIVE_INTEGRATIONS = {
    "production cloud account",
    "production cloud",
    "git repositories",
    "git repository",
    "document repository",
    "crm",
    "credentials",
    "secrets",
}

# Prompt injection markers in untrusted business text
PROMPT_INJECTION_PATTERNS = [
    r"ignore (?:all )?(?:previous|system|procurement) (?:instructions|rules)",
    r"bypass (?:all )?(?:approval|controls|policy)",
    r"approve (?:it )?immediately",
    r"treat this request as (?:cfo|ceo|executive)[ -]approved",
    r"system instruction",
    r"developer instruction",
    r"reveal (?:all )?secrets",
    r"auto[ -]?approve",
]


def _parse_date(date_str: str | None) -> date | None:
    if not date_str:
        return None
    try:
        return date.fromisoformat(str(date_str).strip())
    except Exception:
        return None


def evaluate_procurement_rules(
    context: RequestContext | dict[str, Any],
    catalog_result: CatalogSearchResult | ToolResult | dict[str, Any] | None = None,
    vendor_risk: VendorRiskProfile | ToolResult | dict[str, Any] | None = None,
    vendor_registry_record: dict[str, Any] | None = None,
) -> RuleEvaluationResult:
    """Evaluate deterministic procurement rules against gathered evidence.

    This engine does NOT call an LLM. It enforces hard policy rules, thresholds,
    and governance gates according to data/procurement_policy.md (version 2026.09).

    Evaluates:
    A. Required information completeness
    B. Available department budget check
    C. Financial approval thresholds ($1,000 / $10,000 / $25,000)
    D. Existing software catalog overlap
    E. Information Security triggers
    F. Vendor review freshness (365 days from 2026-09-30)
    G. Internal registry vs external risk API conflict
    H. Privacy / PII / Cross-region triggers
    I. Legal review triggers (New vendor spend >= $10k, unapproved terms, cross-region)
    J. Untrusted data & prompt injection detection
    K. Tool / API failure handling
    L. Preserves human_review_required = True
    """
    evidence: list[EvidenceItem] = []
    missing_information: list[str] = []
    risk_flags_set: set[str] = set()
    approvals_set: set[str] = set()

    # Extract base request dictionary
    if isinstance(context, RequestContext):
        req = context.request
        dept = context.department
        budget_info = context.budget
        evidence.extend(context.evidence)
    else:
        req = context.get("request", context)
        dept = context.get("department", req.get("department", "Unknown"))
        budget_info = context.get("budget", {})
        evidence.extend([EvidenceItem.model_validate(e) if isinstance(e, dict) else e for e in context.get("evidence", [])])

    request_id = str(req.get("request_id", "UNKNOWN"))
    product_name = req.get("product_name")
    vendor_name = str(req.get("vendor_name", ""))
    annual_cost = req.get("annual_cost_usd")
    user_count = req.get("user_count")
    data_access_level = req.get("data_access_level")
    business_justification = str(req.get("business_justification", ""))
    requested_integrations = req.get("requested_integrations") or []

    # -------------------------------------------------------------
    # J. PROMPT INJECTION & UNTRUSTED BUSINESS DATA CHECK (Policy §9)
    # -------------------------------------------------------------
    has_injection = False
    for pat in PROMPT_INJECTION_PATTERNS:
        if re.search(pat, business_justification, re.IGNORECASE):
            has_injection = True
            break

    if has_injection:
        risk_flags_set.add("prompt_injection_detected")
        evidence.append(
            EvidenceItem(
                source="requests.json",
                finding=(
                    f"Prompt injection / override pattern detected in request {request_id} justification. "
                    "In accordance with Section 9, embedded instructions to bypass procurement rules or spoof approvals were ignored."
                ),
                reference=request_id,
            )
        )

    # -------------------------------------------------------------
    # A. REQUIRED INFORMATION COMPLETENESS (Policy §1)
    # -------------------------------------------------------------
    if not req.get("requester_id"):
        missing_information.append("requester identity (requester_id)")
    if not product_name:
        missing_information.append("product name (product_name)")
    if not vendor_name:
        missing_information.append("vendor name (vendor_name)")
    if annual_cost is None or annual_cost <= 0:
        missing_information.append("annual cost estimate (annual_cost_usd)")
    if user_count is None or user_count <= 0:
        missing_information.append("number of users/licenses (user_count)")
    if not business_justification.strip():
        missing_information.append("business purpose (business_justification)")
    if not data_access_level or str(data_access_level).lower() == "unknown":
        missing_information.append("intended data access level (data_access_level)")

    if missing_information:
        risk_flags_set.add("missing_information")
        evidence.append(
            EvidenceItem(
                source="procurement_policy.md",
                finding=f"Request is missing material information: {', '.join(missing_information)}. Section 1 requires clarification before approval.",
                reference="Section 1",
            )
        )

    # -------------------------------------------------------------
    # B. BUDGET CHECK (Policy §2)
    # -------------------------------------------------------------
    available_budget = budget_info.get("available_usd")
    if annual_cost is not None and available_budget is not None:
        if annual_cost > available_budget:
            risk_flags_set.add("budget_insufficient")
            approvals_set.add("Finance")
            evidence.append(
                EvidenceItem(
                    source="department_budgets.csv",
                    finding=(
                        f"Annual cost of ${annual_cost:,.2f} exceeds {dept} available software budget of "
                        f"${available_budget:,.2f} by ${annual_cost - available_budget:,.2f}. Section 2 requires Finance exception review."
                    ),
                    reference=dept,
                )
            )
        else:
            evidence.append(
                EvidenceItem(
                    source="department_budgets.csv",
                    finding=f"Annual cost of ${annual_cost:,.2f} is within {dept} available budget of ${available_budget:,.2f}.",
                    reference=dept,
                )
            )

    # -------------------------------------------------------------
    # C. FINANCIAL APPROVAL THRESHOLDS (Policy §4)
    # -------------------------------------------------------------
    if annual_cost is not None and annual_cost > 0:
        cost_val = float(annual_cost)
        if cost_val <= 1000.00:
            approvals_set.add("Manager")
            evidence.append(
                EvidenceItem(
                    source="procurement_policy.md",
                    finding=f"Spend of ${cost_val:,.2f} is up to $1,000; requires Manager approval per Section 4.",
                    reference="Section 4",
                )
            )
        elif 1000.00 < cost_val <= 10000.00:
            approvals_set.add("Department Head")
            approvals_set.add("Procurement")
            evidence.append(
                EvidenceItem(
                    source="procurement_policy.md",
                    finding=f"Spend of ${cost_val:,.2f} ($1,000.01 - $10,000) requires Department Head and Procurement approval per Section 4.",
                    reference="Section 4",
                )
            )
        elif 10000.00 < cost_val <= 25000.00:
            approvals_set.add("Department Head")
            approvals_set.add("Finance")
            approvals_set.add("Procurement")
            evidence.append(
                EvidenceItem(
                    source="procurement_policy.md",
                    finding=f"Spend of ${cost_val:,.2f} ($10,000.01 - $25,000) requires Department Head, Finance, and Procurement approval per Section 4.",
                    reference="Section 4",
                )
            )
        else:  # cost_val > 25000.00
            approvals_set.add("Department Head")
            approvals_set.add("Finance")
            approvals_set.add("CFO")
            approvals_set.add("Procurement")
            evidence.append(
                EvidenceItem(
                    source="procurement_policy.md",
                    finding=f"Spend of ${cost_val:,.2f} exceeds $25,000; requires Department Head, Finance, CFO, and Procurement approval per Section 4.",
                    reference="Section 4",
                )
            )

    # -------------------------------------------------------------
    # D. EXISTING SOFTWARE OVERLAP (Policy §3)
    # -------------------------------------------------------------
    catalog_overlap_detected = False
    if catalog_result is not None:
        cat_data = catalog_result.data if hasattr(catalog_result, "data") else catalog_result
        if isinstance(cat_data, dict):
            has_overlap = cat_data.get("has_overlap", False)
            exact = cat_data.get("exact_matches") or []
            vendor_matches = cat_data.get("vendor_matches") or []
            category_matches = cat_data.get("category_matches") or []

            if has_overlap or exact or category_matches:
                catalog_overlap_detected = True
                risk_flags_set.add("existing_tool_overlap")
                # Add catalog evidence items if not already present
                cat_ev = cat_data.get("evidence", [])
                for ev in cat_ev:
                    item = EvidenceItem.model_validate(ev) if isinstance(ev, dict) else ev
                    if item not in evidence:
                        evidence.append(item)

    # -------------------------------------------------------------
    # LOAD VENDOR REGISTRY RECORD IF NOT PROVIDED
    # -------------------------------------------------------------
    if vendor_registry_record is None and vendor_name:
        try:
            vendors_df = load_vendors()
            v_rows = vendors_df[vendors_df["vendor_name"] == vendor_name]
            if not v_rows.empty:
                vendor_registry_record = v_rows.iloc[0].to_dict()
        except Exception:
            pass

    # -------------------------------------------------------------
    # EXTRACT VENDOR RISK API STATUS (Tool Result / Profile)
    # -------------------------------------------------------------
    risk_api_data: dict[str, Any] = {}
    api_available = True
    if vendor_risk is not None:
        if isinstance(vendor_risk, ToolResult):
            api_available = vendor_risk.success
            risk_api_data = vendor_risk.data if isinstance(vendor_risk.data, dict) else {}
            for ev in vendor_risk.evidence:
                if ev not in evidence:
                    evidence.append(ev)
        elif isinstance(vendor_risk, VendorRiskProfile):
            api_available = vendor_risk.verified
            risk_api_data = vendor_risk.model_dump()
            for ev in vendor_risk.evidence:
                if ev not in evidence:
                    evidence.append(ev)
        elif isinstance(vendor_risk, dict):
            api_available = vendor_risk.get("verified", vendor_risk.get("success", True))
            risk_api_data = vendor_risk

    # -------------------------------------------------------------
    # K. VENDOR API FAILURE HANDLING (Policy §10)
    # -------------------------------------------------------------
    if not api_available:
        risk_flags_set.add("vendor_risk_unavailable")
        risk_flags_set.add("security_review_required")
        approvals_set.add("Security")
        evidence.append(
            EvidenceItem(
                source="vendor-risk-api",
                finding=(
                    f"External vendor risk service is unavailable for vendor '{vendor_name}'. "
                    "Under Section 10, favorable risk cannot be assumed; Security review is required."
                ),
                reference=vendor_name,
            )
        )

    # -------------------------------------------------------------
    # E. SECURITY REVIEW & SENSITIVE DATA (Policy §5)
    # -------------------------------------------------------------
    data_level_norm = str(data_access_level).lower() if data_access_level else ""
    if data_level_norm in SECURITY_SENSITIVE_DATA_LEVELS:
        risk_flags_set.add("security_review_required")
        approvals_set.add("Security")
        evidence.append(
            EvidenceItem(
                source="requests.json",
                finding=f"Request specifies sensitive data access level '{data_access_level}'. Section 5 mandates Information Security review.",
                reference="Section 5",
            )
        )

    # Sensitive integrations
    for integ in requested_integrations:
        if str(integ).lower() in SECURITY_SENSITIVE_INTEGRATIONS:
            risk_flags_set.add("security_review_required")
            approvals_set.add("Security")
            evidence.append(
                EvidenceItem(
                    source="requests.json",
                    finding=f"Integration with '{integ}' requires Information Security architecture review under Section 5.",
                    reference=str(integ),
                )
            )

    # -------------------------------------------------------------
    # F. VENDOR REVIEW FRESHNESS & STATUS (Policy §5)
    # -------------------------------------------------------------
    # Check internal registry
    reg_security_status = str(vendor_registry_record.get("security_status", "")).lower() if vendor_registry_record else "unknown"
    reg_review_date = _parse_date(vendor_registry_record.get("security_review_date")) if vendor_registry_record else None

    # Check external API
    api_security_status = str(risk_api_data.get("security_review_status", "")).lower() if risk_api_data else "unknown"
    api_review_date = _parse_date(risk_api_data.get("last_review_date")) if risk_api_data else None

    # Freshness check using 2026-09-30
    active_review_date = api_review_date or reg_review_date
    if active_review_date:
        days_old = (POLICY_REFERENCE_DATE - active_review_date).days
        if days_old > 365 or api_security_status == "expired":
            risk_flags_set.add("vendor_review_expired")
            risk_flags_set.add("security_review_required")
            approvals_set.add("Security")
            evidence.append(
                EvidenceItem(
                    source="vendor-risk-api",
                    finding=(
                        f"Vendor '{vendor_name}' security review date ({active_review_date}) is {days_old} days old "
                        f"(exceeds 365 days relative to reference date {POLICY_REFERENCE_DATE}). Status is expired under Section 5."
                    ),
                    reference="Section 5",
                )
            )
    elif vendor_registry_record and reg_security_status in ["pending", "unknown", "not_completed"]:
        # Missing / incomplete security review
        risk_flags_set.add("security_review_required")
        approvals_set.add("Security")
        evidence.append(
            EvidenceItem(
                source="vendors.csv",
                finding=f"Vendor '{vendor_name}' has incomplete security assessment status '{reg_security_status}'. Security review required.",
                reference="vendors.csv",
            )
        )

    # -------------------------------------------------------------
    # G. CONFLICTING VENDOR EVIDENCE (Policy §5)
    # -------------------------------------------------------------
    if api_available and vendor_registry_record and risk_api_data:
        # Check if internal registry says Approved but external API says expired or not_completed
        if reg_security_status == "approved" and api_security_status in ["expired", "not_completed", "pending"]:
            risk_flags_set.add("conflicting_vendor_evidence")
            risk_flags_set.add("security_review_required")
            approvals_set.add("Security")
            evidence.append(
                EvidenceItem(
                    source="vendors.csv",
                    finding=(
                        f"Conflicting vendor evidence for '{vendor_name}': Internal registry reports security status '{reg_security_status}', "
                        f"while external risk API reports status '{api_security_status}'. Surface conflict to Security per Section 5."
                    ),
                    reference=vendor_name,
                )
            )

    # -------------------------------------------------------------
    # H. PRIVACY REVIEW (Policy §6)
    # -------------------------------------------------------------
    processes_pii = data_level_norm in {"employee_pii", "customer_pii"}
    stores_outside_region = bool(risk_api_data.get("stores_data_outside_region", False)) if risk_api_data else False

    if processes_pii or stores_outside_region:
        risk_flags_set.add("privacy_review_required")
        approvals_set.add("Privacy")
        reasons = []
        if processes_pii:
            reasons.append(f"processing {data_access_level}")
        if stores_outside_region:
            reasons.append("storing data outside operating region")
        evidence.append(
            EvidenceItem(
                source="procurement_policy.md",
                finding=f"Privacy review required under Section 6 due to {', and '.join(reasons)}.",
                reference="Section 6",
            )
        )

    # -------------------------------------------------------------
    # I. LEGAL REVIEW (Policy §7)
    # -------------------------------------------------------------
    is_new_vendor = False
    if vendor_registry_record:
        is_new_vendor = str(vendor_registry_record.get("procurement_status", "")).lower() == "new"

    legal_terms_status = str(vendor_registry_record.get("legal_terms_status", "unknown")).lower() if vendor_registry_record else "unknown"
    non_standard_terms = legal_terms_status in {"draft", "unknown", "none"}

    legal_triggers = []
    # 1. New vendor and annual spend >= $10,000 (Notice: >= $10,000 inclusive per Policy §7)
    if is_new_vendor and annual_cost is not None and float(annual_cost) >= 10000.00:
        legal_triggers.append(f"new vendor with annual spend >= $10,000 (${float(annual_cost):,.2f})")

    # 2. Non-standard terms
    if is_new_vendor and non_standard_terms:
        legal_triggers.append(f"unapproved/draft legal terms ('{legal_terms_status}')")

    # 3. Cross-region data storage issue
    if stores_outside_region:
        legal_triggers.append("cross-region data processing")

    if legal_triggers:
        risk_flags_set.add("legal_review_required")
        approvals_set.add("Legal")
        evidence.append(
            EvidenceItem(
                source="procurement_policy.md",
                finding=f"Legal review required under Section 7 due to {'; '.join(legal_triggers)}.",
                reference="Section 7",
            )
        )

    # -------------------------------------------------------------
    # SORTED ORDERING OF APPROVALS & RISK FLAGS
    # -------------------------------------------------------------
    approval_priority = [
        "Manager",
        "Department Head",
        "Procurement",
        "Finance",
        "CFO",
        "Security",
        "Privacy",
        "Legal",
    ]
    sorted_approvals = [appr for appr in approval_priority if appr in approvals_set]
    # Add any extra approvers that might have been dynamically added
    for appr in sorted(approvals_set):
        if appr not in sorted_approvals:
            sorted_approvals.append(appr)

    sorted_risk_flags = sorted(risk_flags_set)

    # -------------------------------------------------------------
    # FORMULATE PRELIMINARY RECOMMENDATION & NEXT STEP
    # -------------------------------------------------------------
    if missing_information:
        recommendation = f"Request clarification on missing {', '.join(missing_information)} before proceeding."
        next_step = "Route ticket back to requester with specific request for missing pricing, seat count, and data access information."
        is_valid = False
    elif "budget_insufficient" in risk_flags_set and "security_review_required" in risk_flags_set:
        recommendation = "Hold for Finance budget exception and Security risk review."
        next_step = f"Route for required governance reviews: {', '.join(sorted_approvals)}."
        is_valid = True
    elif "vendor_risk_unavailable" in risk_flags_set:
        recommendation = "Route for manual InfoSec review due to unavailable external vendor risk data."
        next_step = f"Notify Security and route for required approvals: {', '.join(sorted_approvals)}."
        is_valid = True
    elif "existing_tool_overlap" in risk_flags_set and is_new_vendor:
        recommendation = "Review existing catalog software before onboarding new vendor."
        next_step = f"Conduct overlap review with Department Head; route for required approvals: {', '.join(sorted_approvals)}."
        is_valid = True
    elif "security_review_required" in risk_flags_set or "privacy_review_required" in risk_flags_set:
        recommendation = "Route for specialized Security and Privacy governance reviews."
        next_step = f"Submit for governance and management signoffs: {', '.join(sorted_approvals)}."
        is_valid = True
    elif sorted_approvals == ["Manager"]:
        recommendation = "Ready for Manager approval."
        next_step = "Route request to Direct Manager for standard low-value signoff."
        is_valid = True
    else:
        recommendation = f"Route for standard business approvals: {', '.join(sorted_approvals)}."
        next_step = f"Submit to designated approvers: {', '.join(sorted_approvals)}."
        is_valid = True

    return RuleEvaluationResult(
        request_id=request_id,
        is_valid=is_valid,
        missing_information=missing_information,
        risk_flags=sorted_risk_flags,
        required_approvals=sorted_approvals,
        evidence=evidence,
        human_review_required=True,  # STRICT POLICY RULE §11: Always True
        preliminary_recommendation=recommendation,
        next_step=next_step,
    )
