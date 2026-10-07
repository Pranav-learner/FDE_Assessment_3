# 10. Data Model & Entities Specification: AI Procurement Request Copilot

**Document Version:** 1.0.0  
**Phase:** Phase 2 (Data Foundation & Tool Contracts)  
**Evaluation Reference Date:** `2026-09-30`  
**Author:** Forward Deployed Engineering (FDE)

---

## 1. Overview & Source of Truth

This document defines the core data model, entity schemas, relationships, and systems of record powering the deterministic layer and future agent layers of the AI Procurement Request Copilot.

### 1.1 Authoritative Sources of Truth
1. **Governance & Thresholds:** `data/procurement_policy.md` (Version 2026.09, Reference Date `2026-09-30`).
2. **Organizational & HR Data:** `data/employees.csv`.
3. **Department Financials:** `data/department_budgets.csv`.
4. **Software Catalog:** `data/software_catalog.csv`.
5. **Vendor Registry:** `data/vendors.csv`.
6. **Historical Spend:** `data/purchase_history.csv`.
7. **External Risk Intelligence:** Vendor Risk REST API (`GET /vendor-risk/{vendor_name}`).
8. **Intake Requests:** `data/requests.json`.

---

## 2. Entity Relationship Diagram

```text
       +-----------------------+                +-----------------------+
       |     employees.csv     |                | department_budgets.csv|
       +-----------------------+                +-----------------------+
       | employee_id (PK)      |                | department (PK)       |
       | name                  |                | annual_budget_usd     |
       | department (FK) ------+-------+        | committed_usd         |
       | manager_id (FK)       |       |        | available_usd         |
       | level                 |       |        +-----------+-----------+
       | country               |       |                    |
       +-----------+-----------+       |                    |
                   |                   +--------+           |
                   |                            |           |
                   v                            v           v
       +-----------------------+        +-------------------------------+
       |     requests.json     |        |      RequestContext (Model)   |
       +-----------------------+        +-------------------------------+
       | request_id (PK)       |        | request: dict                 |
       | requester_id (FK) ----+------->| requester: dict               |
       | product_name          |        | department: str               |
       | vendor_name (FK) -----+--+     | manager: dict | None          |
       | category              |  |     | budget: dict                  |
       | annual_cost_usd       |  |     | evidence: list[EvidenceItem]  |
       | user_count            |  |     +---------------+---------------+
       | business_justification|  |                     |
       | data_access_level     |  |                     |
       | requested_integrations|  |                     |
       +-----------------------+  |                     |
                                  |                     v
                                  |     +-------------------------------+
                                  |     |    Deterministic Rule Engine  |
                                  |     +-------------------------------+
                                  |                     |
          +-----------------------+                     |
          |                                             |
          v                                             v
+-----------------------+   +-----------------------+   |
|      vendors.csv      |   |   Vendor Risk API     |   |
+-----------------------+   +-----------------------+   |
| vendor_id (PK)        |   | risk_level            |   |
| vendor_name           |   | security_status       |   |
| procurement_status    |   | last_review_date      |   |
| security_status       |   | processes_personal_data   |
| security_review_date  |   | stores_outside_region |   |
| legal_terms_status    |   +-----------+-----------+   |
+-----------+-----------+               |               |
            |                           |               |
            +-------------+-------------+               |
                          |                             |
                          v                             v
            +---------------------------+   +---------------------------+
            |  VendorRiskProfile (Model)|   | RuleEvaluationResult      |
            +---------------------------+   +---------------------------+
            | verified: bool            |   | is_valid: bool            |
            | risk_level: str           |   | missing_information: list |
            | security_status: str      |   | risk_flags: list          |
            | date_staleness: int       |   | required_approvals: list  |
            | outside_region: bool      |   | evidence: list            |
            | error: str | None         |   | human_review_required=True|
            +---------------------------+   +---------------------------+
```

---

## 3. Data Entities & Attribute Definitions

