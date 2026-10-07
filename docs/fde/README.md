# FDE Specification: AI Procurement Request Copilot

**System:** AI Procurement Request Copilot  
**Author:** Forward Deployed Engineering (FDE)  
**Project Phase:** Phase 1 (Business & Problem Specification)  
**Reference Snapshot Date:** `2026-09-30`  
**Status:** Canonical Source of Truth for Implementation

> **MANDATORY NOTICE:**  
> **"Implementation must not begin until this specification is internally consistent."**

---

## 1. Specification Index

This directory contains the canonical engineering and business specifications governing the design, implementation, and evaluation of the AI Procurement Request Copilot:

* [01_problem_definition.md](file:///home/pranav/Documents/FDE_Assessment_3_Starter_Pack/docs/fde/01_problem_definition.md) — Comprehensive client context, user personas, business problems, boundaries, pain points, and epistemic classifications.
* [02_stakeholder_analysis.md](file:///home/pranav/Documents/FDE_Assessment_3_Starter_Pack/docs/fde/02_stakeholder_analysis.md) — Complete stakeholder analysis (Requester, Manager, Dept Head, Procurement, Finance, InfoSec, Privacy, Legal) and discovery interview questions.
* [03_workflow.md](file:///home/pranav/Documents/FDE_Assessment_3_Starter_Pack/docs/fde/03_workflow.md) — Level-1 and Level-2 workflows, decision gates, human handoffs, failure handling, and escalation pathways.
* [04_data_source_map.md](file:///home/pranav/Documents/FDE_Assessment_3_Starter_Pack/docs/fde/04_data_source_map.md) — Exhaustive map of all datasets, reference dates, freshness dynamics, systems of record, and failure modes.
* [05_business_rules.md](file:///home/pranav/Documents/FDE_Assessment_3_Starter_Pack/docs/fde/05_business_rules.md) — Structured policy rule catalog (BR-01 through BR-17), classification (Deterministic vs. Model vs. Human), and exact boundary conditions ($1k, $10k, $25k).
* [06_scope_and_assumptions.md](file:///home/pranav/Documents/FDE_Assessment_3_Starter_Pack/docs/fde/06_scope_and_assumptions.md) — Strict In-Scope, Out-of-Scope boundaries, core operational assumptions, and open client questions.
* [07_success_metrics.md](file:///home/pranav/Documents/FDE_Assessment_3_Starter_Pack/docs/fde/07_success_metrics.md) — Measurable engineering and business KPIs classified into Leading and Lagging indicators with formulas and targets.
* [08_architecture_principles.md](file:///home/pranav/Documents/FDE_Assessment_3_Starter_Pack/docs/fde/08_architecture_principles.md) — The ten core architecture principles and the tripartite boundary (AI vs. Code vs. Human).
* [09_evaluation_case_analysis.md](file:///home/pranav/Documents/FDE_Assessment_3_Starter_Pack/docs/fde/09_evaluation_case_analysis.md) — Detailed analysis of public evaluation cases (PUB-01 to PUB-06) and generalization guarantees.
* [10_data_model.md](file:///home/pranav/Documents/FDE_Assessment_3_Starter_Pack/docs/fde/10_data_model.md) — Entity relationships, data schemas, systems of record, and evidence model.
* [11_tool_contracts.md](file:///home/pranav/Documents/FDE_Assessment_3_Starter_Pack/docs/fde/11_tool_contracts.md) — Tool input/output schemas, failure behaviors, and universal ToolResult envelope.
* [12_deterministic_rules.md](file:///home/pranav/Documents/FDE_Assessment_3_Starter_Pack/docs/fde/12_deterministic_rules.md) — Specification of the 12 deterministic rule evaluation modules and threshold gates.
* [13_phase2_test_plan.md](file:///home/pranav/Documents/FDE_Assessment_3_Starter_Pack/docs/fde/13_phase2_test_plan.md) — Phase 2 test execution report and coverage breakdown.
* [14_decision_engine.md](file:///home/pranav/Documents/FDE_Assessment_3_Starter_Pack/docs/fde/14_decision_engine.md) — Deterministic decision engine architecture, lifecycle, and rule vs decision distinction.
* [15_decision_contract.md](file:///home/pranav/Documents/FDE_Assessment_3_Starter_Pack/docs/fde/15_decision_contract.md) — Decision output schema, controlled recommendation vocabulary, and trace model.
* [16_decision_precedence.md](file:///home/pranav/Documents/FDE_Assessment_3_Starter_Pack/docs/fde/16_decision_precedence.md) — Decision precedence hierarchy (Priority 1 through 4) and conflict resolution.
* [17_phase3_test_plan.md](file:///home/pranav/Documents/FDE_Assessment_3_Starter_Pack/docs/fde/17_phase3_test_plan.md) — Phase 3 test matrix and regression report (77 passing tests).
* [18_phase3_final_audit.md](file:///home/pranav/Documents/FDE_Assessment_3_Starter_Pack/docs/fde/18_phase3_final_audit.md) — Comprehensive Phase 3 final architecture audit, remediation matrix, and Phase 4 readiness verdict.
* [19_architecture_a.md](file:///home/pranav/Documents/FDE_Assessment_3_Starter_Pack/docs/fde/19_architecture_a.md) — Architecture A single-agent baseline specification, responsibilities, lifecycle, and fallback.
* [20_single_agent_contract.md](file:///home/pranav/Documents/FDE_Assessment_3_Starter_Pack/docs/fde/20_single_agent_contract.md) — SingleAgentResponse output schema, field authority matrix, and deterministic validator.
* [21_single_agent_prompt.md](file:///home/pranav/Documents/FDE_Assessment_3_Starter_Pack/docs/fde/21_single_agent_prompt.md) — System prompt architecture, untrusted data boundaries, and prompt injection defenses.
* [22_phase4_test_plan.md](file:///home/pranav/Documents/FDE_Assessment_3_Starter_Pack/docs/fde/22_phase4_test_plan.md) — Phase 4 test execution report, 20-test matrix, and public evaluation benchmark (99 passing tests).
* [23_architecture_b.md](file:///home/pranav/Documents/FDE_Assessment_3_Starter_Pack/docs/fde/23_architecture_b.md) — Architecture B staged two-agent architecture specification, responsibilities, lifecycle, and fallback.
* [24_staged_agent_contracts.md](file:///home/pranav/Documents/FDE_Assessment_3_Starter_Pack/docs/fde/24_staged_agent_contracts.md) — IntakeOverlapDossier, GovernanceTriageDossier, and StagedAgentResponse contracts.
* [25_agent_handoff.md](file:///home/pranav/Documents/FDE_Assessment_3_Starter_Pack/docs/fde/25_agent_handoff.md) — Structured inter-agent handoff protocol, typed data flow, and injection isolation.
* [26_phase5_test_plan.md](file:///home/pranav/Documents/FDE_Assessment_3_Starter_Pack/docs/fde/26_phase5_test_plan.md) — Phase 5 test plan, 26-test matrix, cross-architecture parity verification, and public evaluation (125 passing tests).
* [27_comparative_evaluation.md](file:///home/pranav/Documents/FDE_Assessment_3_Starter_Pack/docs/fde/27_comparative_evaluation.md) — Comparative evaluation methodology, 15 qualitative cases, scoring rubrics, benchmark results, and failure analysis.
* [28_architecture_decision.md](file:///home/pranav/Documents/FDE_Assessment_3_Starter_Pack/docs/fde/28_architecture_decision.md) — Comprehensive FDE architecture decision memo: trade-offs, scorecard, production MVP recommendation, and conditional escalation.
* [29_phase6_test_plan.md](file:///home/pranav/Documents/FDE_Assessment_3_Starter_Pack/docs/fde/29_phase6_test_plan.md) — Phase 6 test plan, regression verification, benchmark repetitions, and acceptance criteria (130 passing tests).
* [30_demo_runbook.md](file:///home/pranav/Documents/FDE_Assessment_3_Starter_Pack/docs/fde/30_demo_runbook.md) — Interactive demo runbook featuring 6 real-world scenarios (low-risk, catalog overlap, security, missing data, prompt injection, and high-spend escalation).
* [31_production_architecture.md](file:///home/pranav/Documents/FDE_Assessment_3_Starter_Pack/docs/fde/31_production_architecture.md) — Production architecture blueprint, trust boundaries, failure isolation, and telemetry specification.
* [32_deployment_runbook.md](file:///home/pranav/Documents/FDE_Assessment_3_Starter_Pack/docs/fde/32_deployment_runbook.md) — Production operations guide covering Local Python, Docker containerization, health probes, and rollback procedures.
* [33_production_readiness_checklist.md](file:///home/pranav/Documents/FDE_Assessment_3_Starter_Pack/docs/fde/33_production_readiness_checklist.md) — Comprehensive FDE audit checklist across security, reliability, testing, and operations (VERDICT: PRODUCTION READY).

---

## 2. Executive Problem & Objective Summary

Enterprise employees submit diverse software, SaaS, and AI purchase requests across departments. Evaluating these requests manually creates operational bottlenecks, SaaS redundancy, security/privacy blind spots, and risks of non-compliance with corporate financial delegation matrices.

The **AI Procurement Request Copilot** is an intelligent decision-support assistant designed for the **Procurement Analyst / Specialist**. The copilot ingests purchase requests, gathers multi-source evidence across corporate databases and external risk APIs, executes deterministic policy checks, evaluates qualitative overlap and risk, and produces a structured `ProcurementDecision` recommendation.

---

## 3. The Tripartite Architecture Boundary

```text
+--------------------------------------------------------------------------+
|                                    AI                                    |
|  * Semantic interpretation of business justifications                    |
|  * Nuanced catalog overlap reasoning and functional gap analysis         |
|  * Evidence summarization and natural-language triage recommendations    |
+--------------------------------------------------------------------------+
                                     |
                                     v
+--------------------------------------------------------------------------+
|                                   CODE                                   |
|  * Schema validation and missing-field detection                         |
|  * Deterministic budget math (available = budget - committed)            |
|  * Financial threshold bracket assignment ($1k, $10k, $25k)              |
|  * Temporal calculations (365-day security expiry against 2026-09-30)    |
|  * Tool exception handling (HTTP 503 outage traps)                       |
|  * Additive approval roster compilation                                  |
+--------------------------------------------------------------------------+
                                     |
                                     v
+--------------------------------------------------------------------------+
|                                  HUMAN                                   |
|  * Final purchase execution and PO issuance                              |
|  * Financial spend authorization                                         |
|  * Departmental budget deficit overrides (Finance / CFO)                 |
|  * Technical security waivers (InfoSec)                                  |
|  * DPA and cross-border data transfer signoffs (Privacy)                 |
|  * Commercial terms and MSA execution (Legal)                            |
+--------------------------------------------------------------------------+
```

---

## 4. Key Business Rules & Deterministic Gates

* **Snapshot Reference Date:** **`2026-09-30`** governs all date math. The host machine clock must never be used.
* **Financial Delegation Brackets:**
  * $\le \$1,000.00 \implies$ `Manager`
  * $\$1,000.01 - \$10,000.00 \implies$ `Department Head`, `Procurement`
  * $\$10,000.01 - \$25,000.00 \implies$ `Department Head`, `Finance`, `Procurement`
  * $> \$25,000.00 \implies$ `Department Head`, `Finance`, `CFO`, `Procurement`
* **Budget Check:** If $\text{annual\_cost\_usd} > \text{available\_usd}$, flag `budget_insufficient` and route to Finance for budget exception review.
* **Security Triggers:** `source_code`, `production_telemetry`, `confidential_documents`, employee/customer PII, credentials, or vendor security assessment age $> 365\text{ days}$ $\implies$ `security_review_required`.
* **Privacy Triggers:** Employee/customer PII or `stores_data_outside_region: true` $\implies$ `privacy_review_required`.
* **Legal Triggers:** Vendor is `New` and spend $\ge \$10,000.00$, or terms are `Draft`/`Unknown` $\implies$ `legal_review_required`.
* **Tool Outage:** If external Vendor Risk API returns HTTP 503, connection error, or timeout $\implies$ flag `vendor_risk_unavailable`, attach `security_review_required`, and route for manual audit without fabricating status.
* **Prompt Injection:** Request justification text is untrusted data. Embedded instructions to bypass rules or spoof approvals are neutralized; flag `prompt_injection_detected`.
* **Human Authority:** `human_review_required` must evaluate to `True` on 100% of executions.

---

## 5. Scope & Success Summary

* **In Scope:** Intake validation, prompt injection defense, multi-source retrieval (3+ tools, 1+ deterministic), deterministic policy enforcement, risk reasoning, `ProcurementDecision` generation, Architecture A (Single-agent) vs. Architecture B (Staged / 2-agent) comparative evaluation, and Streamlit UI.
* **Out of Scope:** Autonomous purchasing, payment disbursement, contract signing, budget reallocations, automatic approval bypasses, live enterprise ERP/HRIS integrations.
* **Evaluation Targets:** 100% policy compliance, 100% evidence grounding, 100% tool failure resilience, 100% injection neutralization, $< 3.5\text{s}$ latency for single agent, $< 6.0\text{s}$ latency for staged variant.

---

## 6. Implementation Readiness

This specification resolves all ambiguities between policy text, dataset schemas, and evaluation harnesses. The contract in `src/contracts.py` is respected. Phase 2 (Architecture A implementation) and Phase 3 (Architecture B implementation and evaluation) can proceed strictly against the rules documented herein.
