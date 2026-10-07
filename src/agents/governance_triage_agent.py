"""Architecture B: Agent 2 — Governance & Triage Specialist.

Consumes the structured intake dossier from Agent 1 alongside authoritative
policy decisions to synthesize an executive governance triage dossier for human reviewers.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from src.agents.contracts import GovernanceTriageDossier, IntakeOverlapDossier
from src.agents.prompts import (
    AGENT2_GOVERNANCE_TRIAGE_SYSTEM_PROMPT,
    format_agent2_governance_user_prompt,
)
from src.contracts import ProcurementDecision
from src.llm.client import BaseLLMClient, LLMMessage, get_llm_client

logger = logging.getLogger(__name__)


class GovernanceTriageAgent:
    """Agent 2 in Architecture B: Governance & Triage Specialist.

    Responsible for evaluating financial, security, privacy, and legal risks,
    synthesizing stakeholder impact, and preparing the human approval briefing.
    """

    def __init__(self, llm_client: BaseLLMClient | None = None) -> None:
        self.llm_client = llm_client

    def run(
        self,
        request_id: str,
        intake_dossier: IntakeOverlapDossier,
        context_data: dict[str, Any],
        vendor_risk_data: dict[str, Any],
        decision: ProcurementDecision,
    ) -> GovernanceTriageDossier:
        """Synthesize governance and triage analysis from Agent 1 dossier and policy facts."""
        user_prompt = format_agent2_governance_user_prompt(
            intake_dossier_data=intake_dossier.model_dump(),
            request_data=context_data,
            vendor_risk_data=vendor_risk_data,
            deterministic_decision=decision,
        )

        messages = [
            LLMMessage(role="system", content=AGENT2_GOVERNANCE_TRIAGE_SYSTEM_PROMPT),
            LLMMessage(role="user", content=user_prompt),
        ]

        client = self.llm_client or get_llm_client()
        dossier: GovernanceTriageDossier | None = None

        try:
            resp = client.generate(messages=messages, temperature=0.0, timeout=12.0)
            raw_text = resp.text.strip()
            if raw_text.startswith("```json"):
                raw_text = raw_text[len("```json"):].strip()
            elif raw_text.startswith("```"):
                raw_text = raw_text[len("```"):].strip()
            if raw_text.endswith("```"):
                raw_text = raw_text[:-len("```")].strip()

            payload = json.loads(raw_text)
            payload["request_id"] = request_id
            dossier = GovernanceTriageDossier.model_validate(payload)

        except Exception as exc:
            logger.warning(
                f"Agent 2 (Governance & Triage) failed for {request_id} ({type(exc).__name__}: {exc}). "
                f"Executing safe deterministic fallback dossier."
            )
            dossier = None

        # Deterministic Fallback if LLM failed
        if dossier is None:
            approvers_str = ", ".join(decision.required_approvals) if decision.required_approvals else "Procurement"
            risks_str = ", ".join(decision.risk_flags) if decision.risk_flags else "none"

            actions = [f"Obtain approval from {app}" for app in decision.required_approvals]
            if "vendor_risk_unavailable" in decision.risk_flags:
                actions.insert(0, "Initiate manual security verification due to vendor risk API outage")
            if "existing_tool_overlap" in decision.risk_flags:
                actions.insert(0, "Verify functional differentiation against existing catalog tools")

            dossier = GovernanceTriageDossier(
                request_id=request_id,
                executive_summary=(
                    f"Procurement request {request_id} determined as {decision.recommendation}. "
                    f"Mandatory reviews assigned to: {approvers_str}."
                ),
                governance_summary=f"Request evaluated under corporate policy with active risk flags: {risks_str}.",
                financial_summary=f"Financial spend review routed to {', '.join([a for a in decision.required_approvals if a in ('Manager', 'Department Head', 'Finance', 'CFO')])}.",
                security_summary="InfoSec review required based on data access level or vendor status." if "security_review_required" in decision.risk_flags else "Standard security controls apply.",
                privacy_summary="Data privacy review required based on PII or cross-region processing." if "privacy_review_required" in decision.risk_flags else "No elevated privacy triggers identified.",
                legal_summary="Legal terms review required for new vendor spend." if "legal_review_required" in decision.risk_flags else "Existing contract terms apply.",
                risk_explanation=f"Policy checks surfaced the following governance flags: {risks_str}.",
                recommended_human_actions=actions,
                clarification_questions=[f"Please clarify {item}" for item in decision.missing_information],
            )

        return dossier
