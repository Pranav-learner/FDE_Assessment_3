# 05. Business Rules: AI Procurement Request Copilot

**Document Version:** 1.0.0  
**Status:** Baseline Specification (Phase 1 Source of Truth)  
**Policy Source:** `data/procurement_policy.md` (Version 2026.09)  
**Evaluation Reference Date:** `2026-09-30`  
**Author:** Forward Deployed Engineering (FDE)

---

## 1. Classification Methodology

Every business rule in the procurement copilot is classified into one of three execution categories:

* **[DETERMINISTIC CODE]:** The rule is strictly computational, logical, or arithmetic. It has exact mathematical boundaries, set memberships, or boolean criteria. **It MUST be implemented in deterministic Python code** without LLM involvement to guarantee 100% repeatability, zero hallucination, and auditable precision.
* **[MODEL-DRIVEN]:** The rule requires semantic reasoning, natural language interpretation, fuzzy matching, or contextual summarization (e.g., comparing qualitative business justifications against catalog capability descriptions, identifying adversarial injection attempts).
* **[HUMAN-IN-THE-LOOP]:** The rule governs an authority boundary that must be decided, signed, or waived exclusively by a human stakeholder.

---

## 2. Structured Policy Rule Table

| Rule ID | Policy Domain | Business Condition | Classification | Input Evidence | Expected Output | Risk Flag Triggered | Required Approvals / Reviews | Source Section |
|---|---|---|:---:|---|---|:---:|---|:---:|
| **BR-01** | Completeness | Any mandatory field missing or null: `requester_id`, `product_name`, `vendor_name`, `annual_cost_usd`, `user_count`, `business_justification`, or `data_access_level`. | **DETERMINISTIC CODE** | `requests.json` fields | Request blocked from approval; list missing items; recommend clarification. | `missing_information` | Procurement (Triage) | §1 |
| **BR-02** | Budget Sufficiency | `annual_cost_usd` $\le$ `available_usd` for requesting department (`annual_software_budget - committed`). | **DETERMINISTIC CODE** | `requests.json`, `department_budgets.csv` | Budget check passes; continue pipeline. | *(None)* | Standard per tier | §2 |
| **BR-03** | Budget Deficit | `annual_cost_usd` $>$ `available_usd` for requesting department. | **DETERMINISTIC CODE** | `requests.json`, `department_budgets.csv` | Flag budget deficit; route for budget exception. | `budget_insufficient` | Finance (Exception Review) | §2 |
| **BR-04** | Overlap: Catalog Match | Requested product name, vendor name, or functional category matches an active entry in `software_catalog.csv`. | **DETERMINISTIC CODE** + **MODEL** | `software_catalog.csv`, `requests.json` | Surface catalog alternative(s), seat counts, and scope; analyze stated justification gap. | `existing_tool_overlap` | Department Head / Procurement | §3 |
| **BR-05A**| Financial Tier 1 | `annual_cost_usd` $\le \$1,000.00$ | **DETERMINISTIC CODE** | `requests.json` (`annual_cost_usd`) | Route to Direct Manager. | *(None)* | `Manager` | §4 |
| **BR-05B**| Financial Tier 2 | $\$1,000.00 < \text{cost} \le \$10,000.00$ (e.g. $\$1,000.01$ to $\$10,000.00$) | **DETERMINISTIC CODE** | `requests.json` (`annual_cost_usd`) | Route to Department Head and Procurement. | *(None)* | `Department Head`, `Procurement` | §4 |
| **BR-05C**| Financial Tier 3 | $\$10,000.00 < \text{cost} \le \$25,000.00$ (e.g. $\$10,000.01$ to $\$25,000.00$) | **DETERMINISTIC CODE** | `requests.json` (`annual_cost_usd`) | Route to Dept Head, Finance, and Procurement. | *(None)* | `Department Head`, `Finance`, `Procurement` | §4 |
| **BR-05D**| Financial Tier 4 | `annual_cost_usd` $> \$25,000.00$ (e.g. $\$25,000.01+$) | **DETERMINISTIC CODE** | `requests.json` (`annual_cost_usd`) | Route to Dept Head, Finance, CFO, and Procurement. | *(None)* | `Department Head`, `Finance`, `CFO`, `Procurement` | §4 |
| **BR-06** | Security: Sensitive Data | `data_access_level` $\in$ {`source_code`, `production_telemetry`, `confidential_documents`, `employee_pii`, `customer_pii`, `credentials`} OR `requested_integrations` contains production cloud, git repositories, or secrets. | **DETERMINISTIC CODE** | `requests.json` (`data_access_level`, `requested_integrations`) | Trigger mandatory InfoSec evaluation. | `security_review_required` | `Security` | §5 |
| **BR-07** | Security: Missing Vendor Review | Vendor security assessment is missing, null, or status is `not_completed` / `Pending` in `vendors.csv` or Vendor Risk API. | **DETERMINISTIC CODE** | `vendors.csv`, Vendor Risk API | Trigger mandatory InfoSec evaluation. | `security_review_required` | `Security` | §5 |
| **BR-08** | Security: Expired Review | Vendor security review date is $> 365$ days before reference date `2026-09-30` (i.e. `review_date < 2025-09-30`) OR API status is `expired`. | **DETERMINISTIC CODE** | `vendors.csv`, Vendor Risk API, reference date `2026-09-30` | Trigger vendor reassessment requirement. | `vendor_review_expired`, `security_review_required` | `Security` | §5 |
| **BR-09** | Security: Conflicting Signals | `vendors.csv` and Vendor Risk API report conflicting security statuses (e.g. registry says `Approved` but API says `expired` or `medium`). | **DETERMINISTIC CODE** | `vendors.csv` vs. Vendor Risk API | Surface discrepancy transparently; do not choose one silently. | `conflicting_vendor_evidence`, `security_review_required` | `Security` | §5 |
| **BR-10** | Privacy: PII Processing | `data_access_level` $\in$ {`employee_pii`, `customer_pii`} OR Vendor Risk API `processes_personal_data: true`. | **DETERMINISTIC CODE** | `requests.json`, Vendor Risk API | Trigger mandatory DPO data privacy audit. | `privacy_review_required` | `Privacy` | §6 |
| **BR-11** | Privacy: Cross-Region | Vendor Risk API reports `stores_data_outside_region: true`. | **DETERMINISTIC CODE** | Vendor Risk API | Trigger cross-border transfer review. | `privacy_review_required`, `legal_review_required` | `Privacy`, `Legal` | §6, §7 |
| **BR-12** | Legal: New Vendor Spend | Vendor `procurement_status == "New"` AND `annual_cost_usd` $\ge \$10,000.00$. | **DETERMINISTIC CODE** | `vendors.csv`, `requests.json` | Trigger contract drafting and negotiation review. | `legal_review_required` | `Legal` | §7 |
| **BR-13** | Legal: Unapproved Terms | Vendor `legal_terms_status` $\in$ {`Draft`, `Unknown`, `None`} in `vendors.csv`. | **DETERMINISTIC CODE** | `vendors.csv` | Trigger corporate legal terms verification. | `legal_review_required` | `Legal` | §7 |
| **BR-14** | AI Governance | Requested software category is `Developer AI`, `General AI`, or product utilizes generative LLM capabilities. | **MODEL-DRIVEN** + **CODE** | `requests.json` (`category`, `product_name`), `procurement_policy.md` | Apply strict data class controls; existing general approvals do not cover code/PII. | *(Triggers BR-06/BR-10 as applicable)* | `Security`, `Privacy` (if sensitive data) | §8 |
| **BR-15** | Prompt Injection Defense | Request text contains instructions to ignore policy, bypass approvals, self-approve, or alter system behavior. | **MODEL-DRIVEN** | `requests.json` (`business_justification`, notes) | Treat text as untrusted business data; strip instruction; continue normal policy evaluation. | `prompt_injection_detected` | Standard per policy | §9 |
| **BR-16** | Evidence Resilience | Vendor Risk API returns HTTP 503, connection timeout, or 404. | **DETERMINISTIC CODE** | `src/vendor_client.py` exception | Do not assume low risk; log unverified status; route to manual InfoSec audit. | `vendor_risk_unavailable`, `security_review_required` | `Security` | §10 |
| **BR-17** | Human Authority Gate | All requests without exception must return `human_review_required: true`. Copilot never makes binding decisions. | **DETERMINISTIC CODE** | Output constructor | Force advisory status; attach required approval roster. | *(None)* | Human signoff always preserved | §11 |

