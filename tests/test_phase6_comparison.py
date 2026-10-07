from __future__ import annotations

import json
import unittest
from pathlib import Path

from src.contracts import ProcurementDecision
from src.decision_engine import make_procurement_decision
from src.solution import handle_request
from evals.run_comparison import (
    score_grounding,
    score_business_understanding,
    score_catalog_fit,
    score_governance,
    score_clarification,
)

ROOT = Path(__file__).resolve().parents[1]


class Phase6ComparativeEvaluationTests(unittest.TestCase):
    """Test suite for Phase 6 comparative evaluation harness and invariants."""

    @classmethod
    def setUpClass(cls):
        cases_file = ROOT / "evals" / "qualitative_cases.json"
        cls.cases = json.loads(cases_file.read_text(encoding="utf-8"))

    def test_qualitative_dataset_completeness(self):
        """Verify that at least 15 qualitative cases exist with required schema."""
        self.assertGreaterEqual(len(self.cases), 15)
        case_ids = [c["case_id"] for c in self.cases]
        self.assertEqual(len(case_ids), len(set(case_ids)))
        for case in self.cases:
            self.assertIn("case_id", case)
            self.assertIn("request_id", case)
            self.assertIn("expected", case)
            self.assertTrue(case["expected"].get("human_review_required"))

    def test_deterministic_parity_all_qualitative_cases(self):
        """Verify 100% deterministic parity between Single and Staged across all cases."""
        for case in self.cases:
            req_id = case["request_id"]
            authoritative = make_procurement_decision(req_id)
            single_res = handle_request(req_id, architecture="single")
            staged_res = handle_request(req_id, architecture="staged")

            # Assert deterministic fields match authoritative policy exactly
            self.assertEqual(single_res.recommendation, authoritative.recommendation)
            self.assertEqual(staged_res.recommendation, authoritative.recommendation)

            self.assertEqual(
                set(single_res.required_approvals), set(authoritative.required_approvals)
            )
            self.assertEqual(
                set(staged_res.required_approvals), set(authoritative.required_approvals)
            )

            self.assertEqual(
                set(single_res.risk_flags), set(authoritative.risk_flags)
            )
            self.assertEqual(
                set(staged_res.risk_flags), set(authoritative.risk_flags)
            )

            self.assertEqual(
                set(single_res.missing_information), set(authoritative.missing_information)
            )
            self.assertEqual(
                set(staged_res.missing_information), set(authoritative.missing_information)
            )

            self.assertTrue(single_res.human_review_required)
            self.assertTrue(staged_res.human_review_required)

    def test_llm_call_count_discipline(self):
        """Verify Architecture A executes 1 call and Architecture B executes 2 calls."""
        for req_id in ["REQ-1001", "REQ-1002", "REQ-1003"]:
            single_res = handle_request(req_id, architecture="single")
            staged_res = handle_request(req_id, architecture="staged")

            self.assertIsNotNone(single_res.telemetry)
            self.assertEqual(single_res.telemetry.llm_calls, 1)

            self.assertIsNotNone(staged_res.telemetry)
            self.assertEqual(staged_res.telemetry.llm_calls, 2)
            self.assertEqual(
                staged_res.telemetry.agent_names,
                ["intake_overlap", "governance_triage"],
            )

    def test_tool_call_count_discipline(self):
        """Verify both architectures make exactly 5 shared tool calls."""
        for req_id in ["REQ-1001", "REQ-1005", "REQ-1008"]:
            single_res = handle_request(req_id, architecture="single")
            staged_res = handle_request(req_id, architecture="staged")

            self.assertEqual(single_res.telemetry.tool_calls, 5)
            self.assertEqual(staged_res.telemetry.tool_calls, 5)

    def test_scoring_functions_validity(self):
        """Verify scoring functions produce values in [0, 3]."""
        for case in self.cases[:3]:
            req_id = case["request_id"]
            single_res = handle_request(req_id, architecture="single")
            staged_res = handle_request(req_id, architecture="staged")

            g_a = score_grounding(single_res, case)
            g_b = score_grounding(staged_res, case)
            self.assertIn(g_a, [0, 1, 2, 3])
            self.assertIn(g_b, [0, 1, 2, 3])

            b_a = score_business_understanding(single_res, case, is_staged=False)
            b_b = score_business_understanding(staged_res, case, is_staged=True)
            self.assertIn(b_a, [0, 1, 2, 3])
            self.assertIn(b_b, [0, 1, 2, 3])

            c_a = score_catalog_fit(single_res, case, is_staged=False)
            c_b = score_catalog_fit(staged_res, case, is_staged=True)
            self.assertIn(c_a, [0, 1, 2, 3])
            self.assertIn(c_b, [0, 1, 2, 3])

            gov_a = score_governance(single_res, case, is_staged=False)
            gov_b = score_governance(staged_res, case, is_staged=True)
            self.assertIn(gov_a, [0, 1, 2, 3])
            self.assertIn(gov_b, [0, 1, 2, 3])

            clar_a = score_clarification(single_res, case)
            clar_b = score_clarification(staged_res, case)
            self.assertIn(clar_a, [0, 1, 2, 3])
            self.assertIn(clar_b, [0, 1, 2, 3])


if __name__ == "__main__":
    unittest.main()
