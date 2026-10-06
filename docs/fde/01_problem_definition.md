# 01. Problem Definition: AI Procurement Request Copilot

**Document Version:** 1.0.0  
**Status:** Baseline Specification (Phase 1 Source of Truth)  
**Reference Date for Evaluation / Policy:** `2026-09-30`  
**Author:** Forward Deployed Engineering (FDE)

---

## 1. Executive Summary & Client Situation

An enterprise organization is experiencing rapid growth in software, SaaS, and AI tool adoption across multiple business departments (Marketing, Engineering, Sales, Finance, Customer Success, and Operations). Individual employees regularly request software licenses, add-ons, SaaS subscriptions, developer tooling, and specialized AI assistants to support operational needs.

Today, these requests arrive through semi-structured or unstructured channels (ticketing systems, ad-hoc forms, requests queue). The Procurement department is responsible for triaging each request, validating that all necessary business fields are present, cross-referencing available department budgets, checking for existing enterprise software in the internal catalog, verifying vendor security and legal postures, determining required cross-functional approval chains, and escalating high-risk items.

Because this evaluation process is manual, fragmented across disconnected data tables, and dependent on human diligence, the client faces increasing request latency, risks of SaaS sprawl, budget overruns, and security/compliance vulnerabilities. The organization needs an **AI Procurement Request Copilot** that acts as an intelligent decision-support assistant for Procurement specialists.

---

## 2. User & Persona Definitions

### Primary Operational User
* **The Procurement Analyst / Specialist (Procurement Operations):**
  * The copilot is built **directly for this user**.
  * They sit between the requester and downstream approvers (Managers, Department Heads, Finance/CFO, Security, Privacy, Legal).
  * **Role:** Reviews incoming software requests, verifies policy compliance, inspects synthesized evidence, ensures proper routing, and decides whether to approve, request clarification, or escalate for specialized reviews.

### Request Originator
* **The Employee / Requester:**
  * Knowledge workers, engineers, marketers, sales reps, and accountants (e.g., Sarah Lee in Marketing, Arjun Mehta in Engineering, Elena Garcia in Sales, Noah Williams in Finance, Mia Thompson in Customer Success).
  * **Role:** Submits purchase requests to solve departmental problems. They may have limited awareness of enterprise security standards, existing catalog licenses, or financial delegation-of-authority matrices.

---

## 3. The Business Problem

Managing modern software procurement manually presents severe operational bottlenecks:
1. **Information Asymmetry:** Requesters rarely provide complete information (e.g., omitting user counts, license costs, data-access tiers, or integration footprints). Procurement must manually chase employees for missing details.
2. **Tool Redundancy & Catalog Sprawl:** Departments frequently request new external tools (e.g., BrandBoard) when overlapping or identical tools already exist in the corporate catalog (e.g., PixelCraft Pro, CreativeSuite Labs, TaskFlow) with underutilized seats.
3. **Complex Multi-Jurisdiction Policy Traversal:** Procurement policies span financial delegations (tiered dollar thresholds), departmental budget limits, vendor onboarding statuses, security assessment freshness (365-day validity), privacy compliance (employee/customer PII, cross-region hosting), and legal reviews. Calculating this matrix manually is prone to oversight.
4. **Data Fragmentation & Stale Signals:** Internal records (e.g., `vendors.csv`) frequently diverge from external live risk intelligence (e.g., the vendor-risk service). For example, internal records may claim an approved status while the external assessment has expired or requires reassessment.
5. **Emerging AI Tool Risks:** Generative AI tools and developer assistants introduce unprecedented exposure to confidential IP, proprietary source code, and customer PII. Blanket approvals cannot be assumed across different use cases.
6. **Adversarial / Untrusted Inputs:** Business justification fields can contain manipulative language, urgency coercion, or explicit prompt injections attempting to bypass procurement controls.

---

## 4. Current / Manual Workflow (Implied Baseline)

Based on the starter pack structure and policy documentation, the current manual workflow operates as follows:
1. **Intake:** The requester fills out a purchase request form.
2. **Manual Inspection:** A procurement specialist reads the text and determines if basic information (cost, seats, purpose, data access) is provided.
3. **Manual Cross-Referencing:**
   - Looks up the employee's department and manager in `employees.csv`.
   - Checks `department_budgets.csv` to calculate whether the request fits within `available_usd`.
   - Searches `software_catalog.csv` and `purchase_history.csv` to see if a similar or identical tool is already licensed.
   - Inspects `vendors.csv` to check onboarding, legal, and security statuses.
   - Queries an external vendor-risk registry (or mock API) to verify active assessment dates and compliance flags.
