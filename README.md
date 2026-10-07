# AI Procurement Request Copilot

**Autonomous Decision Support & Procurement Intake Platform**  
*Forward Deployed Engineering (FDE) Assessment 3 Deliverable*

---

## 1. Problem Statement
Enterprise procurement teams face severe operational bottlenecks during software intake. Requesters submit vague justifications, duplicate existing corporate tooling, and fail to provide required security or commercial terms. Human procurement analysts spend hours manually reviewing catalogs, verifying departmental budgets, and interpreting multi-domain compliance policies (InfoSec, Privacy/GDPR, Legal, and Finance).

---

## 2. FDE Solution Overview & Product Workflow

The **AI Procurement Request Copilot** is an enterprise decision-support platform designed for procurement teams. It ingests software purchase requests, gathers verified evidence across corporate databases and external risk APIs, executes deterministic policy rules, detects SaaS redundancy, and generates structured, actionable triage dossiers.

### Core Governance Invariant
> **The copilot is strictly advisory. Human review is always mandatory (`human_review_required = True`). The system never executes autonomous purchases or contract approvals.**

### 3-Panel Visual Workflow (UI on Port 8501)
1. **Panel 1 — Inbound Procurement Request:** Displays requester identity, department hierarchy, annual spend ($), seat counts, vendor/product, data access level, and business justification.
2. **Panel 2 — Copilot Recommendation & Action:** Displays the status badge (`PROCEED_TO_REVIEW`, `MANUAL_REVIEW`, or `NEEDS_INFORMATION`), mandatory human review banner, required approval roster, risk flags, missing info clarifications, executive summary, next steps, and live runtime telemetry.
3. **Panel 3 — Verified Evidence Panel (5 Categorized Tabs):**
   - `💰 Budget & Context`: Department budget headroom vs. committed spend.
   - `📦 Software Catalog`: Existing tools overlap analysis (e.g. PixelCraft Pro vs. BrandBoard).
   - `🔒 Vendor Security`: External vendor risk posture, security review dates, and data types.
   - `📜 Policy Rules`: Financial spend delegation thresholds ($1k, $10k, $25k).
   - `📋 Full Trace`: Ordered chronological evidence trail connecting findings to ground truth.

---

## 3. High-Level Architecture

The platform enforces a tripartite architecture separating untrusted inputs, authoritative deterministic policy rules, and qualitative LLM synthesis:

```
[ Inbound Request (Untrusted Data) ]
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ 1. DETERMINISTIC TOOLS LAYER (Authoritative Ground Truth)   │
│    • Request Context & Hierarchy Tool                       │
│    • Department Budget Headroom Tool                        │
│    • Software Catalog Overlap Search Tool                   │
│    • Vendor Risk Microservice Client (HTTP Port 8001)       │
│    • Procurement Policy Rule Parser                         │
└──────────────────────────────┬──────────────────────────────┘
                               │ Verified Evidence Items
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. QUALITATIVE AGENT LAYER (Reasoning & Stakeholder Brief)  │
│    Architecture A: Single-Agent Baseline (1 LLM Call)       │
│    Architecture B: Staged Two-Agent Variant (2 LLM Calls)   │
└──────────────────────────────┬──────────────────────────────┘
                               │ Proposed Narrative Dossier
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. DETERMINISTIC GUARDRAIL VALIDATOR                        │
│    • Invariant: human_review_required = True (Hard-Locked)   │
│    • Enforces authoritative approvers and risk flags        │
│    • Sanitizes hallucinated "auto-approved" claims          │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
               [ Final ProcurementDecision Contract ]
```

---

## 4. Tools & Deterministic Checks

The copilot integrates **5 dedicated tools**, strictly separating deterministic policy enforcement from LLM interpretation:

| Tool Name | Type | Data Source | Responsibility |
|:---|:---:|:---|:---|
| `get_request_context` | Deterministic | `requests.json`, `employees.csv` | Ingests request payload and resolves employee organizational reporting hierarchy. |
| `department_budgets` | Deterministic | `department_budgets.csv` | Computes allocated budget, committed spend, and remaining financial headroom. |
| `search_software_catalog` | Deterministic | `software_catalog.csv` | Matches requested tools by name and category; flags duplicate licenses. |
| `get_vendor_risk` | REST Microservice | HTTP `GET :8001/vendor-risk/{v}` | Fetches live vendor security status, risk tier (`low`/`medium`/`high`), and review recency. |
| `get_procurement_policy` | Deterministic | `procurement_policy.md` | Authoritative spend thresholds ($1k, $10k, $25k), security, privacy, and legal delegation rules. |

---

## 5. Agent System Design: Architecture A vs. Architecture B

