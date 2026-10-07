from __future__ import annotations

import unittest
from src.tools.procurement_policy import get_procurement_policy
from src.tools.request_context import get_request_context
from src.tools.software_catalog import search_software_catalog
from src.tools.vendor_risk import get_vendor_risk


class ToolLayerTests(unittest.TestCase):
    def test_get_request_context_success(self):
        result = get_request_context("REQ-1001")
        self.assertTrue(result.success)
        self.assertEqual(result.tool_name, "get_request_context")
        data = result.data
        self.assertEqual(data["request"]["product_name"], "SignFlow Add-on")
        self.assertEqual(data["department"], "Finance")
        self.assertEqual(data["requester"]["name"], "Noah Williams")
        self.assertIsNotNone(data["manager"])
        self.assertEqual(data["manager"]["name"], "Priya Shah")
        self.assertEqual(data["budget"]["annual_software_budget_usd"], 90000)
        self.assertEqual(data["budget"]["committed_usd"], 61000)
        self.assertEqual(data["budget"]["available_usd"], 29000)
        self.assertGreaterEqual(len(result.evidence), 2)

    def test_get_request_context_unknown_request(self):
        result = get_request_context("REQ-NONEXISTENT")
        self.assertFalse(result.success)
        self.assertIn("Unknown request_id", result.errors[0])

    def test_search_software_catalog_exact_match(self):
        result = search_software_catalog(product_name="PixelCraft Pro")
        self.assertTrue(result.success)
        data = result.data
        self.assertTrue(data["has_overlap"])
        self.assertGreaterEqual(len(data["exact_matches"]), 1)
        self.assertEqual(data["exact_matches"][0]["software_id"], "SW001")

    def test_search_software_catalog_category_match(self):
        result = search_software_catalog(category="Design & Creative")
        self.assertTrue(result.success)
        data = result.data
        self.assertTrue(data["has_overlap"])
        self.assertGreaterEqual(len(data["category_matches"]), 2)

    def test_search_software_catalog_no_match(self):
        result = search_software_catalog(product_name="QuantumSupercomputerToolXYZ")
        self.assertTrue(result.success)
        data = result.data
        self.assertFalse(data["has_overlap"])
        self.assertEqual(len(data["potential_alternatives"]), 0)

    def test_vendor_risk_success(self):
        result = get_vendor_risk("PixelCraft")
        self.assertTrue(result.success)
        data = result.data
        self.assertTrue(data["verified"])
        self.assertEqual(data["risk_level"], "low")
        self.assertEqual(data["security_review_status"], "approved")
        self.assertEqual(data["last_review_date"], "2026-04-12")

    def test_vendor_risk_404(self):
        result = get_vendor_risk("UnknownVendorDoesNotExist")
        self.assertFalse(result.success)
        data = result.data
        self.assertFalse(data["verified"])
        self.assertEqual(data["status_code"], 404)
        self.assertIn("404", result.errors[0])

    def test_vendor_risk_forced_outage_503(self):
        result = get_vendor_risk("NimbusAI")
        self.assertFalse(result.success)
        data = result.data
        self.assertFalse(data["verified"])
        self.assertEqual(data["status_code"], 503)
        self.assertTrue(any("503" in e for e in result.errors))

    def test_vendor_risk_timeout(self):
        result = get_vendor_risk("TestVendor", simulate_failure="timeout")
        self.assertFalse(result.success)
        data = result.data
        self.assertFalse(data["verified"])
        self.assertTrue(any("timeout" in e.lower() for e in result.errors))

    def test_vendor_risk_connection_failure(self):
        result = get_vendor_risk("TestVendor", simulate_failure="connection")
        self.assertFalse(result.success)
        data = result.data
        self.assertFalse(data["verified"])
        self.assertTrue(any("connection" in e.lower() for e in result.errors))

    def test_vendor_risk_malformed_response(self):
        result = get_vendor_risk("TestVendor", simulate_failure="malformed")
        self.assertFalse(result.success)
        data = result.data
        self.assertFalse(data["verified"])
        self.assertTrue(any("malformed" in e.lower() for e in result.errors))

    def test_get_procurement_policy(self):
        result = get_procurement_policy()
        self.assertTrue(result.success)
        data = result.data
        self.assertEqual(data["version"], "2026.09")
        self.assertEqual(data["reference_date"], "2026-09-30")
        self.assertEqual(len(data["sections"]), 11)
        self.assertEqual(data["sections"][0]["section_number"], 1)
        self.assertEqual(data["sections"][10]["section_number"], 11)


if __name__ == "__main__":
    unittest.main()
