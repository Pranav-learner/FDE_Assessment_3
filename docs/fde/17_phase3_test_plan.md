# 17. Phase 3 Test Plan & Verification Report: AI Procurement Request Copilot

**Document Version:** 1.0.0  
**Phase:** Phase 3 (Deterministic Decision Engine Test Plan)  
**Author:** Forward Deployed Engineering (FDE)

---

## 1. Test Strategy Overview

Phase 3 validates the **deterministic decision aggregation engine** (`src/decision_engine.py`).

The testing strategy guarantees that:
1. Decision precedence operates with 100% mathematical reliability.
2. Controlled recommendation states (`NEEDS_INFORMATION`, `MANUAL_REVIEW`, `PROCEED_TO_REVIEW`) are strictly respected.
3. Autonomous approvals (`APPROVED`, `PURCHASED`) are impossible.
4. Human review remains unconditionally mandatory (`human_review_required = True`).
5. Complete decision contracts satisfy all expectations of the public evaluation harness (`PUB-01` through `PUB-06`).
6. Zero regression occurs across the 56 existing Phase 2 unit tests.

---

## 2. Test Coverage & Execution Matrix

### New Decision Engine Test Suite: `tests/test_decision_engine.py` (21 Tests)

| Test ID | Test Name | Target Behavior | Precedence Tier | Result |
|---|---|---|:---:|:---:|
| **01** | `test_01_normal_request` | Normal happy-path request | Priority 4 | PASS |
| **02** | `test_02_missing_information` | Missing required fields | Priority 1 | PASS |
| **03** | `test_03_budget_insufficiency` | Budget deficit triggers Finance | Priority 3 | PASS |
| **04** | `test_04_low_value_approval` | Spend $\le \$1,000 \rightarrow$ Manager only | Priority 4 | PASS |
| **05** | `test_05_boundary_1000_01` | Spend $\$1,000.01 \rightarrow$ Dept Head, Procurement | Priority 3/4 | PASS |
| **06** | `test_06_boundary_10000` | Spend $\$10,000.00 \rightarrow$ Dept Head, Procurement | Priority 3/4 | PASS |
| **07** | `test_07_boundary_10000_01` | Spend $\$10,000.01 \rightarrow$ Dept Head, Finance, Procurement | Priority 3 | PASS |
| **08** | `test_08_boundary_25000` | Spend $\$25,000.00 \rightarrow$ Dept Head, Finance, Procurement | Priority 3 | PASS |
| **09** | `test_09_boundary_25000_01` | Spend $\$25,000.01 \rightarrow$ Dept Head, Finance, CFO, Procurement | Priority 3 | PASS |
| **10** | `test_10_security_review` | Source-code access $\rightarrow$ Security | Priority 3 | PASS |
| **11** | `test_11_privacy_review` | Customer PII $\rightarrow$ Privacy | Priority 3 | PASS |
| **12** | `test_12_legal_review` | New vendor spend $\ge \$10,000 \rightarrow$ Legal | Priority 3 | PASS |
| **13** | `test_13_existing_software_overlap` | Catalog overlap flagged, not rejected | Priority 3 | PASS |
| **14** | `test_14_expired_vendor_review` | Assessment $> 365$ days $\rightarrow$ Expired, Security | Priority 3 | PASS |
| **15** | `test_15_conflicting_vendor_evidence`| Conflicting records $\rightarrow$ MANUAL_REVIEW | Priority 2 | PASS |
| **16** | `test_16_vendor_api_unavailable` | 503 outage on NimbusAI $\rightarrow$ MANUAL_REVIEW | Priority 2 | PASS |
| **17** | `test_17_prompt_injection` | Prompt injection neutralized; human signoff preserved | Priority 1/3 | PASS |
| **18** | `test_18_multiple_simultaneous_risks`| Budget deficit + Security + Privacy + Legal | Priority 3 | PASS |
| **19** | `test_19_multiple_required_approvals`| Accumulation of all required approver roles | Priority 3 | PASS |
| **20** | `test_20_human_review_always_true` | Verified across all 10 requests | Universal | PASS |
| **21** | `test_21_all_public_eval_cases` | PUB-01 to PUB-06 pass evaluation harness | Universal | PASS |

---

## 3. Full Repository Test Summary & Regression Verification

```bash
python -m unittest discover tests -v
```

### Cumulative Results Breakdown:
* **Starter Pack Integrity Tests (`test_data_integrity.py`, `test_mock_api.py`):** 10 tests
* **Tool Layer Tests (`test_tools.py`):** 12 tests
* **Deterministic Rule Engine Tests (`test_deterministic_engine.py`):** 33 tests
* **Public Compatibility Tests (`test_public_compatibility.py`):** 1 test
* **Decision Engine Tests (`test_decision_engine.py`):** 21 tests
* **Total Passing Tests:** **77 tests**
* **Total Failures / Errors:** **0**
* **Execution Duration:** 1.189s

Zero regressions detected across all existing Phase 2 suites.