### 3.1 Inbound Purchase Request (`requests.json`)
* **`request_id` (string, PK):** Unique request identifier (e.g., `REQ-1001`).
* **`requester_id` (string, FK):** Maps to `employees.employee_id`.
* **`product_name` (string):** Name of requested software, add-on, or service.
* **`vendor_name` (string):** Name of external vendor or publisher.
* **`category` (string):** Functional market segment (e.g., `Developer AI`, `E-signature`).
* **`annual_cost_usd` (float | null):** Annualized contract value in USD.
* **`user_count` (int | null):** Number of authorized seats/licenses.
* **`business_justification` (string):** Requester's explanation of need (untrusted text; potential prompt injection site).
* **`data_access_level` (string):** Sensitivity classification (`internal_documents`, `source_code`, `customer_pii`, `unknown`).
* **`requested_integrations` (list[string]):** Connected enterprise systems (e.g., `Git repositories`, `SSO`, `Production cloud account`).
* **`urgency` (string):** Operational priority assertion (`normal`, `high`, `urgent`).

### 3.2 Employee Directory (`employees.csv`)
* **`employee_id` (string, PK):** Primary employee key (e.g., `E001`).
* **`name` (string):** Full employee name.
* **`department` (string, FK):** Maps to `department_budgets.department`.
* **`manager_id` (string | null, FK):** Self-referencing key to manager's `employee_id`.
* **`level` (string):** Job level (`IC3`, `IC4`, `IC5`, `Director`, `VP`).
* **`country` (string):** Physical employee location (`India`, `United Kingdom`, `United States`, `Spain`, `Singapore`).

### 3.3 Department Budget (`department_budgets.csv`)
* **`department` (string, PK):** Department name.
* **`annual_software_budget_usd` (int):** Total fiscal year software allocation.
* **`committed_usd` (int):** Already contracted software spend.
* **`available_usd` (int):** Remaining uncommitted funds ($ \text{annual\_budget} - \text{committed} $).

### 3.4 Software Catalog (`software_catalog.csv`)
* **`software_id` (string, PK):** Catalog asset identifier (e.g., `SW001`).
* **`product_name` (string):** Approved tool name.
* **`category` (string):** Functional category.
* **`vendor_name` (string):** Vendor entity.
* **`status` (string):** State of approval (`Approved`, `Approved - limited use`).
* **`annual_cost_usd` (int):** Active annual contract value.
* **`licensed_seats` (int):** Provisioned user seats.
* **`scope` (string):** Departmental or company-wide license scope (`Company-wide`, `Engineering`, `Marketing`, `Customer Success`).
* **`notes` (string):** Restrictions, data boundaries, or use-case notes.

### 3.5 Vendor Master Registry (`vendors.csv`)
* **`vendor_id` (string, PK):** Vendor key (e.g., `V001`).
* **`vendor_name` (string):** Company name.
* **`procurement_status` (string):** Onboarding state (`Approved`, `New`).
* **`security_status` (string):** Recorded security status (`Approved`, `Pending`, `Unknown`).
* **`security_review_date` (string | null):** ISO date of last recorded review.
* **`legal_terms_status` (string):** State of terms (`Approved`, `Draft`, `Unknown`).
* **`notes` (string):** Operational notes.

### 3.6 External Vendor Risk Profile (Mock API)
* **`risk_level` (string):** Overall third-party risk level (`low`, `medium`, `high`).
* **`security_review_status` (string):** Live security audit state (`approved`, `expired`, `not_completed`).
* **`last_review_date` (string | null):** ISO date of external assessment.
* **`processes_personal_data` (bool):** Whether third-party systems ingest PII.
* **`stores_data_outside_region` (bool):** Whether vendor stores data across international borders.
* **`notes` (string):** Assessment findings.
* **`force_error` (bool | null):** Simulates 503 outage.

---

## 4. Evidence Model: Structured `EvidenceItem`

All factual findings gathered by tools or generated by the deterministic engine are represented using the standardized `EvidenceItem` contract:

```python
class EvidenceItem(BaseModel):
    source: str = Field(description="Tool or underlying data source name")
    finding: str = Field(description="Concise factual finding")
    reference: str | None = Field(default=None, description="Record ID, policy section, or endpoint")
```

### Traceability Guarantee
Every recommendation in the final output must cite verifiable evidence items linking directly to:
* Specific records in `requests.json`
* Exact employee rows in `employees.csv`
* Mathematical budget lines in `department_budgets.csv`
* Overlap rows in `software_catalog.csv`
* Live responses from `vendor-risk-api`
* Explicit sections in `procurement_policy.md`
