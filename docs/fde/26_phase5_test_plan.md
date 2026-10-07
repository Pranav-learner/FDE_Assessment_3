# Phase 5 Test Plan & Verification Matrix

**Document ID:** `docs/fde/26_phase5_test_plan.md`  
**Phase:** 5 — Architecture B (Staged Two-Agent Architecture)  
**System:** AI Procurement Request Copilot  
**Author:** Forward Deployed Engineering (FDE)  
**Status:** IMPLEMENTED & VERIFIED  

---

## 1. Test Suite Architecture

Architecture B is validated across 125 total tests covering starter data integrity, mock API behavior, tool contracts, deterministic rule evaluation, decision engine precedence, Architecture A unit tests, and Architecture B staged tests.

### Test Files Breakdown
1. `tests/test_data_integrity.py`: 4 tests
2. `tests/test_mock_api.py`: 3 tests
3. `tests/test_tools.py`: 12 tests
4. `tests/test_deterministic_engine.py`: 33 tests
5. `tests/test_decision_engine.py`: 26 tests
6. `tests/test_public_compatibility.py`: 1 test
7. `tests/test_single_agent.py`: 20 tests (Architecture A)
8. `tests/test_staged_agents.py`: 26 tests (Architecture B & Cross-Architecture)

**Total Test Count:** **125 tests** (100% PASSING, 0 failures, 0 errors).

---

## 2. Architecture B Test Matrix (`tests/test_staged_agents.py`)

| Test ID | Test Name | Target Behavior | Assertions |
|:---|:---|:---|:---|
| `test_01` | `test_01_normal_low_risk_request` | Low-value spend ($800) | `Manager` approval, `llm_calls=2`, both agent names in telemetry. |
| `test_02` | `test_02_existing_tool_overlap` | Catalog alternative detection | `existing_tool_overlap` flagged in both dossier and decision. |
| `test_03` | `test_03_functional_mismatch` | Functional gap extraction | Agent 1 identifies specific capability gap in catalog tool. |
| `test_04` | `test_04_security_sensitive_request` | Source code data access | `security_review_required` flagged, `Security` reviewer assigned. |
| `test_05` | `test_05_privacy_sensitive_request` | Customer PII & cross-region data | `privacy_review_required` flagged, `Privacy` reviewer assigned. |
| `test_06` | `test_06_legal_review_required` | New vendor + spend $\ge \$10\text{k}$ | `legal_review_required` flagged, `Legal` reviewer assigned. |
| `test_07` | `test_07_budget_insufficient` | Department spend deficit | `budget_insufficient` flagged, `Finance` reviewer assigned. |
| `test_08` | `test_08_missing_information` | Missing required fields | `NEEDS_INFORMATION`, $\ge 3$ clarification questions generated. |
| `test_09` | `test_09_vendor_api_unavailable` | External API 503 outage | `MANUAL_REVIEW`, unverified evidence cited without false claims. |
| `test_10` | `test_10_conflicting_vendor_evidence` | Inconsistent vendor records | `MANUAL_REVIEW`, conflict surfaced for human reconciliation. |
| `test_11` | `test_11_prompt_injection` | Embedded override attempt | `prompt_injection_detected`, human review enforced, override ignored. |
| `test_12` | `test_12_agent1_malformed_output` | Broken JSON from Agent 1 | Agent 1 deterministic fallback dossier succeeds cleanly. |
| `test_13` | `test_13_agent1_timeout` | Timeout in Agent 1 | Fallback handles timeout without breaking pipeline. |
| `test_14` | `test_14_agent2_malformed_output` | Broken JSON from Agent 2 | Agent 2 deterministic fallback dossier succeeds cleanly. |
| `test_15` | `test_15_agent2_timeout` | Timeout in Agent 2 | Fallback handles timeout without breaking pipeline. |
| `test_16` | `test_16_deterministic_fallback` | Total provider outage | Pipeline gracefully returns valid `StagedAgentResponse`. |
| `test_17` | `test_17_agent1_cannot_change_policy` | Rogue Agent 1 claims no review | Policy recommendations and approvers preserved. |
| `test_18` | `test_18_agent2_cannot_change_policy` | Rogue Agent 2 claims auto-approval | Auto-approval token sanitized, `NEEDS_INFORMATION` preserved. |
| `test_19` | `test_19_required_approvals_cannot_be_removed` | Roster tampering attempt | All deterministic approvers preserved. |
| `test_20` | `test_20_human_review_cannot_be_disabled` | Autonomous execution attempt | `human_review_required = True` invariant. |
| `test_21` | `test_21_risk_flags_cannot_be_cleared` | Risk clearing attempt | All deterministic risk flags preserved. |
| `test_22` | `test_22_structured_handoff` | Inter-agent communication | Typed `IntakeOverlapDossier` and `GovernanceTriageDossier` present. |
| `test_23` | `test_23_exactly_two_llm_calls` | Multi-agent execution count | Exactly 2 LLM calls recorded in normal run. |
| `test_24` | `test_24_telemetry_records_both_agents` | Telemetry instrumentation | Agent names `["intake_overlap", "governance_triage"]` recorded. |
| `test_25` | `test_25_matches_deterministic_policy` | Policy parity | Complete output conforms to deterministic ground truth. |
| `test_26` | `test_26_cross_architecture_equality` | Parity with Architecture A | Identical recommendations, approvers, missing info, and risks across all 6 public cases. |

---

## 3. Public Evaluation Benchmark Comparison

Evaluations executed using `python evals/run_public_evals.py`:

| Case ID | Request ID | Architecture A (Single) | Architecture B (Staged) | Status |
|:---|:---|:---:|:---:|:---:|
| **PUB-01** | `REQ-1001` | PASS (617 ms, 1 LLM, 5 Tools) | **PASS** (547 ms, 2 LLM, 5 Tools) | **PARITY** |
| **PUB-02** | `REQ-1002` | PASS (49 ms, 1 LLM, 5 Tools) | **PASS** (50 ms, 2 LLM, 5 Tools) | **PARITY** |
| **PUB-03** | `REQ-1003` | PASS (52 ms, 1 LLM, 5 Tools) | **PASS** (49 ms, 2 LLM, 5 Tools) | **PARITY** |
| **PUB-04** | `REQ-1005` | PASS (47 ms, 1 LLM, 5 Tools) | **PASS** (53 ms, 2 LLM, 5 Tools) | **PARITY** |
| **PUB-05** | `REQ-1006` | PASS (51 ms, 1 LLM, 5 Tools) | **PASS** (47 ms, 2 LLM, 5 Tools) | **PARITY** |
| **PUB-06** | `REQ-1009` | PASS (52 ms, 1 LLM, 5 Tools) | **PASS** (51 ms, 2 LLM, 5 Tools) | **PARITY** |

**Evaluation Result:** 6/6 passed for both architectures.