### Architecture A: Single-Agent Baseline (Core Production MVP)
- Executes deterministic tools, followed by **exactly 1 LLM synthesis call**.
- The single agent receives verified evidence and generates:
  - An executive summary narrative for non-technical procurement stakeholders.
  - Explanations of risk flags and software overlap.
  - Targeted clarification questions for missing information.
- **Latency:** ~26.7 ms (offline mock) / ~1.2s (live cloud LLM).
- **Token Budget:** ~1,200 tokens per request.
- **Reliability:** Single failure boundary with automatic deterministic fallback.

### Architecture B: Staged Two-Agent Architecture (Escalation Variant)
- Splits synthesis across two sequential agents connected via a typed Pydantic contract:
  1. **Agent 1 (Intake & Overlap Specialist):** Decomposes business intent, requested capabilities, and catalog functional overlap $\rightarrow$ outputs `IntakeOverlapDossier`.
  2. **Agent 2 (Governance & Triage Specialist):** Ingests Agent 1's dossier, vendor risk records, and budget constraints $\rightarrow$ outputs `GovernanceTriageDossier`.
- **Latency:** ~26.0 ms (offline mock) / ~2.6s–4.0s (live cloud LLM).
- **Token Budget:** ~2,400 tokens per request (2 sequential LLM calls).

---

## 6. Assumptions & Scope Boundaries

1. **Policy Supremacy:** Corporate procurement rules, financial delegation limits, and vendor risk tiers are deterministic ground truth. The LLM is an advisor and communicator, never a policy authority.
2. **Mandatory Human Sign-off:** No software purchase can be executed without human approval. Autonomous purchasing is disabled by design.
3. **Data Snapshot Date:** Date-based reviews adhere to the static corporate audit reference date (`2026-09-30`) to ensure 100% test reproducibility.
4. **Adversarial Untrusted Data:** All user-submitted text (e.g. business justification) is treated as untrusted and wrapped in security boundaries before prompt inclusion.

---

## 7. Quick Start (One-Command Start Path)

The repository provides a root-level one-command startup script `./run.sh`:

```bash
git clone https://github.com/Pranav-learner/FDE_Assessment_3.git
cd FDE_Assessment_3
./run.sh
```

- **Vendor-Risk & Copilot REST API:** `http://127.0.0.1:8001`
- **Interactive Procurement Web UI:** `http://127.0.0.1:8501`

### 7.1 Local Python Commands
```bash
# Set up virtual environment
python -m venv .venv
source .venv/bin/activate  # (or .venv/bin/activate.fish)
pip install -r requirements.txt

# Run pre-flight verification
python verify_setup.py

# Launch local stack
python run_local.py
```

### 7.2 Configuration (`.env`)
```bash
cp .env.example .env
```
Key settings:
- `LLM_MODE=mock`: Offline deterministic synthesizer (default, zero API keys required). Set `live` to use cloud providers.
- `VENDOR_RISK_BASE_URL=http://127.0.0.1:8001`: Upstream vendor risk assessment endpoint.
- `DEFAULT_ARCHITECTURE=single`: Default execution pipeline (`single` or `staged`).
- `OPENAI_API_KEY` / `GEMINI_API_KEY`: Optional; automatically used when provided.

---

## 8. Command Line Interface (CLI) & REST API

```bash
# Evaluate using default Single-Agent (Architecture A)
python app.py --request-id REQ-1001

# Explicitly select Architecture A
python app.py --request-id REQ-1002 --architecture single

# Select Staged Two-Agent (Architecture B)
python app.py --request-id REQ-1005 --architecture staged

# Machine-readable JSON output
python app.py --request-id REQ-1001 --json

# List all available sample requests in the database
python app.py --list
```

### HTTP REST API Endpoints (Port 8001)
| Method | Endpoint | Description |
|:---|:---|:---|
| `GET` | `/health` | Liveness healthcheck (`{"status":"ok"}`) |
| `GET` | `/ready` | Readiness check (verifies 7 data assets on disk) |
| `GET` | `/vendor-risk/{vendor}` | Vendor security risk record |
| `POST` | `/procurement/evaluate` | Evaluates request payload `{"request_id": "REQ-1001", "architecture": "single"}` |

---

## 9. Evaluation Results & Comparative Scorecard

Both architectures were benchmarked across the **6 Public Evaluation Cases** and **15 Qualitative Edge-Case Cassettes** (including budget deficits, tool overlaps, prompt injections, and API outages):

```bash
# Run public evaluation harness (6/6 PASS on both architectures)
./run.sh --eval
```

