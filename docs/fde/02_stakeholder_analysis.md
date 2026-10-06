# 02. Stakeholder Analysis: AI Procurement Request Copilot

**Document Version:** 1.0.0  
**Status:** Baseline Specification (Phase 1 Source of Truth)  
**Author:** Forward Deployed Engineering (FDE)

---

## 1. Stakeholder Matrix

This document maps all operational, technical, executive, and governance stakeholders involved in the procurement decision lifecycle. For each stakeholder, we analyze their core responsibilities, operational goals, key decision factors, risk exposures, and how the copilot transforms their day-to-day workflow.

---

### 1.1 Employee / Requester
* **Role:** Individual Contributor or Team Lead submitting a software or SaaS purchase request (e.g., E001 Sarah Lee in Marketing, E002 Arjun Mehta in Engineering, E003 Elena Garcia in Sales, E004 Noah Williams in Finance, E005 Mia Thompson in Customer Success).
* **Goal:** Quickly obtain access to software or AI capabilities required to complete business projects and meet team targets.
* **Information They Care About:** Request turnaround time, status of their ticket, clarity on required information, cost impact, and clear instructions if clarification is needed.
* **Decision / Responsibility:** Formulates the business justification, estimates seat count and data access tier, and provides vendor pricing details.
* **What Failure Looks Like:** Prolonged delays, arbitrary rejections without explanation, opaque procurement bureaucracy, or being forced to adopt an unsuitable existing tool that doesn't meet technical requirements.
* **How the Copilot Affects Them:** Accelerates triage; immediately highlights missing fields (e.g., missing price or seat count) so requests can be remediated upfront rather than lingering in a queue.

---

### 1.2 Direct Manager
* **Role:** Line Manager of the requester (e.g., E006 Priya Shah, E007 Robert King, E008 Maya Rao, E009 David Chen).
* **Goal:** Ensure team productivity while maintaining basic operational oversight and keeping low-value expenditures aligned with quarterly goals.
* **Information They Care About:** Legitimacy of the business need, identity of the employee requesting, direct team utility, and cost (especially under $1,000 threshold).
* **Decision / Responsibility:** First-line operational signoff. Sole financial approver for requests up to $1,000; provides operational endorsement for higher-tier requests.
* **What Failure Looks Like:** Approving unnecessary tools, rubber-stamping rogue subscriptions, or blocking critical tooling due to lack of visibility.
* **How the Copilot Affects Them:** Summarizes the core request justification and confirms whether the tool is within the $1,000 manager-only approval threshold.

---

### 1.3 Department Head / Director / VP
* **Role:** Executive leader of the department (e.g., Directors E006, E007, E008, E009; VP Operations E010 Lisa Park).
* **Goal:** Strategic departmental efficiency, portfolio management, staying within annual software budget allocations.
* **Information They Care About:** Total annual cost ($1,000.01 - $10,000, $10,000.01 - $25,000, and >$25,000 brackets), impact on available department budget, team-wide adoption viability, and potential overlap with other tools already owned by the department.
* **Decision / Responsibility:** Primary business authority for requests exceeding $1,000. Decides whether to commit department funds and confirms whether existing departmental software alternatives are sufficient.
* **What Failure Looks Like:** Incurring budget deficits (`budget_insufficient`), approving redundant licenses across teams, or failing to capture department-level volume discounts.
* **How the Copilot Affects Them:** Delivers clean pre-computed budget math (`available_usd` vs. `annual_cost_usd`) and surfaces existing catalog software in the same category.

---

### 1.4 Procurement Specialist / Analyst (Primary User)
* **Role:** Operational procurement specialist triaging inbound tickets in the central queue.
* **Goal:** Process inbound requests rapidly, enforce corporate procurement policy without error, avoid duplicate purchasing, and ensure compliance.
* **Information They Care About:** Completeness of submission, vendor contract status (New vs. Approved), existing catalog overlap, budget sufficiency, verified risk flags, and an auditable list of required downstream approvers.
* **Decision / Responsibility:** Primary operator of the copilot. Synthesizes findings, requests requester clarification, routes to approvers, or escalates to governance reviews.
* **What Failure Looks Like:** Passing non-compliant requests, missing vendor risk flags, failing to catch catalog overlap, or routing to the wrong approvers.
* **How the Copilot Affects Them:** Serves as an augmented workbench. Replaces manual spreadsheet lookups and multi-system cross-referencing with a single synthesized evidence pane and recommended next action.

