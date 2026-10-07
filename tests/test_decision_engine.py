from __future__ import annotations

import json
from pathlib import Path
import unittest

from evals.run_public_evals import evaluate
from src.contracts import ProcurementDecision
from src.decision_engine import (
    RecommendationState,
    make_procurement_decision,
    make_procurement_decision_with_trace,
)
from src.tools.contracts import (
    RequestContext,
    ToolResult,
    VendorRiskProfile,
)
from src.tools.rule_engine import evaluate_procurement_rules

ROOT = Path(__file__).resolve().parents[1]


class DecisionEngineTests(unittest.TestCase):
    """Exhaustive test suite for the deterministic procurement decision engine."""

    # -------------------------------------------------------------
    # 1. NORMAL REQUEST (Standard path)
    # -------------------------------------------------------------
    def test_01_normal_request(self):
        decision = make_procurement_decision("REQ-1001")
        self.assertEqual(decision.recommendation, RecommendationState.PROCEED_TO_REVIEW.value)
        self.assertEqual(decision.required_approvals, ["Manager"])
        self.assertEqual(len(decision.missing_information), 0)
        self.assertNotIn("budget_insufficient", decision.risk_flags)
        self.assertTrue(decision.human_review_required)
        self.assertGreaterEqual(len(decision.evidence), 2)
        self.assertIn("Manager", decision.next_step)

    # -------------------------------------------------------------
    # 2. MISSING INFORMATION (Priority 1 Precedence)
    # -------------------------------------------------------------
    def test_02_missing_information(self):
        decision = make_procurement_decision("REQ-1006")
        self.assertEqual(decision.recommendation, RecommendationState.NEEDS_INFORMATION.value)
        self.assertIn("missing_information", decision.risk_flags)
        self.assertGreater(len(decision.missing_information), 0)
        self.assertTrue(any("annual_cost_usd" in item for item in decision.missing_information))
        self.assertTrue(any("user_count" in item for item in decision.missing_information))
        self.assertIn("Request the missing", decision.next_step)
        self.assertTrue(decision.human_review_required)

    # -------------------------------------------------------------
    # 3. BUDGET INSUFFICIENCY
    # -------------------------------------------------------------
    def test_03_budget_insufficiency(self):
        decision = make_procurement_decision("REQ-1005")
        self.assertIn("budget_insufficient", decision.risk_flags)
        self.assertIn("Finance", decision.required_approvals)
        self.assertEqual(decision.recommendation, RecommendationState.PROCEED_TO_REVIEW.value)
        self.assertIn("Finance", decision.next_step)

    # -------------------------------------------------------------
    # 4. LOW-VALUE APPROVAL (<= $1,000)
    # -------------------------------------------------------------
    def test_04_low_value_approval(self):
        decision = make_procurement_decision("REQ-1010")
        self.assertEqual(decision.recommendation, RecommendationState.PROCEED_TO_REVIEW.value)
        self.assertEqual(decision.required_approvals, ["Manager"])
        self.assertNotIn("Finance", decision.required_approvals)
        self.assertNotIn("Department Head", decision.required_approvals)

    # -------------------------------------------------------------
    # 5. $1,000.01 BOUNDARY
    # -------------------------------------------------------------
    def test_05_boundary_1000_01(self):
        # Construct synthetic context at $1,000.01
        ctx = RequestContext(
            request={
                "request_id": "REQ-B1000",
                "requester_id": "E004",
                "product_name": "BoundaryApp",
                "vendor_name": "SignFlow",
                "category": "E-signature",
                "annual_cost_usd": 1000.01,
                "user_count": 5,
                "business_justification": "Boundary test.",
                "data_access_level": "internal_documents",
            },
            requester={"employee_id": "E004", "name": "Noah Williams", "department": "Finance"},
            department="Finance",
            manager={"employee_id": "E006", "name": "Priya Shah"},
            budget={"department": "Finance", "annual_software_budget_usd": 90000, "committed_usd": 61000, "available_usd": 29000},
            evidence=[],
        )
        res = evaluate_procurement_rules(ctx)
        self.assertIn("Department Head", res.required_approvals)
        self.assertIn("Procurement", res.required_approvals)
        self.assertNotIn("Manager", res.required_approvals)
        self.assertNotIn("Finance", res.required_approvals)

    # -------------------------------------------------------------
    # 6. $10,000 BOUNDARY
    # -------------------------------------------------------------
    def test_06_boundary_10000(self):
        ctx = RequestContext(
            request={
                "request_id": "REQ-B10K",
                "requester_id": "E004",
                "product_name": "BoundaryApp10k",
                "vendor_name": "SignFlow",
                "category": "E-signature",
                "annual_cost_usd": 10000.00,
                "user_count": 15,
                "business_justification": "Boundary test 10k.",
                "data_access_level": "internal_documents",
            },
            requester={"employee_id": "E004", "name": "Noah Williams", "department": "Finance"},
            department="Finance",
            manager={"employee_id": "E006", "name": "Priya Shah"},
            budget={"department": "Finance", "annual_software_budget_usd": 90000, "committed_usd": 61000, "available_usd": 29000},
            evidence=[],
        )
        res = evaluate_procurement_rules(ctx)
        self.assertIn("Department Head", res.required_approvals)
        self.assertIn("Procurement", res.required_approvals)
        self.assertNotIn("Finance", res.required_approvals)

    # -------------------------------------------------------------
    # 7. $10,000.01 BOUNDARY
    # -------------------------------------------------------------
    def test_07_boundary_10000_01(self):
        ctx = RequestContext(
            request={
                "request_id": "REQ-B10K01",
                "requester_id": "E004",
                "product_name": "BoundaryApp10k01",
                "vendor_name": "SignFlow",
                "category": "E-signature",
                "annual_cost_usd": 10000.01,
                "user_count": 15,
                "business_justification": "Boundary test 10k.01.",
                "data_access_level": "internal_documents",
            },
            requester={"employee_id": "E004", "name": "Noah Williams", "department": "Finance"},
            department="Finance",
            manager={"employee_id": "E006", "name": "Priya Shah"},
            budget={"department": "Finance", "annual_software_budget_usd": 90000, "committed_usd": 61000, "available_usd": 29000},
            evidence=[],
        )
        res = evaluate_procurement_rules(ctx)
        self.assertIn("Department Head", res.required_approvals)
        self.assertIn("Finance", res.required_approvals)
        self.assertIn("Procurement", res.required_approvals)
        self.assertNotIn("CFO", res.required_approvals)

    # -------------------------------------------------------------
    # 8. $25,000 BOUNDARY
    # -------------------------------------------------------------
    def test_08_boundary_25000(self):
        ctx = RequestContext(
            request={
                "request_id": "REQ-B25K",
                "requester_id": "E004",
                "product_name": "BoundaryApp25k",
                "vendor_name": "SignFlow",
                "category": "E-signature",
                "annual_cost_usd": 25000.00,
                "user_count": 25,
                "business_justification": "Boundary test 25k.",
                "data_access_level": "internal_documents",
            },
            requester={"employee_id": "E004", "name": "Noah Williams", "department": "Finance"},
            department="Finance",
            manager={"employee_id": "E006", "name": "Priya Shah"},
            budget={"department": "Finance", "annual_software_budget_usd": 90000, "committed_usd": 61000, "available_usd": 29000},
            evidence=[],
        )
        res = evaluate_procurement_rules(ctx)
        self.assertIn("Department Head", res.required_approvals)
        self.assertIn("Finance", res.required_approvals)
        self.assertIn("Procurement", res.required_approvals)
        self.assertNotIn("CFO", res.required_approvals)

    # -------------------------------------------------------------
    # 9. $25,000.01 BOUNDARY
    # -------------------------------------------------------------
    def test_09_boundary_25000_01(self):
        ctx = RequestContext(
            request={
                "request_id": "REQ-B25K01",
                "requester_id": "E004",
                "product_name": "BoundaryApp25k01",
                "vendor_name": "SignFlow",
                "category": "E-signature",
                "annual_cost_usd": 25000.01,
                "user_count": 25,
                "business_justification": "Boundary test 25k.01.",
                "data_access_level": "internal_documents",
            },
            requester={"employee_id": "E004", "name": "Noah Williams", "department": "Finance"},
            department="Finance",
            manager={"employee_id": "E006", "name": "Priya Shah"},
            budget={"department": "Finance", "annual_software_budget_usd": 90000, "committed_usd": 61000, "available_usd": 29000},
            evidence=[],
        )
        res = evaluate_procurement_rules(ctx)
        self.assertIn("Department Head", res.required_approvals)
        self.assertIn("Finance", res.required_approvals)
        self.assertIn("CFO", res.required_approvals)
        self.assertIn("Procurement", res.required_approvals)

    # -------------------------------------------------------------
    # 10. SECURITY REVIEW
    # -------------------------------------------------------------
    def test_10_security_review(self):
        decision = make_procurement_decision("REQ-1003")
        self.assertIn("security_review_required", decision.risk_flags)
        self.assertIn("Security", decision.required_approvals)
        self.assertEqual(decision.recommendation, RecommendationState.PROCEED_TO_REVIEW.value)

    # -------------------------------------------------------------
    # 11. PRIVACY REVIEW
    # -------------------------------------------------------------
    def test_11_privacy_review(self):
        decision = make_procurement_decision("REQ-1004")
        self.assertIn("privacy_review_required", decision.risk_flags)
        self.assertIn("Privacy", decision.required_approvals)
        self.assertIn("Security", decision.required_approvals)

    # -------------------------------------------------------------
    # 12. LEGAL REVIEW
    # -------------------------------------------------------------
    def test_12_legal_review(self):
        decision = make_procurement_decision("REQ-1002")
        self.assertIn("legal_review_required", decision.risk_flags)
        self.assertIn("Legal", decision.required_approvals)

    # -------------------------------------------------------------
    # 13. EXISTING SOFTWARE OVERLAP
    # -------------------------------------------------------------
    def test_13_existing_software_overlap(self):
        decision = make_procurement_decision("REQ-1002")
        self.assertIn("existing_tool_overlap", decision.risk_flags)
        # Verify not automatically rejected:
        self.assertNotEqual(decision.recommendation, "REJECTED")
        self.assertEqual(decision.recommendation, RecommendationState.PROCEED_TO_REVIEW.value)

    # -------------------------------------------------------------
    # 14. EXPIRED VENDOR REVIEW (> 365 Days)
    # -------------------------------------------------------------
    def test_14_expired_vendor_review(self):
        decision = make_procurement_decision("REQ-1007")
        self.assertIn("vendor_review_expired", decision.risk_flags)
        self.assertIn("Security", decision.required_approvals)

    # -------------------------------------------------------------
    # 15. CONFLICTING VENDOR EVIDENCE
    # -------------------------------------------------------------
    def test_15_conflicting_vendor_evidence(self):
        # REQ-1007 has SignalWatch: Registry says Approved, Risk API says expired
        result = make_procurement_decision_with_trace("REQ-1007")
        self.assertIn("conflicting_vendor_evidence", result.decision.risk_flags)
        self.assertEqual(result.state, RecommendationState.MANUAL_REVIEW)

    # -------------------------------------------------------------
    # 16. VENDOR API UNAVAILABLE (Priority 2 Precedence)
    # -------------------------------------------------------------
    def test_16_vendor_api_unavailable(self):
        decision = make_procurement_decision("REQ-1009")
        self.assertEqual(decision.recommendation, RecommendationState.MANUAL_REVIEW.value)
        self.assertIn("vendor_risk_unavailable", decision.risk_flags)
        self.assertIn("security_review_required", decision.risk_flags)
        self.assertIn("Security", decision.required_approvals)
        self.assertIn("manual risk review", decision.next_step.lower())

    # -------------------------------------------------------------
    # 17. PROMPT INJECTION
    # -------------------------------------------------------------
    def test_17_prompt_injection(self):
        decision = make_procurement_decision("REQ-1006")
        self.assertIn("prompt_injection_detected", decision.risk_flags)
        # Decision must NOT be approved:
        self.assertNotEqual(decision.recommendation, "APPROVED")
        self.assertTrue(decision.human_review_required)

    # -------------------------------------------------------------
    # 18. MULTIPLE SIMULTANEOUS RISKS
    # -------------------------------------------------------------
    def test_18_multiple_simultaneous_risks(self):
        # REQ-1005 has budget_insufficient + security + privacy + legal
        decision = make_procurement_decision("REQ-1005")
        self.assertIn("budget_insufficient", decision.risk_flags)
        self.assertIn("security_review_required", decision.risk_flags)
        self.assertIn("privacy_review_required", decision.risk_flags)
        self.assertIn("legal_review_required", decision.risk_flags)

    # -------------------------------------------------------------
    # 19. MULTIPLE REQUIRED APPROVALS
    # -------------------------------------------------------------
    def test_19_multiple_required_approvals(self):
        decision = make_procurement_decision("REQ-1005")
        expected_subset = {"Department Head", "Procurement", "Finance", "Security", "Privacy", "Legal"}
        for approver in expected_subset:
            self.assertIn(approver, decision.required_approvals)

    # -------------------------------------------------------------
    # 20. HUMAN REVIEW ALWAYS TRUE & NO AUTONOMOUS PURCHASE
    # -------------------------------------------------------------
    def test_20_human_review_always_true(self):
        for rid in ["REQ-1001", "REQ-1002", "REQ-1003", "REQ-1004", "REQ-1005", "REQ-1006", "REQ-1007", "REQ-1008", "REQ-1009", "REQ-1010"]:
            decision = make_procurement_decision(rid)
            self.assertTrue(decision.human_review_required)
            self.assertNotIn(decision.recommendation, ["APPROVED", "AUTO_APPROVED", "PURCHASED", "PURCHASE_NOW"])

    # -------------------------------------------------------------
    # 21. PUBLIC CASES VERIFICATION (PUB-01 to PUB-06)
    # -------------------------------------------------------------
    def test_21_all_public_eval_cases(self):
        cases = json.loads((ROOT / "evals" / "public_cases.json").read_text(encoding="utf-8"))
        for case in cases:
            decision = make_procurement_decision(case["request_id"])
            failures = evaluate(decision, case["expectations"])
            self.assertEqual(
                failures,
                [],
                f"Public eval failed on {case['case_id']} ({case['request_id']}): {failures}",
            )


if __name__ == "__main__":
    unittest.main()
