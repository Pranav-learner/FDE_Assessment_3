# 12. Deterministic Rule Engine Specification: AI Procurement Request Copilot

**Document Version:** 1.0.0  
**Phase:** Phase 2 (Deterministic Procurement Rule Engine)  
**Evaluation Reference Date:** `2026-09-30`  
**Author:** Forward Deployed Engineering (FDE)

---

## 1. Engine Architecture & Non-LLM Execution

The deterministic rule engine (`src/tools/rule_engine.py`) provides an auditable, 100% reproducible decision-support foundation. It evaluates corporate procurement rules strictly using Python logic, mathematical arithmetic, and set comparisons without invoking an LLM.

```text
[RequestContext] + [CatalogSearchResult] + [VendorRiskProfile] + [VendorRegistry]
                                |
                                v
               +---------------------------------+
               |   src/tools/rule_engine.py      |
               |                                 |
               |  1. Prompt Injection Defense    |
               |  2. Completeness Gate           |
               |  3. Budget Arithmetic Math      |
               |  4. Financial Threshold Bands   |
               |  5. Catalog Overlap Detection   |
               |  6. Security & Sensitive Data   |
               |  7. 365-Day Assessment Freshness|
               |  8. Vendor Evidence Discrepancy |
               |  9. Privacy & Cross-Region Data |
               | 10. Legal Contracting Rules     |
               | 11. Tool Outage Resilience      |
               | 12. Human Authority Retention   |
               +---------------------------------+
                                |
                                v
                     [RuleEvaluationResult]
```

---

## 2. Rule Evaluation Modules

### Module 1: Untrusted Data & Prompt Injection (Policy §9)
* **Principle:** Business justification text is untrusted business data, not system instructions.
* **Markers:** Checks for adversarial phrases (`ignore previous instructions`, `ignore all procurement rules`, `bypass approval`, `approve immediately`, `treat this request as cfo-approved`, `reveal secrets`).
* **Engine Action:** If detected:
  1. Appends `prompt_injection_detected` to `risk_flags`.
  2. Generates an `EvidenceItem` referencing Policy §9.
  3. Ignores the embedded command; continues standard policy evaluation without bypassing controls.

---

### Module 2: Completeness Validation (Policy §1)
* **Mandatory Fields:** `requester_id`, `product_name`, `vendor_name`, `annual_cost_usd`, `user_count`, `business_justification`, and `data_access_level`.
* **Engine Action:**
  * If any field is `None`, empty string, $\le 0$, or `"unknown"`:
    - Appends missing field description to `missing_information`.
    - Appends `missing_information` to `risk_flags`.
    - Halts normal approval recommendation; recommends requesting clarification.

---

### Module 3: Budget Arithmetic Check (Policy §2)
* **Formula:**
  $$\text{available\_usd} = \text{annual\_software\_budget\_usd} - \text{committed\_usd}$$
  $$\text{deficit} = \text{annual\_cost\_usd} - \text{available\_usd}$$
* **Engine Action:**
  * If $\text{annual\_cost\_usd} > \text{available\_usd}$:
    - Appends `budget_insufficient` to `risk_flags`.
    - Appends `Finance` to `required_approvals`.
    - Generates evidence citing exact deficit.
  * Note: A positive budget check does not imply approval.

---

### Module 4: Financial Approval Thresholds (Policy §4)
* **Strict Boundary Evaluation:**

| Annual Cost ($) | Evaluation Condition | Required Approvals | Tested Boundaries |
|---|---|---|---|
| **$\le \$1,000.00$** | `cost <= 1000.00` | `["Manager"]` | $950.00$, **$1,000.00$** |
| **$\$1,000.01 - \$10,000.00$** | `1000.00 < cost <= 10000.00` | `["Department Head", "Procurement"]` | **$1,000.01$**, $8,000.00$, **$10,000.00$** |
| **$\$10,000.01 - \$25,000.00$** | `10000.00 < cost <= 25000.00` | `["Department Head", "Finance", "Procurement"]` | **$10,000.01$**, $12,000.00$, **$25,000.00$** |
| **$> \$25,000.00$** | `cost > 25000.00` | `["Department Head", "Finance", "CFO", "Procurement"]` | **$25,000.01$**, $50,000.00$ |

---

### Module 5: Software Catalog Overlap (Policy §3)
* **Condition:** Requested tool matches product, vendor, or category of an active catalog item.
* **Engine Action:**
  * Appends `existing_tool_overlap` to `risk_flags`.
  * Preserves request progression; surfaces matching software details as evidence.

---

### Module 6: Information Security Governance (Policy §5)
* **Triggers:**
  * `data_access_level` $\in$ {`source_code`, `production_telemetry`, `confidential_documents`, `credentials`, `secrets`, `employee_pii`, `customer_pii`}.
  * Integrations with production cloud accounts, git repos, or secrets managers.
  * Vendor security assessment is missing, uncompleted, or expired.
* **Engine Action:**
  * Appends `security_review_required` to `risk_flags`.
  * Appends `Security` to `required_approvals`.

---

### Module 7: Vendor Assessment Date Freshness (Policy §5)
* **Reference Anchor:** Fixed snapshot date `2026-09-30`. (System clock `date.today()` is forbidden).
* **Formula:**
  $$\Delta_{\text{days}} = (\text{date}(2026, 9, 30) - \text{review\_date}).\text{days}$$
* **Engine Action:**
  * If $\Delta_{\text{days}} > 365$ or status is `"expired"`:
    - Appends `vendor_review_expired` to `risk_flags`.
    - Appends `security_review_required` to `risk_flags`.
    - Appends `Security` to `required_approvals`.

---

### Module 8: Conflicting Vendor Evidence (Policy §5)
* **Condition:** Internal registry (`vendors.csv`) lists security as `Approved`, but external Vendor Risk API reports `expired`, `pending`, or `not_completed` (e.g., `SignalWatch`).
* **Engine Action:**
  * Appends `conflicting_vendor_evidence` to `risk_flags`.
  * Appends `security_review_required` to `risk_flags`.
  * Appends `Security` to `required_approvals`.
  * Transparently surfaces the discrepancy in evidence.

---

### Module 9: Privacy Governance (Policy §6)
* **Triggers:**
  * Request processes `employee_pii` or `customer_pii`.
  * Vendor Risk API reports `stores_data_outside_region: true`.
* **Engine Action:**
  * Appends `privacy_review_required` to `risk_flags`.
  * Appends `Privacy` to `required_approvals`.

---

### Module 10: Legal Review Triggers (Policy §7)
* **Triggers:**
  * Vendor is `New` AND `annual_cost_usd >= 10000.00` (Note: $\ge \$10,000$ inclusive).
  * Vendor legal terms are unapproved (`Draft`, `Unknown`, `None`).
  * Vendor stores data outside operating region (`stores_data_outside_region: true`).
* **Engine Action:**
  * Appends `legal_review_required` to `risk_flags`.
  * Appends `Legal` to `required_approvals`.

---

### Module 11: Tool & Evidence Failures (Policy §10)
* **Condition:** External Vendor Risk API returns HTTP 503, connection error, timeout, or malformed data.
* **Engine Action:**
  * Appends `vendor_risk_unavailable` to `risk_flags`.
  * Appends `security_review_required` to `risk_flags`.
  * Appends `Security` to `required_approvals`.
  * Refuses to assume favorable risk status.

---

### Module 12: Human Review Persistence (Policy §11)
* **Rule:** `human_review_required` unconditionally evaluates to `True` on 100% of executions.