---

### 1.5 Finance & Planning (FP&A) / Chief Financial Officer (CFO)
* **Role:** Corporate financial gatekeepers.
* **Goal:** Fiscal discipline, cash flow predictability, corporate financial governance, and budget reconciliation.
* **Information They Care About:** Budget deficits (`budget_insufficient`), threshold compliance ($10,000.01+ triggers Finance; >$25,000 triggers CFO), department commitment velocity, payment terms, and vendor spend aggregation.
* **Decision / Responsibility:** Evaluates budget exception requests when cost exceeds `available_usd`. Formal approval authority for all spend above $10,000; CFO signoff required for spend over $25,000.
* **What Failure Looks Like:** Unbudgeted spend commitments, unexpected software liabilities, uncontrolled departmental budget overruns.
* **How the Copilot Affects Them:** Enforces deterministic budget checks; automatically gates requests with `budget_insufficient` or amounts over $10,000 / $25,000 to Finance/CFO queues.

---

### 1.6 Information Security (InfoSec / SecOps)
* **Role:** Corporate cybersecurity and technical risk team.
* **Goal:** Protect company infrastructure, intellectual property, credentials, source code, and production cloud environments from breach or third-party supply chain risk.
* **Information They Care About:** Data access level (`source_code`, `production_telemetry`, `confidential_documents`, `credentials/secrets`), integrations (Git repositories, cloud accounts, SSO), vendor risk scores, assessment freshness (within 365 days), and uncompleted vendor reviews.
* **Decision / Responsibility:** Mandatory security review when sensitive data access, cloud integrations, or expired/missing vendor reviews are present. Authority to veto vendors or mandate technical security controls.
* **What Failure Looks Like:** Allowing unvetted SaaS tools to access production repositories or cloud environments; approving vendors whose 365-day security certification has lapsed.
* **How the Copilot Affects Them:** Automatically attaches vendor security audit dates, flags `vendor_review_expired` or `conflicting_vendor_evidence`, and tags `security_review_required`.

---

### 1.7 Data Privacy & Compliance (DPO)
* **Role:** Data Protection Officer and compliance officers responsible for GDPR, CCPA, and global privacy standards.
* **Goal:** Prevent regulatory fines, uphold customer and employee data protection rights, and prevent unauthorized cross-border data transfers.
* **Information They Care About:** Presence of `employee_pii` or `customer_pii`, third-party vendor data handling policies, and whether the vendor stores data outside the operating region (`stores_data_outside_region: true`).
* **Decision / Responsibility:** Reviews all tools ingesting personal data or transferring data across geographic borders. Signs off on Data Processing Agreements (DPAs).
* **What Failure Looks Like:** Customer PII exported to unapproved third-party servers without DPA or cross-border safeguards, triggering regulatory penalties.
* **How the Copilot Affects Them:** Surfaces `privacy_review_required` whenever `customer_pii`, `employee_pii`, or cross-region storage is detected.

---

### 1.8 Legal & Contracting
* **Role:** In-house corporate counsel and commercial contracting team.
* **Goal:** Protect company from liability, intellectual property loss, unfavorable indemnification, auto-renewals, and non-standard contract terms.
* **Information They Care About:** Vendor onboarding state (`New` vs. `Approved`), annual spend threshold ($\ge \$10,000$ for new vendors), legal terms status (`Draft`, `Unknown`, `Approved`), and cross-border liability risks.
* **Decision / Responsibility:** Mandatory review for new vendors with annual spend $\ge \$10,000$, unapproved terms, or material data transfer issues. Approves master service agreements (MSAs) and terms of service (ToS).
* **What Failure Looks Like:** Entering into binding agreements with unvetted new vendors without negotiated terms or limitation of liability.
* **How the Copilot Affects Them:** Detects new vendors with contract value $\ge \$10,000$ or non-standard terms and attaches `legal_review_required`.

---

