"""Architecture B: Staged Two-Agent Architecture Orchestrator.

Orchestrates the sequential handoff from:
Agent 1 (Intake & Overlap Specialist)
    ↓ [IntakeOverlapDossier]
Agent 2 (Governance & Triage Specialist)
    ↓ [GovernanceTriageDossier]
Deterministic Response Validator
    ↓
StagedAgentResponse
"""

from __future__ import annotations

import logging
from typing import Any

from src.agents.contracts import StagedAgentResponse, validate_and_assemble_staged_response
from src.agents.governance_triage_agent import GovernanceTriageAgent
from src.agents.intake_overlap_agent import IntakeOverlapAgent
from src.contracts import RunTelemetry
from src.decision_engine import make_procurement_decision_with_trace
from src.llm.client import BaseLLMClient
from src.tools.request_context import get_request_context
from src.tools.software_catalog import search_software_catalog
from src.tools.vendor_risk import get_vendor_risk

logger = logging.getLogger(__name__)


class StagedAgents:
    """Architecture B: Staged Two-Agent Architecture.

    Divides responsibilities cleanly between:
    - Agent 1: Business intent understanding and functional catalog overlap.
    - Agent 2: Governance analysis, policy explanation, and human reviewer briefing.
    Both agents operate on shared verified evidence; policy enforcement remains 100% deterministic.
    """

    def __init__(self, llm_client: BaseLLMClient | None = None) -> None:
        self.llm_client = llm_client

    def run(self, request_id: str) -> StagedAgentResponse:
        """Execute the staged two-agent procurement pipeline."""
        # -------------------------------------------------------------
        # STEP 1: EXECUTE DETERMINISTIC PIPELINE (AUTHORITATIVE POLICY)
        # -------------------------------------------------------------
        det_result = make_procurement_decision_with_trace(request_id)
        decision = det_result.decision

        tool_calls = decision.telemetry.tool_calls if decision.telemetry else 5
        tool_names = list(decision.telemetry.tool_names) if decision.telemetry else []
        agent_names: list[str] = []
        llm_calls_count = 0

        # -------------------------------------------------------------
        # STEP 2: EXTRACT SHARED TOOL CONTEXT (Zero Redundant Queries)
        # -------------------------------------------------------------
        context_res = get_request_context(request_id)
        context_data = context_res.data or {}
        req = context_data.get("request", {})
        product_name = req.get("product_name")
        vendor_name = req.get("vendor_name", "")
        category = req.get("category")

        catalog_res = search_software_catalog(
            product_name=product_name,
            vendor_name=vendor_name,
            category=category,
        )
        catalog_data = catalog_res.data or {}

        vendor_risk_res = get_vendor_risk(vendor_name=vendor_name)
        vendor_risk_data = vendor_risk_res.data or {}

        # -------------------------------------------------------------
        # STEP 3: AGENT 1 — INTAKE & FUNCTIONAL OVERLAP SPECIALIST
        # -------------------------------------------------------------
        agent1 = IntakeOverlapAgent(llm_client=self.llm_client)
        llm_calls_count += 1
        agent_names.append("intake_overlap")
        intake_dossier = agent1.run(
            request_id=request_id,
            context_data=context_data,
            catalog_data=catalog_data,
        )

        # -------------------------------------------------------------
        # STEP 4: AGENT 2 — GOVERNANCE & TRIAGE SPECIALIST (STRUCTURED HANDOFF)
        # -------------------------------------------------------------
        agent2 = GovernanceTriageAgent(llm_client=self.llm_client)
        llm_calls_count += 1
        agent_names.append("governance_triage")
        gov_dossier = agent2.run(
            request_id=request_id,
            intake_dossier=intake_dossier,
            context_data=context_data,
            vendor_risk_data=vendor_risk_data,
            decision=decision,
        )

        # -------------------------------------------------------------
        # STEP 5: FINAL MERGE & DETERMINISTIC RESPONSE VALIDATION
        # -------------------------------------------------------------
        telemetry = RunTelemetry(
            llm_calls=llm_calls_count,
            tool_calls=tool_calls,
            tool_names=tool_names,
            agent_names=agent_names,
        )

        final_response = validate_and_assemble_staged_response(
            intake_dossier=intake_dossier,
            gov_dossier=gov_dossier,
            decision=decision,
            telemetry=telemetry,
        )

        return final_response


def run_staged_agents(
    request_id: str,
    client: BaseLLMClient | None = None,
) -> StagedAgentResponse:
    """Convenience entrypoint for executing Architecture B."""
    pipeline = StagedAgents(llm_client=client)
    return pipeline.run(request_id)
