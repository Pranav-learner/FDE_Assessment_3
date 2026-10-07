from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from mock_api.app import app
from src.contracts import ProcurementDecision
from src.decision_engine import make_procurement_decision
from src.solution import handle_request

ROOT = Path(__file__).resolve().parents[1]


class EndToEndSystemTests(unittest.TestCase):
    """End-to-End integration tests for production runtime and interfaces."""

    def test_e2e_architecture_a_pipeline(self):
        """Test full Architecture A pipeline from intake to validated response."""
        for req_id in ["REQ-1001", "REQ-1002", "REQ-1005"]:
            authoritative = make_procurement_decision(req_id)
            decision = handle_request(req_id, architecture="single")

            self.assertIsInstance(decision, ProcurementDecision)
            self.assertEqual(decision.request_id, req_id)
            self.assertEqual(decision.recommendation, authoritative.recommendation)
            self.assertEqual(set(decision.required_approvals), set(authoritative.required_approvals))
            self.assertEqual(set(decision.risk_flags), set(authoritative.risk_flags))
            self.assertEqual(set(decision.missing_information), set(authoritative.missing_information))
            self.assertTrue(decision.human_review_required)
            self.assertGreaterEqual(len(decision.evidence), 3)

            # Telemetry verification
            self.assertIsNotNone(decision.telemetry)
            self.assertEqual(decision.telemetry.llm_calls, 1)
            self.assertEqual(decision.telemetry.tool_calls, 5)

    def test_e2e_architecture_b_pipeline(self):
        """Test full Architecture B staged pipeline with structured dossiers."""
        for req_id in ["REQ-1001", "REQ-1003", "REQ-1008"]:
            authoritative = make_procurement_decision(req_id)
            decision = handle_request(req_id, architecture="staged")

            self.assertIsInstance(decision, ProcurementDecision)
            self.assertEqual(decision.request_id, req_id)
            self.assertEqual(decision.recommendation, authoritative.recommendation)
            self.assertEqual(set(decision.required_approvals), set(authoritative.required_approvals))
            self.assertEqual(set(decision.risk_flags), set(authoritative.risk_flags))
            self.assertTrue(decision.human_review_required)

            # Verify structured dossiers are present
            self.assertTrue(hasattr(decision, "intake_dossier"))
            self.assertTrue(hasattr(decision, "governance_dossier"))
            self.assertIsNotNone(decision.intake_dossier)
            self.assertIsNotNone(decision.governance_dossier)

            # Telemetry verification
            self.assertIsNotNone(decision.telemetry)
            self.assertEqual(decision.telemetry.llm_calls, 2)
            self.assertEqual(decision.telemetry.tool_calls, 5)
            self.assertEqual(
                decision.telemetry.agent_names,
                ["intake_overlap", "governance_triage"],
            )

    def test_e2e_cli_human_report(self):
        """Test CLI execution produces clean human-readable report."""
        cmd = [sys.executable, str(ROOT / "app.py"), "--request-id", "REQ-1001"]
        proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=15)
        self.assertEqual(proc.returncode, 0)
        self.assertIn("AI PROCUREMENT REQUEST COPILOT", proc.stdout)
        self.assertIn("RECOMMENDATION:", proc.stdout)
        self.assertIn("HUMAN REVIEW REQUIRED:  YES", proc.stdout)
        self.assertIn("Manager", proc.stdout)

    def test_e2e_cli_json_mode(self):
        """Test CLI execution in --json mode produces valid machine-readable JSON."""
        cmd = [sys.executable, str(ROOT / "app.py"), "--request-id", "REQ-1002", "--json"]
        proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=15)
        self.assertEqual(proc.returncode, 0)

        # Parse JSON
        data = json.loads(proc.stdout)
        self.assertEqual(data["request_id"], "REQ-1002")
        self.assertTrue(data["human_review_required"])
        self.assertIn("Department Head", data["required_approvals"])
        self.assertIn("Finance", data["required_approvals"])
        self.assertIn("Security", data["required_approvals"])

    def test_e2e_cli_list_command(self):
        """Test CLI --list command prints catalog of requests."""
        cmd = [sys.executable, str(ROOT / "app.py"), "--list"]
        proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=10)
        self.assertEqual(proc.returncode, 0)
        self.assertIn("REQ-1001", proc.stdout)
        self.assertIn("REQ-1002", proc.stdout)

    def test_e2e_http_api_endpoints(self):
        """Test HTTP API /health, /ready, and /procurement/evaluate endpoints."""
        client = TestClient(app)

        # Health
        res_h = client.get("/health")
        self.assertEqual(res_h.status_code, 200)
        self.assertEqual(res_h.json(), {"status": "ok"})

        # Ready
        res_r = client.get("/ready")
        self.assertEqual(res_r.status_code, 200)
        self.assertEqual(res_r.json()["status"], "ready")

        # Evaluate Architecture A
        res_eval_a = client.post(
            "/procurement/evaluate",
            json={"request_id": "REQ-1001", "architecture": "single"},
        )
        self.assertEqual(res_eval_a.status_code, 200)
        payload_a = res_eval_a.json()
        self.assertEqual(payload_a["request_id"], "REQ-1001")
        self.assertTrue(payload_a["human_review_required"])
        self.assertEqual(payload_a["telemetry"]["llm_calls"], 1)

        # Evaluate Architecture B
        res_eval_b = client.post(
            "/procurement/evaluate",
            json={"request_id": "REQ-1001", "architecture": "staged"},
        )
        self.assertEqual(res_eval_b.status_code, 200)
        payload_b = res_eval_b.json()
        self.assertEqual(payload_b["request_id"], "REQ-1001")
        self.assertTrue(payload_b["human_review_required"])
        self.assertEqual(payload_b["telemetry"]["llm_calls"], 2)

        # Resilient handling for unknown request ID (returns NEEDS_INFORMATION per Phase 3 engine)
        res_unknown = client.post(
            "/procurement/evaluate",
            json={"request_id": "REQ-9999", "architecture": "single"},
        )
        self.assertEqual(res_unknown.status_code, 200)
        self.assertEqual(res_unknown.json()["recommendation"], "NEEDS_INFORMATION")
        self.assertTrue(res_unknown.json()["human_review_required"])

        # 400 for invalid request_id format
        res_400 = client.post(
            "/procurement/evaluate",
            json={"request_id": "../../etc/passwd", "architecture": "single"},
        )
        self.assertEqual(res_400.status_code, 400)


if __name__ == "__main__":
    unittest.main()