---

## 3. Strict Boundary Condition Analysis

Precise boundary values are defined in Section 4 of the Procurement Policy. These thresholds must use exact strict inequality and inclusion logic:

```python
# Formal Deterministic Specification for Financial Approval Tiers:
if annual_cost <= 1000.00:
    base_approvals = ["Manager"]
elif 1000.00 < annual_cost <= 10000.00:
    base_approvals = ["Department Head", "Procurement"]
elif 10000.00 < annual_cost <= 25000.00:
    base_approvals = ["Department Head", "Finance", "Procurement"]
else:  # annual_cost > 25000.00
    base_approvals = ["Department Head", "Finance", "CFO", "Procurement"]
```

### Boundary Test Points Table

| Test Amount | Boundary Significance | Resulting Financial Approvals | Notes / Edge Context |
|---|---|---|---|
| **$950.00** | Well within Tier 1 | `["Manager"]` | REQ-1010 SignFlow Training Pack |
| **$1,000.00** | **Exact Tier 1 Boundary** | `["Manager"]` | "Up to $1,000" inclusive |
| **$1,000.01** | **Exact Tier 2 Floor** | `["Department Head", "Procurement"]` | Exceeds $1,000; triggers Dept Head + Procurement |
| **$8,000.00** | Within Tier 2 | `["Department Head", "Procurement"]` | REQ-1008 TaskFlow Pro |
| **$10,000.00** | **Exact Tier 2 Ceiling** | `["Department Head", "Procurement"]` | "$1,000.01 - $10,000" inclusive. If New Vendor, triggers Legal! |
| **$10,000.01** | **Exact Tier 3 Floor** | `["Department Head", "Finance", "Procurement"]` | Exceeds $10,000; triggers Finance |
| **$12,000.00** | Within Tier 3 | `["Department Head", "Finance", "Procurement"]` | REQ-1002 BrandBoard Enterprise |
| **$24,000.00** | Within Tier 3 | `["Department Head", "Finance", "Procurement"]` | REQ-1007 SignalWatch Advanced |
| **$25,000.00** | **Exact Tier 3 Ceiling** | `["Department Head", "Finance", "Procurement"]` | "$10,000.01 - $25,000" inclusive |
| **$25,000.01** | **Exact Tier 4 Floor** | `["Department Head", "Finance", "CFO", "Procurement"]` | "Above $25,000"; triggers CFO |
| **$50,000.00** | Within Tier 4 | `["Department Head", "Finance", "CFO", "Procurement"]` | High-value contract |

