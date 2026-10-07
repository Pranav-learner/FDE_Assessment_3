# 13. Phase 2 Test Plan & Verification Report: AI Procurement Request Copilot

**Document Version:** 1.0.0  
**Phase:** Phase 2 (Data Foundation, Tool Contracts & Rule Engine)  
**Author:** Forward Deployed Engineering (FDE)

---

## 1. Test Strategy Overview

Phase 2 focuses strictly on testing the **non-LLM foundation**: verifying that tools gather accurate evidence, handle failures gracefully, and apply deterministic rules without reliance on probabilistic AI inference.

The Phase 2 test suite consists of three distinct test modules in `tests/`:
1. **`tests/test_tools.py`**: Validates the tool layer (`get_request_context`, `search_software_catalog`, `get_vendor_risk`, `get_procurement_policy`).
2. **`tests/test_deterministic_engine.py`**: Validates all deterministic policy rules (completeness, budget math, boundaries, security, freshness, privacy, legal, outages, prompt injection).
3. **`tests/test_public_compatibility.py`**: Validates compatibility across all six public evaluation cases (`PUB-01` through `PUB-06`).
4. **Starter Pack Integrity Tests (`test_data_integrity.py`, `test_mock_api.py`)**: Validates dataset schemas, foreign keys, and mock endpoints.

---

## 2. Test Matrix Coverage

| Test Class | Test Method | Target Behavior | Expected Result |
|---|---|---|:---:|
| **ToolLayerTests** | `test_get_request_context_success` | Request, employee, budget joined | PASS |
| | `test_get_request_context_unknown_request` | Unknown request ID handled | PASS |
| | `test_search_software_catalog_exact_match` | Exact product match in catalog | PASS |
| | `test_search_software_catalog_category_match`| Category overlap in catalog | PASS |
| | `test_search_software_catalog_no_match` | Non-overlapping software | PASS |
| | `test_vendor_risk_success` | Verified 200 vendor risk profile | PASS |
| | `test_vendor_risk_404` | Unrated vendor returns 404 | PASS |
| | `test_vendor_risk_forced_outage_503` | Forced outage on NimbusAI | PASS |
| | `test_vendor_risk_timeout` | Timeout simulation handled | PASS |
| | `test_vendor_risk_connection_failure` | Connection error handled | PASS |
| | `test_vendor_risk_malformed_response` | Malformed JSON handled | PASS |
| | `test_get_procurement_policy` | Policy version and 11 sections | PASS |
| **DeterministicRuleEngineTests** | `test_complete_request` | Complete request has 0 missing | PASS |
| | `test_missing_cost` | Missing cost flagged | PASS |
| | `test_missing_users` | Missing seat count flagged | PASS |
| | `test_missing_data_access` | Missing data access flagged | PASS |
| | `test_unknown_data_access_treated_as_missing`| "unknown" data access flagged | PASS |
| | `test_within_budget` | Within budget passes | PASS |
| | `test_over_budget` | Deficit triggers Finance | PASS |
| | `test_threshold_boundary_1000` | $1,000 $\rightarrow$ Manager | PASS |
| | `test_threshold_boundary_1000_01` | $1,000.01 $\rightarrow$ Dept Head, Procurement | PASS |
| | `test_threshold_boundary_10000` | $10,000 $\rightarrow$ Dept Head, Procurement | PASS |
| | `test_threshold_boundary_10000_01` | $10,000.01 $\rightarrow$ Dept Head, Finance, Procurement | PASS |
| | `test_threshold_boundary_25000` | $25,000 $\rightarrow$ Dept Head, Finance, Procurement | PASS |
| | `test_threshold_boundary_25000_01` | $25,000.01 $\rightarrow$ Dept Head, Finance, CFO, Procurement | PASS |
| | `test_security_source_code` | Source code $\rightarrow$ Security | PASS |
| | `test_security_production_access` | Cloud account $\rightarrow$ Security | PASS |
| | `test_security_confidential_documents`| Confidential docs $\rightarrow$ Security | PASS |
| | `test_security_employee_pii` | Employee PII $\rightarrow$ Security, Privacy | PASS |
| | `test_security_customer_pii` | Customer PII $\rightarrow$ Security, Privacy | PASS |
| | `test_security_credentials` | Credentials $\rightarrow$ Security | PASS |
| | `test_security_expired_assessment`| Review $> 365$ days $\rightarrow$ Expired, Security | PASS |
| | `test_security_missing_assessment`| Incomplete review $\rightarrow$ Security | PASS |
| | `test_security_conflicting_evidence`| Registry vs API conflict flagged | PASS |
| | `test_privacy_cross_region_data` | Cross-region $\rightarrow$ Privacy, Legal | PASS |
| | `test_legal_new_vendor_below_10k` | New vendor $<\$10k$ | PASS |
| | `test_legal_new_vendor_exactly_10k`| New vendor $\ge \$10k \rightarrow$ Legal | PASS |
| | `test_legal_new_vendor_above_10k` | New vendor $>\$10k \rightarrow$ Legal | PASS |
| | `test_legal_non_standard_terms` | Draft terms $\rightarrow$ Legal | PASS |
| | `test_vendor_api_unavailable_timeout`| API timeout $\rightarrow$ vendor_risk_unavailable | PASS |
| | `test_vendor_api_unavailable_503` | API 503 $\rightarrow$ vendor_risk_unavailable | PASS |
| | `test_vendor_api_unavailable_404` | API 404 $\rightarrow$ vendor_risk_unavailable | PASS |
| | `test_normal_request_no_injection` | Normal request clean | PASS |
| | `test_prompt_injection_detected_and_neutralized` | Jailbreak text neutralized | PASS |
| | `test_human_review_required_always_true` | Human authority preserved | PASS |
| **PublicCompatibilityTest** | `test_all_public_cases_meet_minimum_expectations` | PUB-01 to PUB-06 pass all eval checks | PASS |

---

## 3. Test Execution Command & Results

Run the full deterministic test suite using:
```bash
python -m unittest discover tests
```

### Execution Output:
```text
Ran 56 tests in 0.350s

OK
```

All 56 unit and compatibility tests pass with zero failures and zero errors.
