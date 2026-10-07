"""Architecture A: Single-Agent Baseline Implementation.

Coordinates evidence intake, deterministic procurement policy evaluation,
qualitative reasoning via a single LLM, response validation, and telemetry tracking.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

from src.agents.contracts import SingleAgentResponse, validate_and_assemble_response
from src.agents.prompts import (
    SINGLE_AGENT_SYSTEM_PROMPT,
    format_single_agent_user_prompt,
)
from src.contracts import RunTelemetry
from src.decision_engine import make_procurement_decision_with_trace
from src.llm.client import BaseLLMClient, LLMMessage, get_llm_client
from src.tools.request_context import get_request_context
from src.tools.software_catalog import search_software_catalog
from src.tools.vendor_risk import get_vendor_risk

logger = logging.getLogger(__name__)


class SingleAgent:
    """Architecture A: Single LLM-based Procurement Agent.

    The single agent consumes the deterministic foundation as ground truth,
    evaluates qualitative business context, and communicates findings clearly
    to stakeholders while strictly preserving human authority.
    """

    def __init__(self, llm_client: BaseLLMClient | None = None) -> None:
        self.llm_client = llm_client

    def run(self, request_id: str) -> SingleAgentResponse:
        """Execute Architecture A lifecycle for a single procurement request."""
        start_time = time.perf_counter()

        # -------------------------------------------------------------
        # STEP 1: EXECUTE DETERMINISTIC PIPELINE (AUTHORITATIVE GROUND TRUTH)
        # -------------------------------------------------------------
        # Invokes request_context, software_catalog, vendor_risk,
        # procurement_policy, and rule_engine in strict deterministic sequence.
        det_result = make_procurement_decision_with_trace(request_id)
        decision = det_result.decision

        # Extract tool telemetry from deterministic run
        tool_calls = decision.telemetry.tool_calls if decision.telemetry else 5
        tool_names = list(decision.telemetry.tool_names) if decision.telemetry else []

        # -------------------------------------------------------------
        # STEP 2: EXTRACT STRUCTURED TOOL CONTEXT FOR AGENT REASONING
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
        # STEP 3: PREPARE PROMPTS FOR THE SINGLE AGENT
        # -------------------------------------------------------------
        user_prompt_content = format_single_agent_user_prompt(
            request_data=context_data,
            catalog_overlap_data=catalog_data,
            vendor_risk_data=vendor_risk_data,
            deterministic_decision=decision,
        )

        messages = [
            LLMMessage(role="system", content=SINGLE_AGENT_SYSTEM_PROMPT),
            LLMMessage(role="user", content=user_prompt_content),
        ]

        # -------------------------------------------------------------
        # STEP 4: CALL LLM REASONING LAYER WITH RESILIENT FALLBACK
        # -------------------------------------------------------------
        client = self.llm_client or get_llm_client()
        llm_calls_count = 0
        llm_payload: dict[str, Any] | None = None

        try:
            llm_calls_count += 1
            response = client.generate(messages=messages, temperature=0.0, timeout=12.0)
            
            # Parse structured JSON output
            raw_text = response.text.strip()
            # Strip markdown code fences if model returned them
            if raw_text.startswith("```json"):
                raw_text = raw_text[len("```json"):].strip()
            elif raw_text.startswith("```"):
                raw_text = raw_text[len("```"):].strip()
            if raw_text.endswith("```"):
                raw_text = raw_text[:-len("```")].strip()

            llm_payload = json.loads(raw_text)

        except Exception as exc:
            logger.warning(
                f"Architecture A: LLM generation or parsing failed for {request_id} ({type(exc).__name__}: {exc}). "
                f"Executing safe deterministic fallback."
            )
            llm_payload = None

        # -------------------------------------------------------------
        # STEP 5: VALIDATE AND ASSEMBLE FINAL SINGLE AGENT RESPONSE
        # -------------------------------------------------------------
        # Assembles response, strictly validating that LLM has not modified
        # recommendation, required approvals, missing info, risk flags, or human review.
        telemetry = RunTelemetry(
            llm_calls=llm_calls_count,
            tool_calls=tool_calls,
            tool_names=tool_names,
        )

        final_response = validate_and_assemble_response(
            llm_payload=llm_payload,
            decision=decision,
            telemetry=telemetry,
        )

        return final_response


def run_single_agent(
    request_id: str,
    client: BaseLLMClient | None = None,
) -> SingleAgentResponse:
    """Convenience entrypoint for executing Architecture A."""
    agent = SingleAgent(llm_client=client)
    return agent.run(request_id)
