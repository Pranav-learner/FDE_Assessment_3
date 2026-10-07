# 16. Decision Precedence & Conflict Resolution: AI Procurement Request Copilot

**Document Version:** 1.0.0  
**Phase:** Phase 3 (Decision Precedence)  
**Author:** Forward Deployed Engineering (FDE)

---

## 1. Multi-Criteria Precedence Hierarchy

In enterprise procurement triage, multiple conflicting signals can arise simultaneously: an incomplete request might also contain prompt injection, an overlapping software request might also exceed available department budget, or a vendor risk API might be unavailable on a high-value purchase.

To ensure consistent, non-arbitrary outcomes across all requests, the Decision Engine executes a strict four-tiered priority precedence ladder:

```text
+-------------------------------------------------------------------------------+
| PRIORITY 1: Material Required Information Missing (Policy §1)                |
| -> Recommendation: NEEDS_INFORMATION                                          |
| -> Next Step: Request missing fields from employee                            |
+-------------------------------------------------------------------------------+
                                        |
                               (Complete Inputs)
                                        v
+-------------------------------------------------------------------------------+
| PRIORITY 2: Material Evidence Unavailable or Conflicting (Policy §§5, 10)     |
| -> Recommendation: MANUAL_REVIEW                                              |
| -> Next Step: Manual InfoSec verification / record reconciliation             |
+-------------------------------------------------------------------------------+
                                        |
                             (Verified Evidence)
                                        v
+-------------------------------------------------------------------------------+
| PRIORITY 3: Governance Reviews Triggered (Policy §§2, 3, 5, 6, 7)             |
| -> Recommendation: PROCEED_TO_REVIEW                                          |
| -> Next Step: Route to Finance, Security, Privacy, and Legal                  |
+-------------------------------------------------------------------------------+
                                        |
                              (Clean Governance)
                                        v
+-------------------------------------------------------------------------------+
| PRIORITY 4: Standard Financial Approval Path (Policy §4)                      |
| -> Recommendation: PROCEED_TO_REVIEW                                          |
| -> Next Step: Route to Direct Manager                                         |
+-------------------------------------------------------------------------------+
```

---

## 2. Priority Details & Concrete Rationale

### Priority 1: Missing Material Information $\longrightarrow$ `NEEDS_INFORMATION`
* **Condition:** `len(rule_result.missing_information) > 0`
* **Trigger Fields:** `annual_cost_usd` is null, `user_count` is null, `data_access_level` is null or `"unknown"`, `business_justification` is blank.
* **Why It Dominates:** Without cost, seat counts, and data access tiers, it is mathematically impossible to evaluate budget sufficiency, financial threshold tiers, or security data boundaries. Calculating approvals on incomplete data creates severe compliance exposure.
* **Action:** Halts progression; instructs specialist to request missing fields from the requester.

---

### Priority 2: Unverified or Conflicting Evidence $\longrightarrow$ `MANUAL_REVIEW`
* **Condition:** `"vendor_risk_unavailable" in risk_flags` OR `"conflicting_vendor_evidence" in risk_flags`.
* **Triggers:**
  * External Vendor Risk API throws HTTP 503, connection error, or timeout.
  * Internal vendor registry (`vendors.csv`) lists vendor security as `Approved`, but external risk API reports `expired`, `pending`, or `not_completed` (e.g. `SignalWatch`).
* **Why It Dominates Priority 3/4:** Under Policy §10, the copilot must **never infer favorable status** when evidence is missing. If vendor risk posture cannot be verified or internal records contradict third-party signals, automated progression is unsafe.
* **Action:** Routes case to InfoSec and Procurement Operations for manual audit.

---

### Priority 3: Governance Reviews Required $\longrightarrow$ `PROCEED_TO_REVIEW`
* **Condition:** Complete, verified request triggers one or more specialized governance gates:
  * Budget shortfall $\rightarrow$ `budget_insufficient` (Routes to `Finance`)
  * Sensitive data / integrations / expired review $\rightarrow$ `security_review_required` (Routes to `Security`)
  * PII or cross-region storage $\rightarrow$ `privacy_review_required` (Routes to `Privacy`)
  * New vendor $\ge \$10,000$ or unapproved terms $\rightarrow$ `legal_review_required` (Routes to `Legal`)
  * Catalog alternative detected $\rightarrow$ `existing_tool_overlap` (Routes to `Dept Head` & `Procurement`)
  * Prompt injection detected $\rightarrow$ `prompt_injection_detected` (Maintains full standard review)
* **Action:** Assembles the additive union of all required approvers and instructs: *"Route the request to [Approvers] for the required governance reviews and approvals."*

---

### Priority 4: Standard Low-Value Approval Path $\longrightarrow$ `PROCEED_TO_REVIEW`
* **Condition:** Request is complete, within available budget, spend is $\le \$1,000.00$, vendor review is current, data access is non-sensitive, and no overlaps exist.
* **Action:** Assembles baseline financial approval: `required_approvals: ["Manager"]`. Instructs: *"Route the request to Manager for standard business approval."*

---

## 3. Precedence Applied Across Public Cases

| Case | Request ID | Dominant Precedence Tier | Outcome State | Primary Drivers |
|---|---|:---:|:---:|---|
| **PUB-01** | `REQ-1001` | **Priority 4** | `PROCEED_TO_REVIEW` | Clean add-on, $800, Manager only signoff |
| **PUB-02** | `REQ-1002` | **Priority 3** | `PROCEED_TO_REVIEW` | Overlap with PixelCraft, $12k new vendor, draft legal terms, pending security |
| **PUB-03** | `REQ-1003` | **Priority 3** | `PROCEED_TO_REVIEW` | Source-code access and Git integration requires Security review |
| **PUB-04** | `REQ-1005` | **Priority 3** | `PROCEED_TO_REVIEW` | Budget shortfall ($22k > $18k), customer PII, cross-region storage |
| **PUB-05** | `REQ-1006` | **Priority 1** | `NEEDS_INFORMATION` | Missing cost, seats, and data access level (Jailbreak attempt neutralized) |
| **PUB-06** | `REQ-1009` | **Priority 2** | `MANUAL_REVIEW` | External vendor risk API outage (HTTP 503 on NimbusAI) |
