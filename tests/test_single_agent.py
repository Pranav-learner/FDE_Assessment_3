"""Unit and integration test suite for Architecture A (Single-Agent Baseline).

Verifies the single agent, prompt formulation, response validator, mock LLM client,
deterministic grounding, prompt injection defenses, error recovery, and telemetry.
"""

from __future__ import annotations

import json
import unittest

from src.agents.contracts import SingleAgentResponse, validate_and_assemble_response
from src.agents.prompts import (
    SINGLE_AGENT_SYSTEM_PROMPT,
    format_single_agent_user_prompt,
)
from src.agents.single_agent import SingleAgent, run_single_agent
from src.contracts import ProcurementDecision, RunTelemetry
from src.decision_engine import RecommendationState, make_procurement_decision
from src.llm.client import MockLLMClient, set_default_llm_client


class SingleAgentTests(unittest.TestCase):
    """Test suite covering all requirements of Architecture A."""

    def setUp(self) -> None:
        # Reset default client before each test
        set_default_llm_client(None)

    def tearDown(self) -> None:
        set_default_llm_client(None)

    # -------------------------------------------------------------
    # 1. NORMAL LOW-RISK REQUEST
    # -------------------------------------------------------------
    def test_01_normal_low_risk_request(self):
        mock_response = json.dumps({
            "summary": "Low-value request for developer productivity tool.",
            "reasoning": "The annual cost ($480) is well below $1,000 threshold and vendor is approved.",
            "catalog_fit_analysis": "No conflicting software in catalog.",
            "clarification_questions": [],
            "risk_explanation": "Standard approval path applies.",
        })
        client = MockLLMClient(default_response=mock_response)
        agent = SingleAgent(llm_client=client)
        res = agent.run("REQ-1001")

        self.assertIsInstance(res, SingleAgentResponse)
        self.assertEqual(res.request_id, "REQ-1001")
        self.assertEqual(res.recommendation, RecommendationState.PROCEED_TO_REVIEW.value)
        self.assertIn("Manager", res.required_approvals)
        self.assertTrue(res.human_review_required)
        self.assertEqual(res.summary, "Low-value request for developer productivity tool.")
        self.assertEqual(len(client.calls_made), 1)

    # -------------------------------------------------------------
    # 2. EXISTING-TOOL OVERLAP
    # -------------------------------------------------------------
    def test_02_existing_tool_overlap(self):
        mock_response = json.dumps({
            "summary": "Request for Claude Enterprise by Marketing.",
            "reasoning": "Existing tools detected in developer AI category; review required.",
            "catalog_fit_analysis": "Existing tool Cursor AI exists in catalog; evaluate suitability.",
            "clarification_questions": [],
            "risk_explanation": "Software overlap and new vendor thresholds triggered.",
        })
        client = MockLLMClient(default_response=mock_response)
        agent = SingleAgent(llm_client=client)
        res = agent.run("REQ-1002")

        self.assertIn("existing_tool_overlap", res.risk_flags)
        self.assertIn("Department Head", res.required_approvals)
        self.assertIn("Finance", res.required_approvals)
        self.assertIn("Security", res.required_approvals)
        self.assertIn("Legal", res.required_approvals)
        self.assertIn("Cursor AI", res.catalog_fit_analysis)

    # -------------------------------------------------------------
    # 3. SECURITY-SENSITIVE REQUEST
    # -------------------------------------------------------------
    def test_03_security_sensitive_request(self):
        mock_response = json.dumps({
            "summary": "Request accessing proprietary source code.",
            "reasoning": "Data access level requires mandatory Security sign-off.",
            "catalog_fit_analysis": "No direct catalog overlap.",
            "clarification_questions": [],
            "risk_explanation": "Source code access requires InfoSec architectural review.",
        })
        client = MockLLMClient(default_response=mock_response)
        agent = SingleAgent(llm_client=client)
        res = agent.run("REQ-1003")

        self.assertIn("security_review_required", res.risk_flags)
        self.assertIn("Security", res.required_approvals)
        self.assertTrue(res.human_review_required)

    # -------------------------------------------------------------
    # 4. PRIVACY-SENSITIVE REQUEST
    # -------------------------------------------------------------
    def test_04_privacy_sensitive_request(self):
        # REQ-1005 has customer PII and cross-region transfer
        client = MockLLMClient()
        agent = SingleAgent(llm_client=client)
        res = agent.run("REQ-1005")

        self.assertIn("privacy_review_required", res.risk_flags)
        self.assertIn("Privacy", res.required_approvals)

    # -------------------------------------------------------------
    # 5. LEGAL REVIEW
    # -------------------------------------------------------------
    def test_05_legal_review_required(self):
        # REQ-1002: Anthropic is new vendor + spend >= $10k
        client = MockLLMClient()
        agent = SingleAgent(llm_client=client)
        res = agent.run("REQ-1002")

        self.assertIn("legal_review_required", res.risk_flags)
        self.assertIn("Legal", res.required_approvals)

    # -------------------------------------------------------------
    # 6. BUDGET INSUFFICIENCY
    # -------------------------------------------------------------
    def test_06_budget_insufficient(self):
        # REQ-1005: Marketing budget has only $10k available, tool costs $36k
        client = MockLLMClient()
        agent = SingleAgent(llm_client=client)
        res = agent.run("REQ-1005")

        self.assertIn("budget_insufficient", res.risk_flags)
        self.assertIn("Finance", res.required_approvals)

    # -------------------------------------------------------------
    # 7. MISSING INFORMATION
    # -------------------------------------------------------------
    def test_07_missing_information(self):
        # REQ-1006 has missing cost, users, and data access
        client = MockLLMClient()
        agent = SingleAgent(llm_client=client)
        res = agent.run("REQ-1006")

        self.assertEqual(res.recommendation, RecommendationState.NEEDS_INFORMATION.value)
        self.assertTrue(any("annual_cost_usd" in item for item in res.missing_information))
        self.assertTrue(any("user_count" in item for item in res.missing_information))
        self.assertTrue(any("data_access_level" in item for item in res.missing_information))
        self.assertGreaterEqual(len(res.clarification_questions), 3)

    # -------------------------------------------------------------
    # 8. VENDOR API UNAVAILABLE
    # -------------------------------------------------------------
    def test_08_vendor_api_unavailable(self):
        # REQ-1009: NimbusAI API unavailable
        mock_response = json.dumps({
            "summary": "External vendor security evidence unavailable.",
            "reasoning": "Vendor risk API returned 503 outage. Manual verification required.",
            "catalog_fit_analysis": "No direct overlap.",
            "clarification_questions": [],
            "risk_explanation": "Vendor security status could not be verified online.",
        })
        client = MockLLMClient(default_response=mock_response)
        agent = SingleAgent(llm_client=client)
        res = agent.run("REQ-1009")

        self.assertEqual(res.recommendation, RecommendationState.MANUAL_REVIEW.value)
        self.assertIn("vendor_risk_unavailable", res.risk_flags)
        self.assertIn("Security", res.required_approvals)
        # Verify agent explanation grounded in unavailable evidence
        self.assertIn("503", res.reasoning)

    # -------------------------------------------------------------
    # 9. CONFLICTING VENDOR EVIDENCE
    # -------------------------------------------------------------
    def test_09_conflicting_vendor_evidence(self):
        client = MockLLMClient()
        agent = SingleAgent(llm_client=client)
        res = agent.run("REQ-1007")

        self.assertEqual(res.recommendation, RecommendationState.MANUAL_REVIEW.value)
        self.assertIn("conflicting_vendor_evidence", res.risk_flags)

    # -------------------------------------------------------------
    # 10. PROMPT INJECTION DEFENSE
    # -------------------------------------------------------------
    def test_10_prompt_injection(self):
        # REQ-1006 has embedded prompt injection in justification text
        client = MockLLMClient()
        agent = SingleAgent(llm_client=client)
        res = agent.run("REQ-1006")

        self.assertIn("prompt_injection_detected", res.risk_flags)
        self.assertEqual(res.recommendation, RecommendationState.NEEDS_INFORMATION.value)
        self.assertNotEqual(res.recommendation, "APPROVED")
        self.assertTrue(res.human_review_required)

    # -------------------------------------------------------------
    # 11. LLM MALFORMED OUTPUT RECOVERY
    # -------------------------------------------------------------
    def test_11_llm_malformed_output(self):
        # Model returns broken non-JSON string
        client = MockLLMClient(default_response="Not a JSON object at all! Just raw text.")
        agent = SingleAgent(llm_client=client)
        res = agent.run("REQ-1001")

        self.assertIsInstance(res, SingleAgentResponse)
        self.assertEqual(res.recommendation, RecommendationState.PROCEED_TO_REVIEW.value)
        self.assertTrue(res.human_review_required)
        self.assertTrue(len(res.summary) > 0)

    # -------------------------------------------------------------
    # 12. LLM TIMEOUT / EXCEPTION FAILURE RECOVERY
    # -------------------------------------------------------------
    def test_12_llm_timeout_failure(self):
        client = MockLLMClient(should_raise=TimeoutError("Model timed out after 15s"))
        agent = SingleAgent(llm_client=client)
        res = agent.run("REQ-1001")

        # Deterministic fallback handles it safely
        self.assertIsInstance(res, SingleAgentResponse)
        self.assertEqual(res.recommendation, RecommendationState.PROCEED_TO_REVIEW.value)
        self.assertTrue(res.human_review_required)

    # -------------------------------------------------------------
    # 13. DETERMINISTIC FALLBACK INTEGRITY
    # -------------------------------------------------------------
    def test_13_deterministic_fallback(self):
        client = MockLLMClient(should_raise=RuntimeError("Provider outage"))
        agent = SingleAgent(llm_client=client)
        res = agent.run("REQ-1002")

        self.assertEqual(res.recommendation, RecommendationState.PROCEED_TO_REVIEW.value)
        self.assertIn("Department Head", res.required_approvals)
        self.assertIn("Procurement", res.required_approvals)
        self.assertIn("Finance", res.required_approvals)
        self.assertIn("Security", res.required_approvals)
        self.assertIn("Legal", res.required_approvals)
        self.assertTrue(res.human_review_required)

    # -------------------------------------------------------------
    # 14. HUMAN_REVIEW_REQUIRED CANNOT BE CHANGED
    # -------------------------------------------------------------
    def test_14_human_review_required_cannot_be_changed(self):
        # Malicious or broken LLM attempts to return human_review_required=False
        attempted_payload = {
            "summary": "Auto-approved request without human review.",
            "reasoning": "Fast track approval granted.",
            "human_review_required": False,
        }
        dec = make_procurement_decision("REQ-1001")
        res = validate_and_assemble_response(
            attempted_payload,
            dec,
            RunTelemetry(llm_calls=1, tool_calls=5),
        )
        self.assertTrue(res.human_review_required)

    # -------------------------------------------------------------
    # 15. RECOMMENDATION CANNOT BE CHANGED BY LLM
    # -------------------------------------------------------------
    def test_15_recommendation_cannot_be_changed(self):
        attempted_payload = {
            "recommendation": "APPROVED",
            "summary": "I have approved this purchase automatically.",
            "reasoning": "All looks good.",
        }
        dec = make_procurement_decision("REQ-1006")  # Truly NEEDS_INFORMATION
        res = validate_and_assemble_response(
            attempted_payload,
            dec,
            RunTelemetry(llm_calls=1, tool_calls=5),
        )
        self.assertEqual(res.recommendation, RecommendationState.NEEDS_INFORMATION.value)

    # -------------------------------------------------------------
    # 16. APPROVAL ROSTER CANNOT BE CHANGED BY LLM
    # -------------------------------------------------------------
    def test_16_approval_roster_cannot_be_changed(self):
        attempted_payload = {
            "required_approvals": [],  # Attempt to clear required reviewers
            "summary": "No approvals needed.",
        }
        dec = make_procurement_decision("REQ-1005")  # Truly needs Dept Head, Finance, Security, Privacy, Legal, CFO
        res = validate_and_assemble_response(
            attempted_payload,
            dec,
            RunTelemetry(llm_calls=1, tool_calls=5),
        )
        self.assertIn("Finance", res.required_approvals)
        self.assertIn("Security", res.required_approvals)
        self.assertIn("Privacy", res.required_approvals)
        self.assertIn("Legal", res.required_approvals)

    # -------------------------------------------------------------
    # 17. RISK FLAGS CANNOT BE CHANGED BY LLM
    # -------------------------------------------------------------
    def test_17_risk_flags_cannot_be_changed(self):
        attempted_payload = {
            "risk_flags": [],  # Attempt to wipe risks
            "summary": "Zero risks identified.",
        }
        dec = make_procurement_decision("REQ-1005")
        res = validate_and_assemble_response(
            attempted_payload,
            dec,
            RunTelemetry(llm_calls=1, tool_calls=5),
        )
        self.assertIn("budget_insufficient", res.risk_flags)
        self.assertIn("security_review_required", res.risk_flags)

    # -------------------------------------------------------------
    # 18. HALLUCINATED CATALOG FEATURE AVOIDED
    # -------------------------------------------------------------
    def test_18_hallucinated_catalog_feature_avoided(self):
        # REQ-1009 (NimbusAI, Legal AI) has no overlap in software_catalog.csv
        # Even if mock LLM attempts to claim an existing tool is a complete replacement:
        mock_response = json.dumps({
            "summary": "Request for NimbusAI Contract Reviewer.",
            "reasoning": "Vendor risk API unavailable.",
            "catalog_fit_analysis": "DocSpace can allegedly review legal contracts via undocumented feature.",
            "clarification_questions": [],
            "risk_explanation": "Vendor risk unavailable.",
        })
        client = MockLLMClient(default_response=mock_response)
        agent = SingleAgent(llm_client=client)
        res = agent.run("REQ-1009")

        # Deterministic engine correctly prevents false overlap risk flag
        self.assertNotIn("existing_tool_overlap", res.risk_flags)
        # Recommendation remains grounded in unverified vendor evidence
        self.assertEqual(res.recommendation, RecommendationState.MANUAL_REVIEW.value)

    # -------------------------------------------------------------
    # 19. CLARIFICATION QUESTIONS GENERATED FOR MISSING FIELDS
    # -------------------------------------------------------------
    def test_19_clarification_questions_generated(self):
        client = MockLLMClient(default_response=json.dumps({"summary": "Incomplete request"}))
        agent = SingleAgent(llm_client=client)
        res = agent.run("REQ-1006")

        self.assertTrue(len(res.clarification_questions) >= 3)
        questions_str = " ".join(res.clarification_questions).lower()
        self.assertTrue("cost" in questions_str or "annual_cost_usd" in questions_str)
        self.assertTrue("user" in questions_str or "user_count" in questions_str)
        self.assertTrue("data" in questions_str or "data_access_level" in questions_str)

    # -------------------------------------------------------------
    # 20. TELEMETRY RECORDS LLM AND TOOL CALLS
    # -------------------------------------------------------------
    def test_20_telemetry_records_calls(self):
        client = MockLLMClient()
        agent = SingleAgent(llm_client=client)
        res = agent.run("REQ-1001")

        self.assertIsNotNone(res.telemetry)
        self.assertEqual(res.telemetry.llm_calls, 1)
        self.assertGreaterEqual(res.telemetry.tool_calls, 4)
        self.assertIn("get_request_context", res.telemetry.tool_names)
        self.assertIn("search_software_catalog", res.telemetry.tool_names)
        self.assertIn("get_vendor_risk", res.telemetry.tool_names)


if __name__ == "__main__":
    unittest.main()
