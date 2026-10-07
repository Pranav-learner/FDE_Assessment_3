from __future__ import annotations

import json
import logging
import re
import sys
from pathlib import Path
from typing import Literal
from urllib.parse import unquote

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.solution import handle_request

logger = logging.getLogger("copilot.api")

DATA = json.loads((ROOT / "data" / "vendor_risk.json").read_text(encoding="utf-8"))

app = FastAPI(
    title="AI Procurement Request Copilot & Mock Vendor API",
    version="1.0.0",
    description="FDE Procurement Request Copilot Evaluation & Mock Vendor Risk Service",
)


class EvaluationRequest(BaseModel):
    request_id: str = Field(..., description="Target purchase request ID (e.g. REQ-1001)")
    architecture: Literal["single", "staged"] = Field(
        default="single",
        description="Architecture to execute: 'single' (Core Production MVP) or 'staged' (Two-Agent Escalation)",
    )


@app.get("/")
def root() -> dict:
    return {
        "service": "AI Procurement Request Copilot",
        "version": "1.0.0",
        "default_architecture": "single",
        "endpoints": [
            "/health",
            "/ready",
            "/procurement/evaluate",
            "/vendor-risk/{vendor_name}",
        ],
    }


@app.get("/health")
def health() -> dict:
    """Process liveness probe."""
    return {"status": "ok"}


@app.get("/ready")
def ready() -> dict:
    """Dependency readiness probe."""
    data_dir = ROOT / "data"
    required_files = [
        "requests.json",
        "employees.csv",
        "department_budgets.csv",
        "software_catalog.csv",
        "vendors.csv",
        "vendor_risk.json",
        "procurement_policy.md",
    ]
    missing = [f for f in required_files if not (data_dir / f).exists()]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Missing required data assets: {', '.join(missing)}",
        )
    return {
        "status": "ready",
        "assets_loaded": len(required_files),
        "default_architecture": "single",
    }


@app.get("/vendor-risk/{vendor_name}")
def vendor_risk(vendor_name: str) -> dict:
    name = unquote(vendor_name)
    record = DATA.get(name)
    if record is None:
        raise HTTPException(status_code=404, detail=f"No vendor-risk record for '{name}'")
    if record.get("force_error"):
        raise HTTPException(status_code=503, detail=record.get("error_message", "Vendor-risk service unavailable"))
    return {"vendor_name": name, **record}


@app.post("/procurement/evaluate")
def evaluate_request(payload: EvaluationRequest) -> dict:
    """Evaluate procurement request through copilot architecture."""
    # Sanitize request_id against path traversal or injection
    if not re.match(r"^[A-Za-z0-9_-]{1,50}$", payload.request_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid request_id format: '{payload.request_id}'. Must be alphanumeric.",
        )

    try:
        decision = handle_request(payload.request_id, architecture=payload.architecture)
        return decision.model_dump(mode="json")
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Request not found: '{payload.request_id}'",
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except Exception as exc:
        logger.error(f"Error evaluating request {payload.request_id}: {exc}", exc_info=True)
        # Never leak internal stack trace to client
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while evaluating the procurement request.",
        )
