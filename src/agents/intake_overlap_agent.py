"""Architecture B: Agent 1 — Intake & Functional Overlap Specialist.

Focuses exclusively on understanding user intent, extracting workflow requirements,
and assessing software catalog alternatives and functional overlap.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from src.agents.contracts import IntakeOverlapDossier
from src.agents.prompts import (
    AGENT1_INTAKE_OVERLAP_SYSTEM_PROMPT,
    format_agent1_intake_user_prompt,
)
from src.llm.client import BaseLLMClient, LLMMessage, get_llm_client

logger = logging.getLogger(__name__)


class IntakeOverlapAgent:
    """Agent 1 in Architecture B: Business Intent & Functional Overlap Specialist.

    Responsible for extracting business requirements and analyzing functional
    catalog overlap without making policy determinations or approval decisions.
    """

    def __init__(self, llm_client: BaseLLMClient | None = None) -> None:
        self.llm_client = llm_client

    def run(
        self,
        request_id: str,
        context_data: dict[str, Any],
        catalog_data: dict[str, Any],
    ) -> IntakeOverlapDossier:
        """Analyze business intent and catalog overlap, returning a structured dossier."""
        req = context_data.get("request", {})
        requester = context_data.get("requester", {})
        product_name = req.get("product_name", "Unknown Product")
        department = context_data.get("department", "Unknown Department")
        has_overlap = catalog_data.get("has_overlap", False)

        # 1. Format prompts
        user_prompt = format_agent1_intake_user_prompt(
            request_data=context_data,
            catalog_overlap_data=catalog_data,
        )
        messages = [
            LLMMessage(role="system", content=AGENT1_INTAKE_OVERLAP_SYSTEM_PROMPT),
            LLMMessage(role="user", content=user_prompt),
        ]

        # 2. Call LLM
        client = self.llm_client or get_llm_client()
        dossier: IntakeOverlapDossier | None = None

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
            dossier = IntakeOverlapDossier.model_validate(payload)

        except Exception as exc:
            logger.warning(
                f"Agent 1 (Intake & Overlap) failed for {request_id} ({type(exc).__name__}: {exc}). "
                f"Executing safe deterministic fallback dossier."
            )
            dossier = None

        # 3. Deterministic Fallback if LLM failed
        if dossier is None:
            catalog_tools = [
                t.get("product_name", "")
                for t in catalog_data.get("potential_alternatives", [])
                if t.get("product_name")
            ]
            fit_text = (
                f"Catalog analysis identified potential functional overlap with active tools: {', '.join(catalog_tools)}."
                if has_overlap
                else "No active software overlap detected in the corporate inventory for this product or category."
            )

            unresolved_q: list[str] = []
            if req.get("annual_cost_usd") is None:
                unresolved_q.append("Annual software cost estimate in USD.")
            if req.get("user_count") is None:
                unresolved_q.append("Expected user seat or license count.")
            if req.get("data_access_level") in (None, "", "unknown"):
                unresolved_q.append("Declared data access classification.")

            dossier = IntakeOverlapDossier(
                request_id=request_id,
                business_need=req.get("business_justification") or f"Procurement of {product_name} for {department}.",
                intended_workflow=f"Workflow execution by {requester.get('name', 'user')} in {department}.",
                user_persona=f"{department} team member ({requester.get('title', 'Employee')}).",
                requested_capabilities=[f"Functionality provided by {product_name}"],
                relevant_catalog_matches=catalog_tools,
                existing_tool_overlap=has_overlap,
                functional_fit_analysis=fit_text,
                functional_gaps=["Requires workflow review against catalog alternative"] if has_overlap else [],
                unresolved_questions=unresolved_q,
                confidence=0.90,
            )

        return dossier
