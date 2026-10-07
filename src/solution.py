from __future__ import annotations

from src.contracts import Architecture, ProcurementDecision
from src.decision_engine import make_procurement_decision


def handle_request(request_id: str, architecture: Architecture = "single") -> ProcurementDecision:
    """Assessment adapter and orchestration boundary.

    Dispatches procurement decision handling.
    In Phase 3 (deterministic baseline), both architectures resolve through
    the deterministic procurement decision engine.
    In Phase 4, Architecture A (single-agent) and Architecture B (staged / 2-agent)
    will augment this pipeline with qualitative agent reasoning while preserving
    deterministic policy enforcement.
    """
    if architecture not in ("single", "staged"):
        raise ValueError(f"Unknown architecture: '{architecture}'. Expected 'single' or 'staged'.")

    # Deterministic baseline implementation (Phase 3)
    return make_procurement_decision(request_id)