### 1.9 Procurement Operations & Sourcing Leadership
* **Role:** Head of Procurement / Sourcing Director.
* **Goal:** Scalable operations, vendor consolidation, enterprise license agreement (ELA) optimization, high team throughput, and auditability.
* **Information They Care About:** Aggregated vendor spend across departments, duplicate vendor relationships, workflow SLAs, and end-to-end audit trails.
* **Decision / Responsibility:** Owns procurement policy, sets governance thresholds, and leads vendor consolidation initiatives.
* **What Failure Looks Like:** Decentralized shadow procurement, uncoordinated vendor proliferation, audit findings of policy non-compliance.
* **How the Copilot Affects Them:** Provides transparent, reproducible evidence records for every transaction, ensuring policy adherence and auditable governance.

---

## 2. Stakeholder Discovery: Questions I Would Ask the Client

*(Note: These questions represent discovery inquiries an FDE would conduct during initial client requirements gathering. These interviews have not yet taken place; they are structured to clarify operational ambiguities in future deployment phases.)*

### 2.1 Current Workflow & Intake
1. *"What is the primary entry point for software requests today (e.g., Jira Service Management, ServiceNow, Slack intake form, email)? Does the form enforce structured validation, or are fields free-text?"*
2. *"What percentage of incoming requests currently arrive with missing information (e.g., missing cost, unknown license count), and how is clarification requested today?"*
3. *"What is the current average turnaround time (SLA) from initial request submission to final PO issuance?"*

### 2.2 Approval Matrix & Financial Delegations
4. *"When a request falls within the $1,000.01 - $10,000 range (Department Head + Procurement), must the Department Head approve before Procurement reviews, or can reviews occur concurrently?"*
5. *"For requests exceeding available department budget (`budget_insufficient`), does Finance require a formal budget reallocation approval before other reviews (Security/Legal) proceed, or do reviews run in parallel?"*
6. *"At what exact seniority level can a Department Head delegate their financial approval authority during out-of-office periods?"*

### 2.3 Software Catalog & Overlap Evaluation
7. *"When an existing tool overlap is identified (e.g., BrandBoard requested while PixelCraft is in the catalog), what constitutes an acceptable 'credible gap'? Is there a formal exception form for requester feature justifications?"*
8. *"Do you currently track unused seats or license utilization in the software catalog? If an approved tool has 50 unallocated seats, is the policy to reject new tool requests outright?"*
9. *"How frequently is `software_catalog.csv` updated when a new purchase order is finalized?"*

### 2.4 Vendor Risk, Security & Freshness Policies
10. *"The policy states vendor security reviews are valid for 365 days. If a review expired 5 days ago, is the request placed on total hold, or can conditional approval be granted pending reassessment?"*
11. *"When the internal vendor registry (`vendors.csv`) and the external risk API conflict (e.g., SignalWatch), what is the standard operating procedure? Is the external API always considered more authoritative?"*
12. *"What is the fallback SLA when the external vendor-risk API is offline or returns a 503 error?"*

### 2.5 Privacy, Legal & Cross-Border Governance
13. *"For employees located across India, UK, Spain, and the US, does 'stores data outside region' refer to the employee's country or the corporate headquarters region (US)?"*
14. *"Are standard online click-through Terms of Service (clickwrap) acceptable for purchases under $1,000, or must Legal review every SaaS agreement regardless of price?"*
15. *"Does an existing vendor approval automatically extend to new subsidiary products or add-ons without fresh legal terms?"*

### 2.6 AI Governance & Untrusted Business Data
16. *"For AI tools (e.g., NeuralDesk, CodeMate), what specific security certifications (e.g., SOC2 Type II, ISO 27001, zero-data-retention agreements) are required before allowing source code or customer PII access?"*
17. *"How do procurement analysts currently identify prompt injection or adversarial text in requests? Have you observed attempts by employees to spoof approvals or bypass rules in ticket descriptions?"*

### 2.7 Auditability, Evidence & System Boundaries
18. *"What format of audit evidence is required by internal compliance? Does saving the structured `EvidenceItem` chain satisfy annual IT audit requirements?"*
19. *"Under what exact conditions would the organization ever consider allowing autonomous low-value ($< $1,000) approvals, or is human review permanently mandatory?"*
20. *"What telemetry and performance metrics (e.g., latency, token expenditure, accuracy) will be tracked in production?"*
