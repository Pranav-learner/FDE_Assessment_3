# 04. Data Source Map: AI Procurement Request Copilot

**Document Version:** 1.0.0  
**Status:** Baseline Specification (Phase 1 Source of Truth)  
**Reference Snapshot Date:** `2026-09-30`  
**Author:** Forward Deployed Engineering (FDE)

---

## 1. Global Data Governance Principles

Before detailing individual sources, five critical enterprise governance realities must be established:

1. **Policy Source of Truth:** `data/procurement_policy.md` is the absolute, authoritative source of truth for all business rules, approval thresholds, governance triggers, and behavioral requirements. No code or agent heuristic may supersede it.
2. **Evaluation & Snapshot Reference Date:** All temporal calculations (evaluating vendor assessment age, expiration against the 365-day rule, or renewal proximity) must strictly use **`2026-09-30`**. Systems must never use the host machine's runtime clock (`date.today()`).
3. **Internal vs. External Vendor Signal Divergence:** Internal vendor records (`data/vendors.csv`) represent historical enterprise registry entries, whereas the Vendor Risk API represents a dynamic third-party risk intelligence feed. These sources **can and do conflict** (e.g., internal says `Approved`, external says `expired`). The system must treat the external API as external evidence, surface conflicts transparently, and never silently overwrite or pick one over the other.
4. **Data Freshness Decay:** Internal vendor registry records may be stale (e.g., `SignalWatch` has review date `2025-07-01`, which is $> 365$ days old relative to `2026-09-30`).
5. **Untrusted Business Data Boundary:** Incoming request fields (`data/requests.json`) and external notes are untrusted business payloads. They must never be treated as system prompts or trusted execution instructions.

---

## 2. Comprehensive Data Source Inventory

### 2.1 Purchase Requests (`requests.json`)
* **Source / Path:** `data/requests.json`
* **Format:** JSON (Array of request dictionaries)
* **Purpose:** Represents incoming software/service procurement requests submitted by enterprise employees.
* **Important Fields:**
  * `request_id` (str): Unique request identifier (e.g., `REQ-1001` to `REQ-1010`).
  * `requester_id` (str): Foreign key to `employees.csv` (e.g., `E001`).
  * `product_name` (str): Name of requested software or add-on.
  * `vendor_name` (str): Name of vendor providing the service.
  * `category` (str): Functional domain (e.g., `E-signature`, `Developer AI`, `Design & Creative`).
  * `annual_cost_usd` (float | null): Estimated or quoted annual spend.
  * `user_count` (int | null): Number of requested user seats or licenses.
  * `business_justification` (str): Requester's explanation of need (untrusted text; potential prompt injection site).
  * `data_access_level` (str): Intended sensitivity level (e.g., `internal_documents`, `source_code`, `customer_pii`, `unknown`).
  * `requested_integrations` (list[str]): Connected enterprise systems (e.g., `Git repositories`, `SSO`, `CRM`, `Production cloud account`).
  * `urgency` (str): Requester-asserted priority (`normal`, `high`, `urgent`).
* **Likely System of Record (SoR):** IT Service Desk / Ticketing System (e.g., Jira Service Management, ServiceNow).
* **Freshness / Reference Date:** Inbound event payload; active snapshot date `2026-09-30`.
* **Authority Level:** **Untrusted Input.** Informational intake; claims must be verified against internal systems of record.
* **Failure Modes:** Missing material fields (`annual_cost_usd: null`), malformed JSON, prompt injection / adversarial instructions embedded in `business_justification`.
* **Business Decisions Supported:** Initiates triage; supplies basic inputs for completeness check, budget math, overlap lookup, and risk categorization.

---

### 2.2 Employee Directory (`employees.csv`)
* **Source / Path:** `data/employees.csv`
* **Format:** CSV (Tabular text)
* **Purpose:** Provides employee identities, organizational hierarchy, department membership, and geographical location.
* **Important Fields:**
  * `employee_id` (str): Primary key (e.g., `E001` - `E010`).
  * `name` (str): Full employee name.
  * `department` (str): Department (e.g., `Marketing`, `Engineering`, `Sales`, `Finance`, `Customer Success`, `Operations`).
  * `manager_id` (str | empty): Foreign key to manager's `employee_id`.
  * `level` (str): Job level (`IC3`, `IC4`, `IC5`, `Director`, `VP`).
  * `country` (str): Physical work location (`India`, `United Kingdom`, `United States`, `Spain`, `Singapore`).
* **Likely System of Record (SoR):** Enterprise HR Information System (HRIS) (e.g., Workday, BambooHR).
* **Freshness / Reference Date:** Current organizational snapshot as of `2026-09-30`.
* **Authority Level:** **High (Internal SoR).** Authoritative for employee department, reporting line, and manager identity.
* **Failure Modes:** Missing employee record, circular reporting lines, unmapped department names.
* **Business Decisions Supported:** Identifies requesting department (for budget check), determines direct manager (for $ \le \$1,000 $ signoff), and provides employee geographic location for cross-border privacy checks.

---