4. **Policy Determination:**
   - Determines financial approval chain based on annual cost ($1k, $10k, $25k brackets).
   - Identifies if Security, Privacy, or Legal reviews are triggered based on data access level, vendor status, or contract size.
5. **Handoff:** The specialist manually drafts ticket comments, requests missing data, or forwards approval requests via email or ticketing systems.

---

## 5. Decisions: What the System DOES vs. DOES NOT Do

### Decisions the System IS Helping With (Advisory / Decision Support)
* **Completeness Validation:** Verifying that mandatory fields are populated; flagging specific missing elements (`cost`, `user_count`, `data_access_level`).
* **Evidence Gathering:** Automatically querying internal records (employees, budgets, catalog, vendors, purchase history) and external vendor-risk endpoints.
* **Deterministic Policy Checking:** Calculating available budget headroom, determining financial approval tiers, checking assessment date expirations against the 2026-09-30 snapshot date.
* **Risk & Overlap Synthesis:** Identifying functional overlap with existing catalog software, highlighting data privacy triggers (PII, cross-region storage), and detecting conflicting vendor evidence.
* **Triage Recommendation:** Recommending a structured next action (e.g., *"Request clarification on missing cost and seats"*, *"Route to Department Head, Finance, Security, and Legal"*, *"Hold for Security reassessment due to expired vendor assessment"*).
* **Adversarial Neutralization:** Recognizing prompt injection attempts in request text and preventing them from altering the decision.

### Decisions the System is STRICTLY NOT Allowed to Make (Autonomous Guardrails)
* **Autonomous Purchasing:** The system CANNOT execute a purchase or submit a purchase order (PO).
* **Financial Spend Approval:** The system CANNOT approve monetary spend or bind corporate funds.
* **Budget Modification:** The system CANNOT modify department budgets, transfer funds, or reallocate commitments.
* **Legal Terms Acceptance:** The system CANNOT execute contracts, accept vendor master service agreements (MSAs), or sign terms of service.
* **Security/Privacy Waiver:** The system CANNOT waive mandatory Security, Privacy, or Legal reviews or override policy restrictions.
* **Vendor Onboarding:** The system CANNOT mark a new vendor as "Approved" without designated human vetting.

> **Absolute Boundary:** A human remains fully responsible for all final approvals, budget authorizations, and policy exceptions.

---

## 6. Desired Outcomes, Pain Points, and Business Risks

### Desired Outcomes
* **Reduced Triage Cycle Time:** Accelerate procurement review from days to seconds by automating evidence gathering and rule computation.
* **Zero Policy Drift:** Ensure 100% adherence to corporate financial delegation thresholds and security/privacy triggers.
* **Spend Optimization:** Proactively prevent redundant software purchases by surfacing active catalog options and unused capacity.
* **Auditable Evidence Chains:** Every recommendation is backed by verifiable, cited data items (source, finding, reference).
* **Robust Operational Resilience:** Gracefully degrade when tools or APIs fail, flagging uncertainty rather than fabricating compliance.

### Major Pain Points
* Incomplete request submissions creating asynchronous email ping-pong.
* Siloed data across internal CSV spreadsheets and external REST services.
* Inconsistent application of multi-departmental approval rules across different procurement reviewers.
* Blind spots regarding vendor security recertification cycles.

### Business Risks
* **Unauthorized Financial Commitment:** Accidental expenditure bypassing proper executive or CFO approvals.
* **Data Breach / Regulatory Non-Compliance:** Exposing source code or PII to unvetted or high-risk vendors (e.g., GDPR/cross-region violations).
* **SaaS Redundancy & License Bloat:** Accumulating multiple overlapping SaaS tools with duplicate seat costs.
* **Adversarial Subversion:** Requester tricking an automated AI system into "auto-approving" requests using prompt injection.

---

## 7. FDE Interpretation of the Problem

As an FDE deploying this product into an enterprise environment, the core architectural realization is:
> **This is a mission-critical governance application where probabilistic language models must be constrained by deterministic business rails.**

