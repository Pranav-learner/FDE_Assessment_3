from __future__ import annotations

from src.agents.single_agent import run_single_agent
from src.contracts import Architecture, ProcurementDecision
from src.decision_engine import make_procurement_decision


def handle_request(request_id: str, architecture: Architecture = "single") -> ProcurementDecision:
    """Assessment adapter and orchestration boundary.

    Dispatches procurement decision handling:
    - architecture="single": Architecture A (Single-Agent Baseline) with deterministic grounding.
    - architecture="staged": Deterministic compatibility baseline until Phase 5 implements Architecture B.
    """
    if architecture not in ("single", "staged"):
        raise ValueError(f"Unknown architecture: '{architecture}'. Expected 'single' or 'staged'.")

    if architecture == "single":
        return run_single_agent(request_id)

    # Staged / Architecture B compatibility baseline (to be implemented in Phase 5)
    return make_procurement_decision(request_id)
