from __future__ import annotations

from src.agents.single_agent import run_single_agent
from src.agents.staged_agent import run_staged_agents
from src.contracts import Architecture, ProcurementDecision


def handle_request(request_id: str, architecture: Architecture = "single") -> ProcurementDecision:
    """Assessment adapter and orchestration boundary.

    Dispatches procurement decision handling:
    - architecture="single": Architecture A (Single-Agent Baseline)
    - architecture="staged": Architecture B (Staged Two-Agent Architecture)
    """
    if architecture not in ("single", "staged"):
        raise ValueError(f"Unknown architecture: '{architecture}'. Expected 'single' or 'staged'.")

    if architecture == "single":
        return run_single_agent(request_id)
    else:
        return run_staged_agents(request_id)
