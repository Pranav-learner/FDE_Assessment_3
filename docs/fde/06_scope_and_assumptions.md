# 06. Scope and Assumptions: AI Procurement Request Copilot

**Document Version:** 1.0.0  
**Status:** Baseline Specification (Phase 1 Source of Truth)  
**Author:** Forward Deployed Engineering (FDE)

---

## 1. IN SCOPE

The initial implementation (Phase 2 & 3) of the AI Procurement Request Copilot is intentionally focused on building a dependable, auditable decision-support engine. The in-scope boundaries comprise:

1. **Intake Processing & Normalization:**
   * Ingesting structured and semi-structured request payloads from `data/requests.json`.
   * Normalizing field values and identifying missing material parameters (`cost`, `user_count`, `data_access_level`).
2. **Untrusted Business Data Sanitization:**
   * Treating all request descriptions, business justifications, and notes as untrusted user inputs.
   * Detecting and neutralizing prompt injection attempts; isolating user text from system instructions.
3. **Multi-Source Evidence Retrieval (Tool Use):**
   * Integrating at least 3 distinct tools, with at least 1 purely deterministic tool:
     - Employee & Department Budget Lookup (Deterministic).
     - Software Catalog & Overlap Search (Deterministic + Semantic).
     - Vendor Registry & Historical Purchase Retrieval (Deterministic).
     - External Vendor-Risk API Client (`mock_api/app.py`).
4. **Deterministic Policy Enforcement:**
   * Calculating available department budget arithmetic (`available_usd = annual_software_budget - committed_usd`).
   * Categorizing annualized requests into exact financial approval brackets ($1,000, $10,000, $25,000).
   * Calculating vendor security assessment staleness against the immutable reference date `2026-09-30` (365-day rule).
5. **Contextual Risk & Overlap Reasoning:**
   * Identifying functional software redundancy against `software_catalog.csv`.
   * Evaluating data access sensitivity (`source_code`, `production_telemetry`, `customer_pii`, `employee_pii`, `confidential_documents`).
   * Detecting internal vs. external vendor data conflicts.
   * Gracefully handling external tool/API outages (HTTP 503 from vendor-risk service).
6. **Structured Output Contract Generation:**
   * Producing fully compliant `ProcurementDecision` objects adhering to `src/contracts.py`:
     - `request_id`, `recommendation`, `evidence` (list of `EvidenceItem`), `required_approvals`, `missing_information`, `risk_flags`, `next_step`, `human_review_required: True`, and `telemetry`.
7. **Architectural Experimentation & Public Evaluation:**
   * Implementing Architecture A: Single-agent baseline.
   * Implementing Architecture B: Lightweight staged / 2-agent variant.
   * Evaluating both architectures against the public evaluation suite (`evals/public_cases.json`, `evals/run_public_evals.py`) and hidden test cases.
   * Benchmarking latency, LLM calls, tool calls, and policy adherence.
8. **User Interface Scaffold:**
   * Providing a local Streamlit interface (`app.py`) for procurement analysts to view request details, inspect evidence chains, and review generated recommendations.

---

## 2. OUT OF SCOPE

To protect enterprise security, prevent unintended side effects, and adhere to the strict scope of the starter pack, the following capabilities are **explicitly out of scope**:

1. **Autonomous Purchase Execution:** The system will NOT submit orders, generate purchase orders (POs), or communicate with external vendors to place software orders.
2. **Payment Processing & Financial Transfers:** The system will NOT integrate with banking gateways, credit card processors, or accounts payable disbursement systems.
3. **Contract Signing & Legal Execution:** The system will NOT execute contracts, sign clickwrap/DocuSign agreements, or bind the enterprise to vendor terms.
4. **Budget Modification & Fund Reallocation:** The system will NOT modify `department_budgets.csv`, transfer budget across departments, or approve financial exceptions.
5. **Automatic Approval & Human Bypasses:** The system will NEVER grant final approval or bypass human review (`human_review_required` must remain `True` across all runs).
6. **Vendor Onboarding Execution:** The system will NOT transition a vendor from `New` to `Approved` in `vendors.csv` or complete vendor risk questionnaires.
7. **Production Enterprise Integrations:** Direct integrations with live enterprise ERPs (NetSuite, SAP), HRIS (Workday), SSO providers (Okta), or enterprise ticketing systems (Jira, ServiceNow) are out of scope unless mocked via the starter pack files.
8. **Arbitrary Multi-Agent Orchestration:** Complex multi-agent swarms with $>2$ agents or autonomous background daemon tasks are out of scope.

---

## 3. ASSUMPTIONS

1. **Static Data Snapshot:** All CSV datasets (`employees.csv`, `department_budgets.csv`, `software_catalog.csv`, `vendors.csv`, `purchase_history.csv`) and the JSON policy document represent an immutable operational state as of `2026-09-30`.
2. **Temporal Anchor:** `2026-09-30` is the single source of truth for all date-based calculations (e.g. 365-day security review freshness). The local host clock is never referenced for business logic.
3. **Currency Standardization:** All monetary figures are expressed in annualized United States Dollars (USD).
4. **Role Seniority Mapping:** In `employees.csv`, employee levels follow standard hierarchy: `IC3` < `IC4` < `IC5` < `Director` < `VP`. Direct managers are determined by `manager_id`.
5. **Budget Sufficiency Definition:** Department available budget is strictly $ \text{annual\_software\_budget\_usd} - \text{committed\_usd} $. If $ \text{annual\_cost\_usd} > \text{available\_usd} $, `budget_insufficient` must be triggered.
6. **Cross-Region Definition:** If the vendor-risk API reports `stores_data_outside_region: true`, it is assumed to constitute cross-border data processing, triggering Privacy and Legal review under Policy §§6–7.
7. **Public Evaluation Alignment:** The public eval cases in `evals/public_cases.json` represent minimum baseline checks; production solutions must generalize to arbitrary hidden edge cases without overfitting to request IDs.

---

## 4. OPEN QUESTIONS

The following questions represent strategic discovery areas that an FDE would clarify with enterprise sponsors prior to enterprise rollout:

1. **Departmental Chargeback vs. Central IT:** If a tool is added to the enterprise catalog for company-wide use, is the cost charged against the initiating department's budget or an IT overhead pool?
2. **SaaS License Re-Harvesting:** Does the enterprise have an automated mechanism to identify inactive seats in existing tools (e.g., PixelCraft Pro) before authorizing new departmental purchases?
3. **SLA for Governance Reviews:** What are the expected turnaround times for InfoSec, Privacy, and Legal reviews, and should the copilot recommend provisional access for low-risk testing?
4. **Ticketing System Target Architecture:** When moving from local Streamlit to production, will the copilot run as an API service called by ServiceNow/Jira, or as an independent browser extension?
5. **Custom Add-On Contracting:** When an existing approved vendor (e.g., SignFlow) offers an add-on, under what conditions does Legal require an amendment to the existing master agreement?