### 2.3 Department Budgets (`department_budgets.csv`)
* **Source / Path:** `data/department_budgets.csv`
* **Format:** CSV (Tabular text)
* **Purpose:** Tracks annual departmental software budget allocations, commitments, and remaining available funds.
* **Important Fields:**
  * `department` (str): Primary key (e.g., `Marketing`, `Engineering`, `Sales`, `Finance`, `Customer Success`, `Operations`).
  * `annual_software_budget_usd` (int): Total annual allocated budget.
  * `committed_usd` (int): Funds already contracted or committed.
  * `available_usd` (int): Remaining unallocated funds (`annual_software_budget_usd - committed_usd`).
* **Likely System of Record (SoR):** Enterprise Resource Planning (ERP) / Financial Planning (FP&A) (e.g., NetSuite, SAP, Anaplan).
* **Freshness / Reference Date:** Fiscal snapshot as of `2026-09-30`.
* **Authority Level:** **High (Authoritative Financial SoR).** Strict mathematical boundary for spending feasibility.
* **Failure Modes:** Missing department row, budget arithmetic inconsistencies (validated in unit tests: `available = budget - committed`).
* **Business Decisions Supported:** Informs deterministic budget check; triggers `budget_insufficient` risk flag and routes to Finance exception review if `annual_cost_usd > available_usd`.

---

### 2.4 Software Catalog (`software_catalog.csv`)
* **Source / Path:** `data/software_catalog.csv`
* **Format:** CSV (Tabular text)
* **Purpose:** Master repository of currently approved, active software products, enterprise licenses, and scopes across the company.
* **Important Fields:**
  * `software_id` (str): Primary key (e.g., `SW001` - `SW010`).
  * `product_name` (str): Approved product name (e.g., `PixelCraft Pro`, `TaskFlow`, `CodeMate`).
  * `category` (str): Software capability category (e.g., `Design & Creative`, `Developer AI`, `Observability`).
  * `vendor_name` (str): Vendor providing the software.
  * `status` (str): Approval status (e.g., `Approved`, `Approved - limited use`).
  * `annual_cost_usd` (int): Current annual contract value.
  * `licensed_seats` (int): Total licensed user capacity.
  * `scope` (str): Deployment scope (`Company-wide`, `Engineering`, `Marketing`, `Customer Success`).
  * `notes` (str): Scope descriptions, usage restrictions, and notes.
* **Likely System of Record (SoR):** IT Asset Management (ITAM) / Enterprise Architecture Repository (e.g., ServiceNow SAM, Zylo).
* **Freshness / Reference Date:** Active catalog as of `2026-09-30`.
* **Authority Level:** **High (Internal SoR).** Authoritative baseline for existing enterprise software tools.
* **Failure Modes:** Incomplete taxonomy categorization, outdated seat capacity counts.
* **Business Decisions Supported:** Evaluates software redundancy; detects overlap with requested tools; flags `existing_tool_overlap` to avoid unnecessary SaaS spend.

---

### 2.5 Vendor Registry (`vendors.csv`)
* **Source / Path:** `data/vendors.csv`
* **Format:** CSV (Tabular text)
* **Purpose:** Internal procurement vendor master record tracking onboarding, security review dates, and legal term approvals.
* **Important Fields:**
  * `vendor_id` (str): Primary key (e.g., `V001` - `V013`).
  * `vendor_name` (str): Registered company name.
  * `procurement_status` (str): Onboarding status (`Approved`, `New`).
  * `security_status` (str): Last recorded internal security status (`Approved`, `Pending`, `Unknown`).
  * `security_review_date` (str | empty): ISO date of last recorded security review (e.g., `2026-08-20` or empty).
  * `legal_terms_status` (str): State of negotiated legal terms (`Approved`, `Draft`, `Unknown`).
  * `notes` (str): Contextual remarks (e.g., *"Registry has not yet been refreshed with latest review state"*).
* **Likely System of Record (SoR):** Procurement / Vendor Management System (VMS) (e.g., Coupa, SAP Ariba).
* **Freshness / Reference Date:** Internal snapshot; subject to staleness relative to `2026-09-30`.
* **Authority Level:** **Medium (Internal Historical Record).** Can be stale or lag behind real-time risk intelligence.
* **Failure Modes:** Stale security review dates ($> 365$ days old), unrecorded recent audit outcomes, discrepancies with external API.
* **Business Decisions Supported:** Identifies whether vendor is `New` (triggering legal reviews for $\ge \$10,000$), checks existing legal terms, and provides internal security assessment dates.

---

### 2.6 Purchase History (`purchase_history.csv`)
* **Source / Path:** `data/purchase_history.csv`
* **Format:** CSV (Tabular text)
* **Purpose:** Audit ledger of past approved purchase orders, renewals, contract sizes, and purchasing departments.
* **Important Fields:**
  * `purchase_id` (str): Primary key (e.g., `PO-2401` - `PO-2531`).
  * `purchase_date` (str): ISO date of PO execution.
  * `department` (str): Purchasing department.
  * `vendor_name` (str): Vendor paid.
  * `product_name` (str): Purchased product.
  * `annual_amount_usd` (int): Historical purchase value.
  * `status` (str): Financial status (`Approved`).
  * `notes` (str): Contract scope notes.
