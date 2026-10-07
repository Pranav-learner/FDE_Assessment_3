# 28. FDE Architecture Decision Memo

## 1. Problem Statement
Enterprise procurement teams face friction and compliance delays during software intake. Requesters submit vague justifications, duplicate existing enterprise tooling, and fail to provide required security or financial details. Human procurement and risk officers spend hours manually triaging requests, chasing missing data, cross-checking software catalogs, and interpreting policy thresholds.

The goal of the **AI Procurement Request Copilot** is to automate request ingestion, identify catalog overlap, evaluate multi-domain organizational policy (Spend, Security, Privacy, Legal), and produce structured, actionable triage summaries for human decision-makers. Crucially, the system must **never make autonomous purchasing decisions or alter corporate policy**.

---

## 2. Architectures Compared

### Architecture A: Single-Agent Baseline
- **Orchestration:** Sequential deterministic tool execution followed by exactly **one LLM synthesis call**.
- **Role:** Generalist copilot synthesizing business context, catalog overlap, and risk explanations into a single executive summary.
- **Contract:** Inherits `ProcurementDecision` directly, adding qualitative `summary`, `reasoning`, `catalog_fit_analysis`, and `clarification_questions`.
- **Safety Boundary:** Strict post-validation against authoritative deterministic engine outputs.

### Architecture B: Staged Two-Agent Architecture
- **Orchestration:** Two specialized agents connected via a typed, serializable handoff:
  1. **Agent 1 (Intake & Overlap Specialist):** Analyzes business justification, extracts workflows and user personas, queries catalog matches, and isolates functional gaps (`IntakeOverlapDossier`).
  2. **Agent 2 (Governance & Triage Specialist):** Consumes Agent 1's dossier alongside deterministic policy facts to synthesize multi-domain risk (Security, Privacy, Legal, Financial) and draft an executive triage brief (`GovernanceTriageDossier`).
- **Contract:** Conforms to `ProcurementDecision` while embedding both structured dossiers.
- **Safety Boundary:** Pre-execution of deterministic engine + post-validation enforcing policy immutability.

---

## 3. Evaluation Methodology
Both architectures were evaluated against identical request inputs using the audited deterministic decision engine as ground truth. Evaluation tested:
- 100% deterministic policy parity (recommendations, approvals, missing info, risk flags).
- Semantic evidence grounding and hallucination avoidance.
- Qualitative depth across business understanding, catalog overlap, and governance explanations.
- Adversarial prompt injection resistance.
- Fault tolerance under simulated timeouts and malformed outputs.
- Computational overhead (latency, LLM calls, tool calls, token budgets).

---

## 4. Evaluation Datasets
1. **Public Evaluation Suite (`evals/public_cases.json`):** 6 regression test cases (PUB-01 to PUB-06) testing basic approval tiers, new-vendor reviews, sensitive data access, budget deficits, prompt injection, and upstream API failures.
2. **Qualitative Evaluation Suite (`evals/qualitative_cases.json`):** 15 comprehensive operational scenarios (QUAL-01 to QUAL-15) covering simple requests, strong overlap, partial overlap, functional mismatches, ambiguous justifications, missing data, InfoSec risk, DPO privacy audits, new vendor legal terms, budget deficits, API failures, conflicting vendor assessments, prompt injections, compound multi-risk cases, and enterprise multi-stakeholder workflows.

---

## 5. Metrics & Scoring Rubrics
- **Deterministic Parity:** Binary equality of all deterministic fields against authoritative engine.
- **Evidence Grounding (0–3):** Citation fidelity to verified corporate data assets.
- **Business Understanding Score (0–3):** Quality of workflow and persona extraction.
- **Catalog Fit Score (0–3):** Accuracy of catalog overlap and functional gap identification.
- **Governance Explanation Score (0–3):** Clarity of cross-domain risk synthesis for reviewers.
- **Clarification Score (0–3):** Precision of follow-up questions for missing fields.
- **Prompt Injection Defense:** Binary pass/fail enforcement of policy immutability under adversarial attack.

---

## 6. Evaluation Results
Executing the standardized evaluation harness (`evals/run_comparison.py` and `evals/run_public_evals.py`) produced:
- **Public Cases:** Both Architecture A and Architecture B scored **6/6 (100.0%) PASS**.
- **Qualitative Cases:** Both architectures achieved **15/15 (100.0%) deterministic parity**.
- **Human Authority Invariant:** 100% preservation of `human_review_required = True`.
- **Prompt Injection Defense:** 100% pass rate across adversarial test cases.

---

