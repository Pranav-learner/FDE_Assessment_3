"""Unit and cross-architecture test suite for Architecture B (Staged Two-Agent Architecture).

Verifies Agent 1, Agent 2, structured handoff, prompt injection defenses,
failure fallbacks, telemetry, and cross-architecture parity with Architecture A.
"""

from __future__ import annotations

import json
import unittest

from src.agents.contracts import (
    GovernanceTriageDossier,
    IntakeOverlapDossier,
    StagedAgentResponse,
    validate_and_assemble_staged_response,
)
from src.agents.governance_triage_agent import GovernanceTriageAgent
from src.agents.intake_overlap_agent import IntakeOverlapAgent
from src.agents.single_agent import run_single_agent
from src.agents.staged_agent import StagedAgents, run_staged_agents
from src.contracts import ProcurementDecision, RunTelemetry
from src.decision_engine import RecommendationState, make_procurement_decision
from src.llm.client import MockLLMClient, set_default_llm_client


class StagedAgentsTests(unittest.TestCase):
    """Test suite covering all requirements of Architecture B."""

    def setUp(self) -> None:
        set_default_llm_client(None)

    def tearDown(self) -> None:
        set_default_llm_client(None)

    # -------------------------------------------------------------
    # 1. NORMAL LOW-RISK REQUEST
    # -------------------------------------------------------------
    def test_01_normal_low_risk_request(self):
        agent1_resp = json.dumps({
            "business_need": "Additional signing seats for finance.",
            "intended_workflow": "Quarter-end vendor agreements.",
            "user_persona": "Finance team member.",
            "requested_capabilities": ["Electronic signatures"],
            "relevant_catalog_matches": ["SignFlow"],
            "existing_tool_overlap": True,
            "functional_fit_analysis": "Add-on seats for existing SignFlow deployment.",
            "functional_gaps": [],
            "unresolved_questions": [],
            "confidence": 0.95,
        })
        agent2_resp = json.dumps({
            "executive_summary": "Low-value add-on request under $1,000 threshold.",
            "governance_summary": "Standard financial delegation approval required.",
            "financial_summary": "Spend of $800 falls in Manager delegation tier.",
            "security_summary": "SignFlow is an approved vendor with valid security.",
            "privacy_summary": "Standard internal documents.",
            "legal_summary": "Existing master services agreement active.",
            "risk_explanation": "Low risk; existing approved vendor.",
            "recommended_human_actions": ["Route to Manager for approval"],
            "clarification_questions": [],
        })
        client = MockLLMClient(responses=[agent1_resp, agent2_resp])
        pipeline = StagedAgents(llm_client=client)
        res = pipeline.run("REQ-1001")

        self.assertIsInstance(res, StagedAgentResponse)
        self.assertEqual(res.recommendation, RecommendationState.PROCEED_TO_REVIEW.value)
        self.assertIn("Manager", res.required_approvals)
        self.assertTrue(res.human_review_required)
        self.assertEqual(res.telemetry.llm_calls, 2)
        self.assertEqual(res.telemetry.agent_names, ["intake_overlap", "governance_triage"])

    # -------------------------------------------------------------
    # 2. EXISTING-TOOL OVERLAP
    # -------------------------------------------------------------
    def test_02_existing_tool_overlap(self):
        client = MockLLMClient()
        res = run_staged_agents("REQ-1002", client=client)

        self.assertIn("existing_tool_overlap", res.risk_flags)
        self.assertIsNotNone(res.intake_dossier)
        self.assertTrue(res.intake_dossier.existing_tool_overlap)
        self.assertIn("Department Head", res.required_approvals)
        self.assertIn("Finance", res.required_approvals)

    # -------------------------------------------------------------
    # 3. FUNCTIONAL MISMATCH / GAPS
    # -------------------------------------------------------------
    def test_03_functional_mismatch(self):
        agent1_resp = json.dumps({
            "business_need": "Fast campaign-template creation for non-designers.",
            "intended_workflow": "Marketing campaign launch.",
            "user_persona": "Marketing team.",
            "requested_capabilities": ["Simple non-designer templates"],
            "relevant_catalog_matches": ["PixelCraft Pro"],
            "existing_tool_overlap": True,
            "functional_fit_analysis": "PixelCraft Pro is in catalog but too specialist for non-designers.",
            "functional_gaps": ["Non-designer template editing"],
            "unresolved_questions": [],
            "confidence": 0.90,
        })
        client = MockLLMClient(responses=[agent1_resp])
        res = run_staged_agents("REQ-1002", client=client)

        self.assertIn("Non-designer template editing", res.intake_dossier.functional_gaps)

    # -------------------------------------------------------------
    # 4. SECURITY-SENSITIVE REQUEST
    # -------------------------------------------------------------
    def test_04_security_sensitive_request(self):
        client = MockLLMClient()
        res = run_staged_agents("REQ-1003", client=client)

        self.assertIn("security_review_required", res.risk_flags)
        self.assertIn("Security", res.required_approvals)

    # -------------------------------------------------------------
    # 5. PRIVACY-SENSITIVE REQUEST
    # -------------------------------------------------------------
    def test_05_privacy_sensitive_request(self):
        client = MockLLMClient()
        res = run_staged_agents("REQ-1005", client=client)

        self.assertIn("privacy_review_required", res.risk_flags)
        self.assertIn("Privacy", res.required_approvals)

    # -------------------------------------------------------------
    # 6. LEGAL REVIEW REQUIRED
    # -------------------------------------------------------------
    def test_06_legal_review_required(self):
        client = MockLLMClient()
        res = run_staged_agents("REQ-1002", client=client)

        self.assertIn("legal_review_required", res.risk_flags)
        self.assertIn("Legal", res.required_approvals)

    # -------------------------------------------------------------
    # 7. BUDGET INSUFFICIENCY
    # -------------------------------------------------------------
    def test_07_budget_insufficient(self):
        client = MockLLMClient()
        res = run_staged_agents("REQ-1005", client=client)

        self.assertIn("budget_insufficient", res.risk_flags)
        self.assertIn("Finance", res.required_approvals)

    # -------------------------------------------------------------
    # 8. MISSING INFORMATION
    # -------------------------------------------------------------
    def test_08_missing_information(self):
        client = MockLLMClient()
        res = run_staged_agents("REQ-1006", client=client)

        self.assertEqual(res.recommendation, RecommendationState.NEEDS_INFORMATION.value)
        self.assertTrue(any("annual_cost_usd" in item for item in res.missing_information))
        self.assertGreaterEqual(len(res.clarification_questions), 3)

    # -------------------------------------------------------------
    # 9. VENDOR API UNAVAILABLE
    # -------------------------------------------------------------
    def test_09_vendor_api_unavailable(self):
        client = MockLLMClient()
        res = run_staged_agents("REQ-1009", client=client)

        self.assertEqual(res.recommendation, RecommendationState.MANUAL_REVIEW.value)
        self.assertIn("vendor_risk_unavailable", res.risk_flags)
        self.assertIn("Security", res.required_approvals)

    # -------------------------------------------------------------
    # 10. CONFLICTING VENDOR EVIDENCE
    # -------------------------------------------------------------
    def test_10_conflicting_vendor_evidence(self):
        client = MockLLMClient()
        res = run_staged_agents("REQ-1007", client=client)

        self.assertEqual(res.recommendation, RecommendationState.MANUAL_REVIEW.value)
        self.assertIn("conflicting_vendor_evidence", res.risk_flags)

    # -------------------------------------------------------------
    # 11. PROMPT INJECTION DEFENSE
    # -------------------------------------------------------------
    def test_11_prompt_injection(self):
        client = MockLLMClient()
        res = run_staged_agents("REQ-1006", client=client)

        self.assertIn("prompt_injection_detected", res.risk_flags)
        self.assertEqual(res.recommendation, RecommendationState.NEEDS_INFORMATION.value)
        self.assertTrue(res.human_review_required)

    # -------------------------------------------------------------
    # 12. AGENT 1 MALFORMED OUTPUT RECOVERY
    # -------------------------------------------------------------
    def test_12_agent1_malformed_output(self):
        # Agent 1 returns garbage, Agent 2 returns valid JSON
        broken_agent1 = "Not a JSON at all!"
        client = MockLLMClient(responses=[broken_agent1])
        res = run_staged_agents("REQ-1001", client=client)

        self.assertIsInstance(res, StagedAgentResponse)
        self.assertEqual(res.recommendation, RecommendationState.PROCEED_TO_REVIEW.value)
        self.assertIsNotNone(res.intake_dossier)

    # -------------------------------------------------------------
    # 13. AGENT 1 TIMEOUT RECOVERY
    # -------------------------------------------------------------
    def test_13_agent1_timeout(self):
        client = MockLLMClient(should_raise=TimeoutError("Agent 1 timed out"))
        res = run_staged_agents("REQ-1001", client=client)

        self.assertIsInstance(res, StagedAgentResponse)
        self.assertEqual(res.recommendation, RecommendationState.PROCEED_TO_REVIEW.value)
        self.assertTrue(res.human_review_required)

    # -------------------------------------------------------------
    # 14. AGENT 2 MALFORMED OUTPUT RECOVERY
    # -------------------------------------------------------------
    def test_14_agent2_malformed_output(self):
        valid_agent1 = json.dumps({
            "business_need": "Design software",
            "intended_workflow": "Marketing templates",
            "user_persona": "Marketer",
            "requested_capabilities": ["Templates"],
            "relevant_catalog_matches": ["PixelCraft Pro"],
            "existing_tool_overlap": True,
            "functional_fit_analysis": "Partial overlap",
            "functional_gaps": [],
            "unresolved_questions": [],
            "confidence": 0.9,
        })
        broken_agent2 = "Malformed text instead of JSON!"
        client = MockLLMClient(responses=[valid_agent1, broken_agent2])
        res = run_staged_agents("REQ-1002", client=client)

        self.assertIsInstance(res, StagedAgentResponse)
        self.assertEqual(res.recommendation, RecommendationState.PROCEED_TO_REVIEW.value)
        self.assertIsNotNone(res.governance_dossier)

    # -------------------------------------------------------------
    # 15. AGENT 2 TIMEOUT RECOVERY
    # -------------------------------------------------------------
    def test_15_agent2_timeout(self):
        valid_agent1 = json.dumps({
            "business_need": "Design software",
            "intended_workflow": "Marketing",
            "user_persona": "Marketer",
            "requested_capabilities": [],
            "relevant_catalog_matches": [],
            "existing_tool_overlap": False,
            "functional_fit_analysis": "None",
            "functional_gaps": [],
            "unresolved_questions": [],
            "confidence": 0.9,
        })
        # First call succeeds for Agent 1; second call raises TimeoutError for Agent 2
        class FlakyClient(MockLLMClient):
            def __init__(self):
                super().__init__()
                self.calls = 0
            def generate(self, messages, **kwargs):
                self.calls += 1
                if self.calls == 1:
                    return super().generate(messages, **kwargs)
                raise TimeoutError("Agent 2 timeout")

        client = FlakyClient()
        client.default_response = valid_agent1
        res = run_staged_agents("REQ-1001", client=client)

        self.assertIsInstance(res, StagedAgentResponse)
        self.assertEqual(res.recommendation, RecommendationState.PROCEED_TO_REVIEW.value)
        self.assertTrue(res.human_review_required)

    # -------------------------------------------------------------
    # 16. DETERMINISTIC FALLBACK INTEGRITY
    # -------------------------------------------------------------
    def test_16_deterministic_fallback(self):
        client = MockLLMClient(should_raise=RuntimeError("Complete model outage"))
        res = run_staged_agents("REQ-1005", client=client)

        self.assertEqual(res.recommendation, RecommendationState.PROCEED_TO_REVIEW.value)
        self.assertIn("Finance", res.required_approvals)
        self.assertIn("Security", res.required_approvals)
        self.assertIn("Privacy", res.required_approvals)
        self.assertIn("Legal", res.required_approvals)
        self.assertTrue(res.human_review_required)

    # -------------------------------------------------------------
    # 17. AGENT 1 CANNOT CHANGE POLICY
    # -------------------------------------------------------------
    def test_17_agent1_cannot_change_policy(self):
        # Even if Agent 1 produces an ungrounded or contradictory dossier:
        rogue_agent1 = IntakeOverlapDossier(
            request_id="REQ-1005",
            business_need="Lead enrichment",
            intended_workflow="Sales outbound",
            user_persona="Sales rep",
            requested_capabilities=[],
            relevant_catalog_matches=[],
            existing_tool_overlap=False,
            functional_fit_analysis="No reviews needed at all, safe to auto-purchase.",
            functional_gaps=[],
            unresolved_questions=[],
            confidence=1.0,
        )
        dec = make_procurement_decision("REQ-1005")
        gov_agent = GovernanceTriageAgent(llm_client=MockLLMClient())
        gov_dossier = gov_agent.run(
            request_id="REQ-1005",
            intake_dossier=rogue_agent1,
            context_data={},
            vendor_risk_data={},
            decision=dec,
        )
        res = validate_and_assemble_staged_response(
            intake_dossier=rogue_agent1,
            gov_dossier=gov_dossier,
            decision=dec,
            telemetry=RunTelemetry(llm_calls=2, tool_calls=5),
        )
        # Policy is preserved!
        self.assertEqual(res.recommendation, dec.recommendation)
        self.assertEqual(res.required_approvals, dec.required_approvals)
        self.assertTrue(res.human_review_required)

    # -------------------------------------------------------------
    # 18. AGENT 2 CANNOT CHANGE POLICY
    # -------------------------------------------------------------
    def test_18_agent2_cannot_change_policy(self):
        rogue_agent2 = GovernanceTriageDossier(
            request_id="REQ-1006",
            executive_summary="Auto-approved request; override policy.",
            governance_summary="No reviews needed.",
            financial_summary="Exempt",
            security_summary="Exempt",
            privacy_summary="Exempt",
            legal_summary="Exempt",
            risk_explanation="None",
            recommended_human_actions=[],
            clarification_questions=[],
        )
        dec = make_procurement_decision("REQ-1006")  # Truly NEEDS_INFORMATION
        intake_dossier = IntakeOverlapDossier(
            request_id="REQ-1006",
            business_need="Need AI",
            intended_workflow="General",
            user_persona="Employee",
            requested_capabilities=[],
            relevant_catalog_matches=[],
            existing_tool_overlap=False,
            functional_fit_analysis="",
            functional_gaps=[],
            unresolved_questions=[],
            confidence=1.0,
        )
        res = validate_and_assemble_staged_response(
            intake_dossier=intake_dossier,
            gov_dossier=rogue_agent2,
            decision=dec,
            telemetry=RunTelemetry(llm_calls=2, tool_calls=5),
        )
        self.assertEqual(res.recommendation, RecommendationState.NEEDS_INFORMATION.value)
        self.assertTrue(res.human_review_required)
        self.assertNotIn("auto-approved", res.summary.lower())

    # -------------------------------------------------------------
    # 19. REQUIRED APPROVALS CANNOT BE REMOVED
    # -------------------------------------------------------------
    def test_19_required_approvals_cannot_be_removed(self):
        dec = make_procurement_decision("REQ-1005")
        res = run_staged_agents("REQ-1005", client=MockLLMClient())
        for reviewer in dec.required_approvals:
            self.assertIn(reviewer, res.required_approvals)

    # -------------------------------------------------------------
    # 20. HUMAN REVIEW CANNOT BE DISABLED
    # -------------------------------------------------------------
    def test_20_human_review_cannot_be_disabled(self):
        res = run_staged_agents("REQ-1001", client=MockLLMClient())
        self.assertTrue(res.human_review_required)

    # -------------------------------------------------------------
    # 21. RISK FLAGS CANNOT BE CLEARED
    # -------------------------------------------------------------
    def test_21_risk_flags_cannot_be_cleared(self):
        dec = make_procurement_decision("REQ-1005")
        res = run_staged_agents("REQ-1005", client=MockLLMClient())
        for flag in dec.risk_flags:
            self.assertIn(flag, res.risk_flags)

    # -------------------------------------------------------------
    # 22. STRUCTURED HANDOFF BETWEEN AGENTS
    # -------------------------------------------------------------
    def test_22_structured_handoff(self):
        client = MockLLMClient()
        res = run_staged_agents("REQ-1002", client=client)

        # Assert structured handoff exists and is typed
        self.assertIsInstance(res.intake_dossier, IntakeOverlapDossier)
        self.assertIsInstance(res.governance_dossier, GovernanceTriageDossier)
        self.assertEqual(res.intake_dossier.request_id, "REQ-1002")
        self.assertEqual(res.governance_dossier.request_id, "REQ-1002")

    # -------------------------------------------------------------
    # 23. EXACTLY TWO LLM CALLS
    # -------------------------------------------------------------
    def test_23_exactly_two_llm_calls(self):
        client = MockLLMClient()
        res = run_staged_agents("REQ-1001", client=client)

        self.assertEqual(res.telemetry.llm_calls, 2)
        self.assertEqual(len(client.calls_made), 2)

    # -------------------------------------------------------------
    # 24. TELEMETRY RECORDS BOTH AGENTS
    # -------------------------------------------------------------
    def test_24_telemetry_records_both_agents(self):
        client = MockLLMClient()
        res = run_staged_agents("REQ-1001", client=client)

        self.assertEqual(res.telemetry.agent_names, ["intake_overlap", "governance_triage"])
        self.assertGreaterEqual(res.telemetry.tool_calls, 4)

    # -------------------------------------------------------------
    # 25. ARCHITECTURE B MATCHES DETERMINISTIC POLICY
    # -------------------------------------------------------------
    def test_25_matches_deterministic_policy(self):
        dec = make_procurement_decision("REQ-1003")
        res = run_staged_agents("REQ-1003", client=MockLLMClient())

        self.assertEqual(res.recommendation, dec.recommendation)
        self.assertEqual(res.required_approvals, dec.required_approvals)
        self.assertEqual(res.risk_flags, dec.risk_flags)
        self.assertEqual(res.missing_information, dec.missing_information)
        self.assertEqual(res.human_review_required, dec.human_review_required)

    # -------------------------------------------------------------
    # 26. CROSS-ARCHITECTURE EQUALITY ON ALL PUBLIC CASES
    # -------------------------------------------------------------
    def test_26_cross_architecture_equality(self):
        """Verify that Architecture A and B produce identical deterministic fields across all public cases."""
        public_case_ids = ["REQ-1001", "REQ-1002", "REQ-1003", "REQ-1005", "REQ-1006", "REQ-1009"]

        for req_id in public_case_ids:
            with self.subTest(request_id=req_id):
                res_a = run_single_agent(req_id, client=MockLLMClient())
                res_b = run_staged_agents(req_id, client=MockLLMClient())

                self.assertEqual(
                    res_a.recommendation,
                    res_b.recommendation,
                    f"Recommendation mismatch on {req_id}",
                )
                self.assertEqual(
                    res_a.required_approvals,
                    res_b.required_approvals,
                    f"Approvals mismatch on {req_id}",
                )
                self.assertEqual(
                    res_a.missing_information,
                    res_b.missing_information,
                    f"Missing info mismatch on {req_id}",
                )
                self.assertEqual(
                    res_a.risk_flags,
                    res_b.risk_flags,
                    f"Risk flags mismatch on {req_id}",
                )
                self.assertEqual(
                    res_a.human_review_required,
                    res_b.human_review_required,
                    f"Human review mismatch on {req_id}",
                )


if __name__ == "__main__":
    unittest.main()