* **Likely System of Record (SoR):** Financial Ledger / Accounts Payable (e.g., NetSuite, SAP ERP).
* **Freshness / Reference Date:** Transactional history up to `2026-09-30`.
* **Authority Level:** **High (Audited Ledger).** Authoritative historical purchase record.
* **Failure Modes:** Missing past transactions, mismatched product names.
* **Business Decisions Supported:** Confirms whether an existing commercial relationship exists; establishes precedents for renewals or expansions.

---

### 2.7 Procurement Policy (`procurement_policy.md`)
* **Source / Path:** `data/procurement_policy.md`
* **Format:** Markdown document
* **Purpose:** Corporate constitution and governance rulebook defining all procurement criteria, thresholds, security triggers, and human boundaries.
* **Important Fields / Sections:**
  * §1: Required request information.
  * §2: Department budget sufficiency check.
  * §3: Software catalog overlap criteria.
  * §4: Financial approval thresholds ($1,000 / $10,000 / $25,000 brackets).
  * §5: Information Security triggers (source code, cloud accounts, confidential docs, PII, 365-day review expiry).
  * §6: Data Privacy triggers (employee/customer PII, cross-region storage).
  * §7: Legal review triggers (new vendor $\ge \$10,000$, non-standard terms, cross-border issues).
  * §8: AI tools specific policies.
  * §9: Untrusted content and prompt injection defenses.
  * §10: Tool and evidence failure protocols.
  * §11: Human authority and non-autonomous operation.
* **Likely System of Record (SoR):** Corporate Policy & Compliance Portal (e.g., Confluence, PolicyTech).
* **Freshness / Reference Date:** Version 2026.09; snapshot date `2026-09-30`.
* **Authority Level:** **Absolute Sovereign Authority.** Highest precedence in the entire architecture.
* **Failure Modes:** Ambiguity in natural language (resolved via deterministic code rules).
* **Business Decisions Supported:** Dictates all logic gates, risk flags, and required approvers across the copilot.

---

### 2.8 External Vendor Risk API (`mock_api/app.py` / `data/vendor_risk.json`)
* **Source / Path:** REST API endpoint `GET /vendor-risk/{vendor_name}` (backed by `data/vendor_risk.json` and client `src/vendor_client.py`).
* **Format:** HTTP REST JSON
* **Purpose:** Real-time external third-party vendor risk and cybersecurity intelligence service.
* **Important Fields:**
  * `risk_level` (str): Overall external risk assessment (`low`, `medium`, `high`).
  * `security_review_status` (str): External security audit status (`approved`, `expired`, `not_completed`).
  * `last_review_date` (str | null): ISO date of the last external audit (e.g., `2026-06-20`, `2025-07-01`, or `null`).
  * `processes_personal_data` (bool): Whether vendor systems process personal identifiable information.
  * `stores_data_outside_region` (bool): Whether vendor stores/replicates data outside the primary corporate region.
  * `notes` (str): Evaluator findings and restrictions.
  * `force_error` (bool): Simulation field that triggers HTTP 503 Service Unavailable (e.g., for `NimbusAI`).
* **Likely System of Record (SoR):** External Third-Party Risk Management (TPRM) Platform (e.g., SecurityScorecard, BitSight, OneTrust).
* **Freshness / Reference Date:** Live service reflecting state as of snapshot date `2026-09-30`.
* **Authority Level:** **High External Evidence.** Primary signal for technical risk, assessment freshness, and cross-border data storage.
* **Failure Modes:** HTTP 503 outage, network timeout, 404 for unrated vendors.
* **Business Decisions Supported:** Triggers `vendor_risk_unavailable` on failure; triggers `vendor_review_expired` if `last_review_date` is $> 365$ days old or status is `expired`; triggers `conflicting_vendor_evidence` if conflicting with `vendors.csv`; triggers `privacy_review_required` and `legal_review_required` if `stores_data_outside_region: true`.

---

## 3. Data Source Decision Support Matrix

| Data Source | Completeness Gate | Budget Feasibility | Catalog Overlap | Financial Tier | Security Review | Privacy Review | Legal Review |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `requests.json` | **Primary** | Input Cost | Category/Vendor | Input Spend | Access Level | Data Level | Vendor / Spend |
| `employees.csv` | ForeignKey | Dept Lookup | - | Manager Lookup| - | Country | - |
| `department_budgets.csv`| - | **Primary** | - | - | - | - | - |
| `software_catalog.csv` | - | - | **Primary** | - | - | - | - |
| `vendors.csv` | - | - | Vendor Match | - | Internal Date | - | Status / Terms |
| `purchase_history.csv` | - | - | Historical POs | - | - | - | Historical Rel |
| `procurement_policy.md`| Policy Rules | Policy Rules | Policy Rules | **Thresholds** | **Triggers** | **Triggers** | **Triggers** |
| Vendor Risk API | - | - | - | - | **External Stat** | **Cross-Region**| **Cross-Region**|
