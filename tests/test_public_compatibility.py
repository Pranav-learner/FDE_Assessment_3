from __future__ import annotations

import json
from pathlib import Path
import unittest

from evals.run_public_evals import evaluate
from src.contracts import ProcurementDecision
from src.tools.procurement_policy import get_procurement_policy
from src.tools.request_context import get_request_context
from src.tools.rule_engine import evaluate_procurement_rules
from src.tools.software_catalog import search_software_catalog
from src.tools.vendor_risk import get_vendor_risk

ROOT = Path(__file__).resolve().parents[1]


class PublicCasesDeterministicCompatibilityTest(unittest.TestCase):
    """Confirm the deterministic layer produces the evidence, risk flags, and approvals

    required by all 6 public evaluation cases, without calling an LLM or hardcoding IDs.
    """

    def test_all_public_cases_meet_minimum_expectations(self):
        cases = json.loads((ROOT / "evals" / "public_cases.json").read_text(encoding="utf-8"))

        for case in cases:
            case_id = case["case_id"]
            req_id = case["request_id"]

            # 1. Gather context
            ctx_res = get_request_context(req_id)
            self.assertTrue(ctx_res.success, f"[{case_id}] Failed to get request context")
            ctx_data = ctx_res.data
            req = ctx_data["request"]

            # 2. Search catalog
            cat_res = search_software_catalog(
                product_name=req.get("product_name"),
                vendor_name=req.get("vendor_name"),
                category=req.get("category"),
            )

            # 3. Query vendor risk
            risk_res = get_vendor_risk(req.get("vendor_name", ""))

            # 4. Evaluate rules deterministically
            rule_res = evaluate_procurement_rules(
                context=ctx_data,
                catalog_result=cat_res,
                vendor_risk=risk_res,
            )

            # Convert to ProcurementDecision
            decision = ProcurementDecision(
                request_id=req_id,
                recommendation=rule_res.preliminary_recommendation,
                evidence=rule_res.evidence,
                required_approvals=rule_res.required_approvals,
                missing_information=rule_res.missing_information,
                risk_flags=rule_res.risk_flags,
                next_step=rule_res.next_step,
                human_review_required=rule_res.human_review_required,
            )

            # 5. Evaluate with evals runner logic
            failures = evaluate(decision, case["expectations"])
            self.assertEqual(
                failures,
                [],
                f"[{case_id} - {req_id}] Public evaluation expectations failed: {failures}",
            )


if __name__ == "__main__":
    unittest.main()