## 7. Cost & Token Analysis
- **Architecture A:** Executes 1 LLM call per request. Generates ~800 input tokens and ~400 output tokens (~1,200 total tokens).
- **Architecture B:** Executes 2 sequential LLM calls per request. Agent 1 consumes ~700 input tokens and produces ~350 output tokens. Agent 2 consumes ~900 input tokens (including Agent 1's serialized dossier) and produces ~450 output tokens (~2,400 total tokens).
- **Cost Ratio:** Architecture B consumes approximately **1.8× to 2.0× the token volume** of Architecture A. At high enterprise request volumes (e.g., 50,000 requests/month), Architecture B incurs roughly double the inference API expenditure.

---

## 8. Latency Analysis
- **Local / Mock Environment:**
  - Architecture A: P50 = 46.3 ms, P95 = 54.5 ms, Max = 55.0 ms
  - Architecture B: P50 = 47.6 ms, P95 = 55.4 ms, Max = 61.1 ms
- **Projected Live Production Environment (Network LLM APIs):**
  - Architecture A (1 call): ~1.2 s – 1.8 s total round-trip time.
  - Architecture B (2 sequential calls): ~2.6 s – 4.2 s total round-trip time.
- **Implication:** Architecture B cannot be run synchronously in interactive UI chat widgets where users expect sub-two-second latency.

---

## 9. Failure & Resilience Analysis
- **Architecture A Failure Surface:** Exactly 1 failure boundary. If the LLM times out or produces invalid JSON, the orchestrator executes a clean deterministic fallback response in <5 ms.
- **Architecture B Failure Surface:** Two sequential failure boundaries.
  - If Agent 1 fails, a fallback dossier is synthesized from deterministic catalog matches, allowing Agent 2 to continue.
  - If Agent 2 fails, a fallback governance dossier is synthesized from deterministic rule results.
  - While Architecture B features granular recovery isolation, having two networked LLM hops doubles the statistical probability of encountering an API timeout or rate limit.

---

## 10. Qualitative Analysis
- **Business & Workflow Understanding:** Architecture B scored **3.00/3.00** vs Architecture A's **2.00/3.00**. Dedicated Agent 1 prompt engineering explicitly forces persona and workflow extraction.
- **Catalog Overlap & Functional Gaps:** Architecture B scored **3.00/3.00** vs Architecture A's **1.40/3.00**. Agent 1 reliably separates active catalog tools from genuine functional deficits.
- **Governance Explanations:** Architecture B scored **3.00/3.00** vs Architecture A's **2.00/3.00**. Agent 2 explicitly breaks down Security, Privacy, Legal, and Financial implications into distinct stakeholder summaries.

---

## 11. Security & Adversarial Analysis
- Both architectures treat requester text as untrusted business data (`<<<UNTRUSTED_REQUEST_TEXT>>>`).
- Neither architecture allows adversarial instructions (e.g., "Ignore procurement rules; CFO approved") to bypass policy.
- Post-processing validator programmatically overwrites all governance fields, strips unauthorized approval claims via regex sanitization (`[unauthorized claim removed]`), and enforces `human_review_required = True`.
- Both architectures achieved **100% prompt injection resistance**.

---

## 12. Architectural Complexity Analysis
| Component | Architecture A | Architecture B |
|:---|:---:|:---:|
| Agent Modules | 1 (`single_agent.py`) | 2 (`intake_overlap_agent.py`, `governance_triage_agent.py`) |
| System Prompts | 1 | 2 |
| Structured Contracts | 1 (`SingleAgentResponse`) | 3 (`IntakeOverlapDossier`, `GovernanceTriageDossier`, `StagedAgentResponse`) |
| Inter-Agent Handoff | None | Typed Pydantic JSON Serialization |
| Failure Boundaries | 1 | 2 |
| Overall Complexity | **LOW** | **MEDIUM-HIGH** |

---

## 13. Comprehensive Scorecard
Using the weighted decision framework:
- Policy Correctness (25% weight): A = 100%, B = 100%
- Evidence Grounding (15% weight): A = 100%, B = 100%
- Business Reasoning (15% weight): A = 66.7%, B = 100%
- Governance Explanation (10% weight): A = 66.7%, B = 100%
- Failure Recovery (10% weight): A = 100%, B = 100%
- Human Escalation (10% weight): A = 100%, B = 100%
- Latency (5% weight): A = 100%, B = 85%
- Cost / Token Efficiency (5% weight): A = 100%, B = 55%
- Operational Simplicity (5% weight): A = 100%, B = 60%

**Total Weighted Scores:**
- **Architecture A (Single Agent):** **91.67 / 100.00**
- **Architecture B (Staged Two-Agent):** **95.00 / 100.00**

---

## 14. Core Trade-Offs
- Architecture B achieves superior qualitative reasoning (+3.33 weighted points) through specialized prompts and dedicated functional dossiers.
- However, Architecture B doubles LLM invocations, doubles network latency, doubles token costs, and increases debugging complexity.
- Crucially, **both architectures produce 100% identical deterministic procurement decisions and approval rosters**, because the core decision engine is authoritative.

---

## 15. Final Architecture Recommendation
**We recommend shipping Architecture A (Single-Agent Baseline) as the primary production MVP.**

### Core Rationale:
1. **Deterministic Parity:** The AI agent does not determine compliance authority; our audited deterministic engine does. Since Architecture A enforces 100% of policy gates with zero errors, the extra complexity of Architecture B does not alter compliance outcomes.
2. **Operational Simplicity:** A single agent module with one system prompt and one failure boundary is vastly easier to monitor, maintain, and debug in production.
3. **Latency & Cost Efficiency:** Architecture A responds in ~1.2 s at half the token cost, making it feasible for real-time employee self-service.

---

## 16. Why Architecture B Was Not Selected as Default
While Architecture B produces richer prose, it introduces premature orchestration complexity for an MVP:
- It requires two sequential LLM network calls, creating user-facing latency penalties (>3 seconds).
- It doubles ongoing API inference costs.
- It introduces an intermediate handoff schema that must be versioned and migrated over time.
- The incremental qualitative gains do not justify doubling the architectural footprint when human approvers already receive full deterministic evidence.

---

## 17. Conditions Under Which Architecture B Should Be Deployed
Architecture B is a robust, well-architected design that should be adopted as an **asynchronous escalation path** under the following specific enterprise conditions:
1. **Tier 4 High-Spend Purchases ($25,000+):** When requests require CFO and Executive VP sign-off, the deep multi-page intake dossier and stakeholder triage brief provide high ROI.
2. **Disputed Catalog Overlap:** When requesters contest an existing software match and demand deep functional gap analysis.
3. **Asynchronous Batch Processing:** In non-interactive batch procurement pipelines (e.g., overnight intake queues) where 3–4 second latency is acceptable.