---

## 4. Vendor Assessment Date Freshness Logic

The policy specifies:
> *"A vendor security assessment is considered current for 365 days from its review date."*

* **Reference Snapshot Date:** `2026-09-30`
* **Calculation:**
  $$\Delta_{\text{days}} = (\text{date}(2026, 9, 30) - \text{review\_date}).\text{days}$$
* **Evaluation Condition:**
  $$\Delta_{\text{days}} > 365 \implies \text{EXPIRED}$$
* **Threshold Reference:**
  $$2026\text{-}09\text{-}30 - 365\text{ days} = 2025\text{-}09\text{-}30$$
  * Any review date **on or before `2025-09-30`** is **EXPIRED** (e.g. `SignalWatch` with review date `2025-07-01` is 456 days old $\implies$ Expired).
  * Any review date **after `2025-09-30`** (e.g., `2026-01-18`, `2026-08-20`) is **CURRENT**.
  * A null or missing review date for a new vendor is **NOT COMPLETED** $\implies$ Triggers `security_review_required`.

---

## 5. Additive Approval Aggregation Logic

Financial approvals represent the baseline approval roster. Governance reviews (Security, Privacy, Legal) are added to the list whenever corresponding risk triggers fire:

$$\text{Final Approvals} = \text{Base Financial Approvals} \cup \text{Security Approvals} \cup \text{Privacy Approvals} \cup \text{Legal Approvals}$$

```python
approvals = set(base_financial_approvals)
if "security_review_required" in risk_flags or "vendor_review_expired" in risk_flags:
    approvals.add("Security")
if "privacy_review_required" in risk_flags:
    approvals.add("Privacy")
if "legal_review_required" in risk_flags:
    approvals.add("Legal")
if "budget_insufficient" in risk_flags:
    approvals.add("Finance")
```

This guarantees that security, compliance, legal, and financial governance teams are never excluded from high-risk purchase flows.
