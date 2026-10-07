# 14. Deterministic Decision Engine: AI Procurement Request Copilot

**Document Version:** 1.0.0  
**Phase:** Phase 3 (Deterministic Procurement Decision Engine)  
**Evaluation Reference Date:** `2026-09-30`  
**Author:** Forward Deployed Engineering (FDE)

---

## 1. Distinction: Rule Engine vs. Decision Engine

In enterprise Forward Deployed Engineering, confusing rule evaluation with decision aggregation leads to brittle architectures. We explicitly separate these two responsibilities:

* **Phase 2 (The Rule Engine - `src/tools/rule_engine.py`):**
  * Evaluates individual business and compliance rules in isolation.
  * Checks specific conditions: Is cost within available budget? Is review age $> 365$ days? Does vendor have draft legal terms?
  * Produces granular boolean flags and raw lists: `risk_flags`, `missing_information`, individual approval triggers.
* **Phase 3 (The Decision Engine - `src/decision_engine.py`):**
  * Answers the operational synthesis question: **"What should Procurement do next based strictly on the available evidence and deterministic policy results?"**
  * Implements deterministic multi-criteria precedence across conflicting or overlapping rule findings.
  * Maps findings to a small controlled recommendation vocabulary (`NEEDS_INFORMATION`, `MANUAL_REVIEW`, `PROCEED_TO_REVIEW`).
  * Aggregates, deduplicates, and structures all evidence items into an auditable dossier.
  * Formulates precise, actionable `next_step` guidance.
  * Assembles the canonical `ProcurementDecision` contract while strictly preserving `human_review_required = True`.

---

## 2. Decision Lifecycle

```mermaid
flowchart TD
    Req(["Inbound Request ID"]) --> Step1["Step 1: Gather Request Context\n(requests.json, employees.csv, department_budgets.csv)"]
    Step1 --> Step2["Step 2: Search Software Catalog\n(software_catalog.csv)"]
    Step2 --> Step3["Step 3: Query Vendor Risk API\n(GET /vendor-risk/{name})"]
    Step3 --> Step4["Step 4: Load Procurement Policy\n(procurement_policy.md)"]
    Step4 --> Step5["Step 5: Execute Rule Engine\n(evaluate_procurement_rules)"]
    
    Step5 --> Step6{"Step 6: Apply Decision Precedence"}
    
    Step6 -- "Priority 1:\nMissing Required Info" --> State1["NEEDS_INFORMATION\n- Flag missing_information\n- Action: Request clarification"]
    
    Step6 -- "Priority 2:\nUnavailable / Conflicting Evidence" --> State2["MANUAL_REVIEW\n- Flag vendor_risk_unavailable / conflict\n- Action: Manual InfoSec verification"]
    
    Step6 -- "Priority 3:\nGovernance Reviews Required" --> State3["PROCEED_TO_REVIEW\n- Approvals: Finance, Security, Privacy, Legal\n- Action: Route to required reviewers"]
    
    Step6 -- "Priority 4:\nStandard Low-Value Path" --> State4["PROCEED_TO_REVIEW\n- Approvals: Manager\n- Action: Route to Manager"]
    
    State1 --> Step7["Step 7: Deduplicate Evidence & Emit Trace"]
    State2 --> Step7
    State3 --> Step7
    State4 --> Step7
    
    Step7 --> Output(["Assemble ProcurementDecision\nhuman_review_required = True"])
```

---

## 3. Evidence Aggregation & Deduplication

Evidence is systematically harvested across four distinct sources and one synthetic evaluation stage:
1. `requests.json` — Product, category, cost estimate, seat count, data access level, requested integrations, justification text.
2. `employees.csv` — Requester identity, department membership, geographical country, manager hierarchy.
3. `department_budgets.csv` — Department annual budget, committed spend, available headroom calculation ($ \text{available} = \text{budget} - \text{committed} $).
4. `software_catalog.csv` — Existing tools, matching categories, licensed seats, scope, usage notes.
5. `vendor-risk-api` — External risk tier, security audit status, review date freshness, personal data ingestion, cross-border storage flags.
6. `procurement_policy.md` — Authoritative threshold bands (§4), security triggers (§5), privacy triggers (§6), legal spend gates (§7), prompt injection defense (§9), tool failure rules (§10), and human authority (§11).

### Deduplication Guarantee
Evidence items are normalized and deduplicated using a composite key:
$$\text{Key} = (\text{norm}(\text{source}), \text{norm}(\text{finding}), \text{reference})$$
This ensures that when both catalog queries and rule evaluations cite the same underlying fact, the final evidence list remains clean, concise, and free of redundant assertions.

---

## 4. Operational Guardrails

1. **No Autonomous Approvals:** The engine has no concept of an `APPROVED`, `AUTO_APPROVED`, or `PURCHASED` state. Recommendations are strictly advisory.
2. **Zero Date Drifts:** All temporal evaluations strictly utilize fixed reference date `2026-09-30`.
3. **No Optimistic Assumptions:** Missing or failed tool queries never yield a clean bill of health; they force `MANUAL_REVIEW`.
4. **Untrusted Data Isolation:** Prompt injection text is detected, logged, and stripped of authority.