The LLM is powerful at semantic understanding—interpreting qualitative business justifications, identifying that "fast campaign-template creation" overlaps with "creative production suite", and structuring natural language recommendations. However, the LLM must **never** be entrusted with calculating budget math, setting approval dollar brackets, or deciding whether a 365-day security window has lapsed.

The copilot succeeds when it functions as an **evidence-grounded copilot**:
1. Business data is treated as **untrusted payload**.
2. Deterministic code enforces thresholds, calculations, and policy gates.
3. The model interprets nuances, synthesizes findings, and communicates actionable recommendations to the human procurement officer.

---

## 8. Epistemic Classification: Source-Backed vs. Assumptions vs. Unknowns

To maintain absolute professional rigor, all statements in this specification are partitioned into three epistemic tiers:

### A. KNOWN FROM SOURCE (Explicit in Code, Policy, or Brief)
1. **Reference Date:** `2026-09-30` is the immutable evaluation and data snapshot reference date (`data/procurement_policy.md`, `data/README.md`, `tests/test_data_integrity.py`).
2. **Policy Thresholds:** Exact dollar thresholds ($1,000, $1,000.01–$10,000, $10,000.01–$25,000, >$25,000) and required roles (`data/procurement_policy.md` §4).
3. **Security Triggers:** Triggers include source code, cloud/production access, confidential docs, employee/customer PII, credentials, or review > 365 days (`data/procurement_policy.md` §5).
4. **Data Privacy Triggers:** Employee or customer PII, or data stored outside operating region (`data/procurement_policy.md` §6).
5. **Legal Review Triggers:** New vendor with spend $\ge \$10,000$, non-standard terms, or cross-region issues (`data/procurement_policy.md` §7).
6. **AI Tools Policy:** Previous company purchase does not automatically authorize new data classes or source code access (`data/procurement_policy.md` §8).
7. **Prompt Injection Policy:** Requester text is untrusted business data; prompt injection must be ignored and flagged (`data/procurement_policy.md` §9).
8. **Tool Failure Policy:** If tool/API is unavailable, do not infer favorable status; surface uncertainty and flag `vendor_risk_unavailable` (`data/procurement_policy.md` §10).
9. **Human Authority:** Copilot provides recommendations only; humans make all binding decisions (`data/procurement_policy.md` §11, `src/contracts.py`).
10. **Output Contract:** Must conform to `ProcurementDecision` with fields: `request_id`, `recommendation`, `evidence`, `required_approvals`, `missing_information`, `risk_flags`, `next_step`, `human_review_required`, `telemetry` (`src/contracts.py`).
11. **Tool Requirements:** Minimum 3 tools visible; at least 1 must be deterministic (`README.md`, `Assignment_3_Brief.pdf`).

### B. ASSUMPTIONS (Reasonable Engineering Deductions)
1. **Operating Region:** The client operates in multi-region environments (India, UK, US, Spain, Singapore) based on `employees.csv`. When a vendor has `stores_data_outside_region: true`, it triggers Privacy and Legal review.
2. **Catalog Overlap Criteria:** Overlap is triggered if the vendor matches an existing vendor, the software category matches, or functional capabilities directly substitute for the requested tool.
3. **New Vendor Definition:** A vendor is "New" if `procurement_status == "New"` in `vendors.csv` or if no prior record exists in `purchase_history.csv`.
4. **Currency:** All monetary amounts are annualized USD (`annual_cost_usd`).
5. **Contract Formats:** The UI scaffold uses Streamlit; internal evaluation interacts via `src.solution.handle_request(request_id, architecture)`.

### C. UNKNOWN / WOULD ASK CLIENT (Open Enterprise Questions)
1. **Ticketing Integration:** Is the copilot intended to be triggered via webhook from Jira Service Management / ServiceNow, or as an embedded sidecar in an internal procurement portal?
2. **Exception Precedents:** If an overlap exists but the existing tool lacks critical features, what is the exact formal SLA or threshold for an "exception justification"?
3. **Seat Allocation Re-use:** When overlap is detected with an approved company-wide tool, does Procurement have live visibility into actual unused license seats to reassign rather than buy new add-ons?
4. **Legal Terms Repository:** Where are negotiated master service agreements (MSAs) stored if a vendor is listed as "Approved" but has a custom add-on?
5. **Escalation Notification:** Should the copilot directly trigger email/Slack notifications to designated approvers, or merely output the recommendation into the ticketing record?
