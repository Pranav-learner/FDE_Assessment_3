# AI Procurement Request Copilot

**Autonomous Decision Support & Procurement Intake Platform**  
*Forward Deployed Engineering (FDE) Assessment 3 Deliverable*

---

## 1. Problem Statement
Enterprise procurement teams face severe operational bottlenecks during software intake. Requesters submit vague justifications, duplicate existing corporate tooling, and fail to provide required security or commercial terms. Human procurement analysts spend hours manually reviewing catalogs, verifying departmental budgets, and interpreting multi-domain compliance policies (InfoSec, Privacy/GDPR, Legal, and Finance).

---

## 2. FDE Solution Overview
The **AI Procurement Request Copilot** is an enterprise decision-support copilot designed for procurement teams. It ingests software purchase requests, gathers verified evidence across corporate databases and external risk APIs, executes deterministic policy rules, detects SaaS redundancy, and generates structured, actionable triage dossiers.

**Core Invariant:** The copilot is strictly advisory. **Human review is always mandatory (`human_review_required = True`)**, and the system never executes autonomous purchases or contract approvals.

---

## 3. High-Level Architecture
The platform enforces a tripartite architecture separating untrusted inputs, authoritative deterministic policy rules, and qualitative LLM synthesis:

```
[Inbound Request] ──> [Deterministic Tools & Rule Engine] ──> Authoritative Policy Facts
                              │                                      │
                              ▼                                      ▼
                   [Qualitative LLM Layer] ───────────────> [Deterministic Validator]
                   (Single or Staged Synthesis)                      │
                                                                     ▼
                                                          ProcurementDecision
                                                      (Human Review Always Required)
```

### Deterministic Policy Boundary
All financial delegation thresholds, approver rosters (`Manager`, `Department Head`, `Procurement`, `Finance`, `CFO`, `Security`, `Privacy`, `Legal`), missing data flags, and prompt injection defenses are executed in **deterministic Python code**. The LLM layer cannot override corporate policy or bypass approval gates.

---

## 4. Architectures Compared

### Architecture A: Single-Agent Baseline (DEFAULT / Core Production MVP)
- Executes deterministic tools once, followed by **exactly 1 LLM synthesis call**.
- Combines business intent, catalog overlap, and risk explanations into a single executive summary.
- Sub-second local execution (~46 ms) and ~1.2s live network latency.
- Half the token budget (~1,200 tokens/request) and a single failure boundary.

### Architecture B: Staged Two-Agent Architecture (Optional Escalation)
- Splits synthesis into two specialized agents connected via a typed Pydantic contract:
  1. **Agent 1 (Intake & Overlap Specialist):** Decomposes business need, user persona, and catalog functional gaps (`IntakeOverlapDossier`).
  2. **Agent 2 (Governance & Triage Specialist):** Synthesizes cross-domain risks into an executive triage brief (`GovernanceTriageDossier`).
- Consumes ~2,400 tokens/request with sequential latency (~2.6s–4.0s live).

### Why Architecture A is the Production Default
Both architectures achieve **100% deterministic policy parity** because the underlying rule engine is authoritative. Architecture A achieves identical compliance enforcement at **half the token cost, half the latency, and half the failure surface**. Architecture B is retained as an optional escalation path for Tier 4 high-spend ($25,000+) purchases and contested catalog overlap disputes.

---

## 5. Quick Start & Setup

### 5.1 Local Python Environment
```bash
# 1. Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Verify setup (pre-flight checks pass without external keys)
python verify_setup.py

# 4. Start local mock vendor-risk API & Streamlit web UI
python run_local.py
```
- **FastAPI Vendor-Risk & Copilot API:** `http://127.0.0.1:8001`
- **Streamlit Web UI:** `http://127.0.0.1:8501`

### 5.2 Environment Configuration
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Key configuration parameters:
- `LLM_MODE=mock`: Offline deterministic engine (default, grading-safe). Set `live` for cloud providers.
- `VENDOR_RISK_BASE_URL=http://127.0.0.1:8001`: Upstream vendor risk assessment endpoint.
- `DEFAULT_ARCHITECTURE=single`: Default execution pipeline.
- Provider API keys (`OPENAI_API_KEY`, etc.) are optional and required only when `LLM_MODE=live`.

---

## 6. Command Line Interface (CLI)

