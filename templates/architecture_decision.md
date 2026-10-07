# Architecture Decision Memo

**Maximum length: 500 words**

## Decision
We recommend shipping **Architecture A (Single-Agent Baseline)** for the production MVP, with **Architecture B (Staged Two-Agent)** designated as an optional asynchronous escalation path for complex high-spend requests ($25,000+).

## Evidence
Both architectures were evaluated against the exact same 15-case qualitative benchmark and 6-case public evaluation suite under authoritative deterministic policy governance.

| Metric | Single agent (Architecture A) | Staged / 2-agent (Architecture B) |
|---|---:|---:|
| Cases passing quality criteria | 15 / 15 (100%) | 15 / 15 (100%) |
| Avg warm latency (local) | 46.3 ms | 47.6 ms |
| Estimated live network latency | 1.2 – 1.8 s | 2.6 – 4.2 s |
| Avg LLM calls | 1 | 2 |
| Avg tool calls | 5 | 5 |
| Notable policy/grounding failures | 0 (100% policy parity) | 0 (100% policy parity) |
| Prompt injection pass rate | 100% | 100% |
| Weighted evaluation score | 91.67 / 100 | 95.00 / 100 |

Both architectures achieved 100% deterministic parity across recommendations, required approval rosters, missing information identification, risk flags, and mandatory human review (`human_review_required = True`). Neither architecture produced ungrounded or fabricated policy claims.

## Trade-offs
- **What improved in Architecture B:** Agent 1 provided deeper functional gap decomposition (catalog fit score 3.0 vs 1.4), and Agent 2 generated more granular cross-domain governance briefs for human reviewers (governance score 3.0 vs 2.0).
- **What became slower and more complex:** Architecture B introduces a sequential second LLM call, doubling live round-trip latency, consuming ~1.8× the token budget, and introducing two separate LLM failure/fallback boundaries that require structured schema serialization.

## Risks / limitations
1. **Mock vs Production Provider Variance:** While local unit tests verify zero failures under deterministic fallbacks, live production LLMs will exhibit non-deterministic parsing jitter that requires persistent monitoring.
2. **Sequential Dependency:** Agent 2 strictly depends on Agent 1's structured dossier; if Agent 1 fails, Agent 2 must degrade to a deterministic fallback dossier.
3. **Escalation Latency:** A two-stage LLM workflow is unsuitable for synchronous user-facing chat interactions requiring sub-second response times.

## Why this is the right MVP
For enterprise procurement intake, **the authoritative decision and risk enforcement already reside in the deterministic policy engine**. The AI agent does not have approval authority, cannot clear risk flags, and cannot bypass human review.

Architecture A accomplishes the core business objective—translating deterministic policy findings into a clear, grounded executive summary and targeted clarification questions—with a single prompt, a single LLM invocation, half the token cost, and half the failure surface. It delivers 100% policy compliance without introducing premature orchestration complexity.
