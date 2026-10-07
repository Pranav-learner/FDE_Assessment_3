# Phase 4 Test Plan & Verification Matrix

**Document ID:** `docs/fde/22_phase4_test_plan.md`  
**Phase:** 4 — Architecture A (Single-Agent Baseline)  
**System:** AI Procurement Request Copilot  
**Author:** Forward Deployed Engineering (FDE)  
**Status:** IMPLEMENTED & VERIFIED  

---

## 1. Test Suite Architecture

Architecture A is validated using a layered test harness ensuring 100% determinism, zero reliance on live internet connectivity for unit tests, and complete protection of human authority guardrails.

### Test Files
1. `tests/test_data_integrity.py`: 4 tests (Starter data integrity)
2. `tests/test_mock_api.py`: 3 tests (Vendor-risk service client)
3. `tests/test_tools.py`: 12 tests (Phase 2 tool contracts)
4. `tests/test_deterministic_engine.py`: 33 tests (Deterministic rule evaluations)
5. `tests/test_decision_engine.py`: 26 tests (Decision aggregation, precedence, and integration)
6. `tests/test_public_compatibility.py`: 1 test (Public case compatibility)
7. `tests/test_single_agent.py`: 20 tests (Architecture A agent, prompt, validation, and error recovery)

**Total Test Count:** **99 tests** (100% passing).

---

## 2. Architecture A Test Matrix (`tests/test_single_agent.py`)

| Test ID | Test Name | Target Behavior | Assertions |
|:---|:---|:---|:---|
| `test_01` | `test_01_normal_low_risk_request` | Low-value spend ($480) | `Manager` approval, `PROCEED_TO_REVIEW`, `llm_calls=1`. |
| `test_02` | `test_02_existing_tool_overlap` | Catalog alternative detection | `existing_tool_overlap` flagged, Dept Head/Finance/Security/Legal reviewers. |
| `test_03` | `test_03_security_sensitive_request` | Source code data access | `security_review_required` flagged, `Security` reviewer assigned. |
| `test_04` | `test_04_privacy_sensitive_request` | Customer PII & cross-region data | `privacy_review_required` flagged, `Privacy` reviewer assigned. |
| `test_05` | `test_05_legal_review_required` | New vendor + spend $\ge \$10\text{k}$ | `legal_review_required` flagged, `Legal` reviewer assigned. |
| `test_06` | `test_06_budget_insufficient` | Department spend deficit | `budget_insufficient` flagged, `Finance` reviewer assigned. |
| `test_07` | `test_07_missing_information` | Missing required fields | `NEEDS_INFORMATION`, $\ge 3$ clarification questions generated. |
| `test_08` | `test_08_vendor_api_unavailable` | External API 503 outage | `MANUAL_REVIEW`, unverified evidence cited without false safety claims. |
| `test_09` | `test_09_conflicting_vendor_evidence` | Inconsistent vendor records | `MANUAL_REVIEW`, conflict surfaced for human reconciliation. |
| `test_10` | `test_10_prompt_injection` | Embedded override attempt | `prompt_injection_detected`, human review enforced, override ignored. |
| `test_11` | `test_11_llm_malformed_output` | Broken JSON from model | Deterministic fallback produces valid `SingleAgentResponse`. |
| `test_12` | `test_12_llm_timeout_failure` | Timeout exception raised | Deterministic fallback succeeds cleanly without request failure. |
| `test_13` | `test_13_deterministic_fallback` | Provider outage exception | Deterministic fallback preserves all required approvals and risks. |
| `test_14` | `test_14_human_review_required_cannot_be_changed` | LLM attempts `human_review_required=False` | Post-processor enforces `human_review_required = True`. |
| `test_15` | `test_15_recommendation_cannot_be_changed` | LLM attempts `"APPROVED"` | Post-processor restores authoritative recommendation. |
| `test_16` | `test_16_approval_roster_cannot_be_changed` | LLM attempts to drop reviewers | Post-processor restores complete deterministic approval roster. |
| `test_17` | `test_17_risk_flags_cannot_be_changed` | LLM attempts to clear risk flags | Post-processor restores all deterministic risk flags. |
| `test_18` | `test_18_hallucinated_catalog_feature_avoided` | LLM claims non-existent catalog tool | Deterministic catalog evidence blocks false overlap flag. |
| `test_19` | `test_19_clarification_questions_generated` | Intake fields missing | Targeted questions generated for cost, users, and data access. |
| `test_20` | `test_20_telemetry_records_calls` | Telemetry instrumentation | Records `llm_calls=1`, `tool_calls \ge 4`, tool names. |

---

## 3. Public Evaluation Benchmark Results

Evaluation executed via `python evals/run_public_evals.py --architecture single`:

| Case ID | Request ID | Title | Minimum Checks | Latency | LLM Calls | Tool Calls |
|:---|:---|:---|:---:|:---:|:---:|:---:|
| **PUB-01** | `REQ-1001` | Low-value approved vendor | **PASS** | 568.5 ms | 1 | 5 |
| **PUB-02** | `REQ-1002` | Existing alternatives + new vendor | **PASS** | 46.4 ms | 1 | 5 |
| **PUB-03** | `REQ-1003` | Sensitive source-code access | **PASS** | 44.8 ms | 1 | 5 |
| **PUB-04** | `REQ-1005` | Budget shortfall + new sensitive vendor | **PASS** | 45.8 ms | 1 | 5 |
| **PUB-05** | `REQ-1006` | Incomplete request + prompt injection | **PASS** | 52.7 ms | 1 | 5 |
| **PUB-06** | `REQ-1009` | Vendor-risk API unavailable | **PASS** | 50.3 ms | 1 | 5 |

**Overall Score:** **6 / 6 (100% PASS)**.
Average Latency: ~135 ms (Cold start 568ms, warm ~48ms), beating the 3.5s target by over 25x.