The CLI supports human-readable triage reports and machine-readable JSON:

```bash
# Evaluate using default Core Production MVP (Architecture A)
python app.py --request-id REQ-1001

# Explicitly select Architecture A
python app.py --request-id REQ-1002 --architecture single

# Select Staged Two-Agent Escalation (Architecture B)
python app.py --request-id REQ-1005 --architecture staged

# Machine-readable JSON output (clean stdout for automated pipelines)
python app.py --request-id REQ-1001 --json

# List all available sample requests in the database
python app.py --list

# View CLI options
python app.py --help
```

---

## 7. HTTP REST API

FastAPI endpoints running on port 8001:

| Method | Endpoint | Description |
|:---|:---|:---|
| `GET` | `/health` | Process liveness probe (`{"status":"ok"}`) |
| `GET` | `/ready` | Dependency readiness probe (verifies 7 data assets on disk) |
| `GET` | `/vendor-risk/{vendor}` | External vendor risk record |
| `POST` | `/procurement/evaluate` | Evaluates request payload `{"request_id": "REQ-1001", "architecture": "single"}` |

---

## 8. Docker & Container Deployment

The application is containerized with a non-root user (`appuser`, UID 1000) based on `python:3.11-slim`:

```bash
# Build production Docker image
docker build -t fde-procurement-copilot:latest .

# Run standalone container
docker run -d --name fde-procurement -p 8001:8001 -p 8501:8501 fde-procurement-copilot:latest

# Verify health
curl -s http://127.0.0.1:8001/health

# Multi-service orchestration (FastAPI + Streamlit)
docker compose up -d

# Stop services
docker compose down
```

---

## 9. Testing & Evaluation

### 9.1 Test Suites (130 Tests, 0 Failures)
```bash
# Run all unit, rule, agent, parity, and E2E tests
python -m unittest discover tests -v

# Run End-to-End integration suite
python -m unittest tests/test_e2e.py -v
```

### 9.2 Public Evaluation Harness (6/6 PASS)
```bash
python evals/run_public_evals.py --architecture single
python evals/run_public_evals.py --architecture staged
```

### 9.3 Comparative Benchmark & Scorecard
```bash
python evals/run_comparison.py
```
Outputs `evals/qualitative_results.csv` and reports a full scorecard across 15 qualitative cases and 30 warm benchmark repetitions.

---

## 10. Security & Safety Defenses
1. **Prompt Injection Quarantine:** Requester justification text is wrapped in data boundaries (`<<<UNTRUSTED_REQUEST_TEXT>>>`). System instructions override attempts are ignored.
2. **Approval Claim Sanitization:** Natural language claims like "auto-approved" or "purchase approved" are sanitized via regex to `[unauthorized claim removed]`.
3. **Hard Human Review Invariant:** `human_review_required = True` is programmatically enforced by post-validators.
4. **Resilient Fallback:** LLM provider timeouts (15s) or malformed JSON payloads automatically trigger deterministic fallbacks, preventing crashes.

---

## 11. Known Limitations
- **Sequential Latency in Architecture B:** Agent 2 strictly depends on Agent 1's structured dossier, doubling round-trip latency in staged mode.
- **Static Ingestion Data:** Currently evaluates against local CSV/JSON snapshots; production ERP integrations (Coupa, Workday) will require asynchronous data connectors.

---

## 12. Documentation Index
Detailed technical specifications are located in `docs/fde/`:
- [`docs/fde/27_comparative_evaluation.md`](docs/fde/27_comparative_evaluation.md) — Evaluation methodology, 15 qualitative cases, and benchmark metrics.
- [`docs/fde/28_architecture_decision.md`](docs/fde/28_architecture_decision.md) — Complete FDE Architecture Decision Memo.
- [`docs/fde/30_demo_runbook.md`](docs/fde/30_demo_runbook.md) — 6 interactive evaluator demonstration scenarios.
- [`docs/fde/31_production_architecture.md`](docs/fde/31_production_architecture.md) — Production architecture and trust boundaries.
- [`docs/fde/32_deployment_runbook.md`](docs/fde/32_deployment_runbook.md) — Operations guide (Local, Docker, probes, rollback).
- [`docs/fde/33_production_readiness_checklist.md`](docs/fde/33_production_readiness_checklist.md) — Production readiness audit checklist.