### Comparative Evaluation Scorecard
| Dimension | Architecture A (Single-Agent) | Architecture B (Staged Two-Agent) |
|:---|:---:|:---:|
| **Deterministic Parity** | **15/15 (100.0%)** | **15/15 (100.0%)** |
| **Human Review Required** | **100.0% (Mandatory)** | **100.0% (Mandatory)** |
| **Prompt Injection Defense** | **100.0% Neutralized** | **100.0% Neutralized** |
| **Grounding Score (0–3)** | **3.00 / 3.00** | **3.00 / 3.00** |
| **Clarification Score (0–3)** | **3.00 / 3.00** | **3.00 / 3.00** |
| **LLM Calls per Request** | **1 call** | **2 calls** |
| **Tool Calls per Request** | **5 calls** | **5 calls** |
| **Local Warm P50 Latency** | **26.67 ms** | **26.03 ms** |
| **Local Warm P95 Latency** | **35.20 ms** | **31.08 ms** |
| **Token Consumption** | **~1,200 tokens** | **~2,400 tokens (2x cost)** |
| **Orchestration Complexity** | **LOW (Single failure domain)** | **MEDIUM-HIGH (Sequential handoff)** |
| **Weighted Total Score (0–100)**| **91.67 / 100.00** | **95.00 / 100.00** |

---

## 10. FINAL QUESTION: Which Architecture Would You Ship — and Why?

> ### **Decision: Ship Architecture A (Single-Agent Baseline)**

### Evidence-Backed Rationale:
1. **100% Policy & Safety Parity:**  
   Our comparative benchmark proves that Architecture A achieves **100% parity** with Architecture B on recommendation accuracy, approver routing, risk flag identification, and prompt injection defense. Because policy enforcement is grounded in authoritative deterministic tools, adding a second LLM agent provides **zero incremental accuracy**.
2. **Cost & Latency Efficiency:**  
   Architecture A requires **exactly 1 LLM call** versus 2 sequential LLM calls in Architecture B. In live cloud deployments, Architecture A cuts token inference costs by **50%** and avoids sequential round-trip latency delays.
3. **Simpler Operational Footprint:**  
   Architecture A possesses a single failure boundary. If the LLM call times out or fails, the deterministic fallback immediately protects the workflow. In Architecture B, sequential agent handoffs double the risk of JSON parsing errors, network timeouts, and serialization mismatches.
4. **Adherence to Core Engineering Principles:**  
   *"A simpler system that performs as well or better is a stronger answer than unnecessary orchestration."* Unnecessary multi-agent orchestration introduces technical debt without commercial or governance benefit. Architecture A is the robust, production-grade choice.

*(Refer to the 443-word Architecture Decision Memo in [`templates/architecture_decision.md`](templates/architecture_decision.md) for the complete executive memorandum).*

---

## 11. Security & Safety Defenses

1. **Prompt Injection Quarantine:** Requester justification text is wrapped in data boundaries (`<<<UNTRUSTED_REQUEST_TEXT>>>`). System instructions override attempts are ignored.
2. **Approval Claim Sanitization:** Natural language claims like "auto-approved" or "purchase approved" are sanitized via regex to `[unauthorized claim removed]`.
3. **Hard Human Review Invariant:** `human_review_required = True` is programmatically enforced by post-validators.
4. **Resilient Fallback:** LLM provider timeouts (15s) or malformed JSON payloads automatically trigger deterministic fallbacks, preventing crashes.

---

## 12. Known Limitations

- **Sequential Latency in Architecture B:** Agent 2 strictly depends on Agent 1's structured dossier, doubling round-trip network latency in staged cloud mode.
- **Static Ingestion Data:** Currently evaluates against local CSV/JSON snapshots; production ERP integrations (Coupa, Workday, SAP) will require asynchronous data connectors.
- **Catalog Similarity Heuristics:** Current catalog matching uses category and substring matching; large-scale enterprise deployments (10,000+ SKUs) will benefit from semantic vector embeddings.

---

## 13. Documentation Index

Detailed technical specifications are located in `docs/fde/`:
- [`docs/fde/27_comparative_evaluation.md`](docs/fde/27_comparative_evaluation.md) — Evaluation methodology, 15 qualitative cases, and benchmark metrics.
- [`docs/fde/28_architecture_decision.md`](docs/fde/28_architecture_decision.md) — Complete FDE Architecture Decision Memo (<= 500 words).
- [`docs/fde/30_demo_runbook.md`](docs/fde/30_demo_runbook.md) — 6 interactive evaluator demonstration scenarios.
- [`docs/fde/31_production_architecture.md`](docs/fde/31_production_architecture.md) — Production architecture and trust boundaries.
- [`docs/fde/32_deployment_runbook.md`](docs/fde/32_deployment_runbook.md) — Operations guide (Local, Docker, probes, rollback).
- [`docs/fde/33_production_readiness_checklist.md`](docs/fde/33_production_readiness_checklist.md) — Production readiness audit checklist.
- [`docs/fde/34_assessment_requirements.md`](docs/fde/34_assessment_requirements.md) — Official Assessment Requirement Matrix (Rubric & Deliverables).
