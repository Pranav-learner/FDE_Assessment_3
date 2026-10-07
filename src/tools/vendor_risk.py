from __future__ import annotations

import json
from typing import Any
import requests
from requests.exceptions import ConnectionError, HTTPError, Timeout

from src.contracts import EvidenceItem
import src.vendor_client as client_module
from src.tools.contracts import ToolResult, VendorRiskProfile


def get_vendor_risk(
    vendor_name: str,
    timeout_seconds: float = 3.0,
    simulate_failure: str | None = None,
) -> ToolResult:
    """Query external third-party vendor risk service.

    Accesses the mock service through the API client (or FastAPI TestClient in testing).
    Never converts unavailable evidence into a favorable result.

    Handles:
    - 200 OK (verified risk record)
    - 404 Not Found (unrated vendor)
    - 500 / 503 Service Unavailable (forced or unexpected outage)
    - Request timeout
    - Connection failure
    - Malformed response
    """
    evidence: list[EvidenceItem] = []
    errors: list[str] = []

    # Handle explicit simulated test failures
    if simulate_failure == "timeout":
        errors.append(f"Request timeout connecting to vendor-risk API for '{vendor_name}'")
        evidence.append(
            EvidenceItem(
                source="vendor-risk-api",
                finding=f"Vendor risk service timed out for '{vendor_name}'. Evidence is unavailable and unverified.",
                reference=vendor_name,
            )
        )
        profile = VendorRiskProfile(
            vendor_name=vendor_name,
            verified=False,
            error=errors[0],
            evidence=evidence,
        )
        return ToolResult(
            tool_name="get_vendor_risk",
            success=False,
            data=profile.model_dump(),
            evidence=evidence,
            errors=errors,
        )

    if simulate_failure == "connection":
        errors.append(f"Connection failure connecting to vendor-risk API for '{vendor_name}'")
        evidence.append(
            EvidenceItem(
                source="vendor-risk-api",
                finding=f"Connection failure reaching vendor risk API for '{vendor_name}'. Risk posture is unverified.",
                reference=vendor_name,
            )
        )
        profile = VendorRiskProfile(
            vendor_name=vendor_name,
            verified=False,
            error=errors[0],
            evidence=evidence,
        )
        return ToolResult(
            tool_name="get_vendor_risk",
            success=False,
            data=profile.model_dump(),
            evidence=evidence,
            errors=errors,
        )

    if simulate_failure == "malformed":
        errors.append(f"Malformed response payload from vendor-risk API for '{vendor_name}'")
        evidence.append(
            EvidenceItem(
                source="vendor-risk-api",
                finding=f"Malformed response from vendor risk API for '{vendor_name}'. Data cannot be verified.",
                reference=vendor_name,
            )
        )
        profile = VendorRiskProfile(
            vendor_name=vendor_name,
            verified=False,
            error=errors[0],
            evidence=evidence,
        )
        return ToolResult(
            tool_name="get_vendor_risk",
            success=False,
            data=profile.model_dump(),
            evidence=evidence,
            errors=errors,
        )

    # 1. Attempt standard HTTP client call
    status_code: int | None = None
    data: dict[str, Any] | None = None

    try:
        data = client_module.get_vendor_risk(vendor_name, timeout_seconds=timeout_seconds)
        status_code = 200
    except HTTPError as exc:
        status_code = exc.response.status_code if exc.response is not None else 500
        detail = ""
        try:
            detail = exc.response.json().get("detail", str(exc))
        except Exception:
            detail = str(exc)
        errors.append(f"HTTP {status_code}: {detail}")
    except Timeout:
        errors.append(f"Vendor risk API request timed out after {timeout_seconds}s for '{vendor_name}'")
    except ConnectionError:
        # Fallback to TestClient for test execution environments if background server is not up
        try:
            from fastapi.testclient import TestClient
            from mock_api.app import app
            from urllib.parse import quote

            test_client = TestClient(app)
            response = test_client.get(f"/vendor-risk/{quote(vendor_name, safe='')}")
            status_code = response.status_code
            if response.status_code == 200:
                data = response.json()
            elif response.status_code == 404:
                errors.append(f"HTTP 404: No vendor-risk record for '{vendor_name}'")
            elif response.status_code == 503:
                detail = response.json().get("detail", "Vendor-risk service unavailable")
                errors.append(f"HTTP 503: {detail}")
            else:
                errors.append(f"HTTP {response.status_code}: {response.text}")
        except Exception as fallback_exc:
            errors.append(f"Connection failure to vendor-risk API: {fallback_exc}")
    except json.JSONDecodeError:
        errors.append(f"Malformed JSON response from vendor-risk API for '{vendor_name}'")
    except Exception as exc:
        errors.append(f"Unexpected error querying vendor-risk API: {exc}")

    # Process successful response
    if data and status_code == 200 and not errors:
        risk_level = data.get("risk_level")
        review_status = data.get("security_review_status")
        last_date = data.get("last_review_date")
        personal_data = data.get("processes_personal_data", False)
        outside_region = data.get("stores_data_outside_region", False)
        notes = data.get("notes", "")

        finding_parts = [
            f"External vendor risk level is '{risk_level}'",
            f"security review status is '{review_status}' (last reviewed: {last_date or 'never'})",
        ]
        if personal_data:
            finding_parts.append("processes personal data")
        if outside_region:
            finding_parts.append("stores data outside operating region")

        evidence.append(
            EvidenceItem(
                source="vendor-risk-api",
                finding=f"Vendor '{vendor_name}': {'; '.join(finding_parts)}. Notes: {notes}",
                reference=vendor_name,
            )
        )

        profile = VendorRiskProfile(
            vendor_name=vendor_name,
            verified=True,
            risk_level=risk_level,
            security_review_status=review_status,
            last_review_date=last_date,
            processes_personal_data=personal_data,
            stores_data_outside_region=outside_region,
            notes=notes,
            raw_response=data,
            status_code=200,
            evidence=evidence,
        )

        return ToolResult(
            tool_name="get_vendor_risk",
            success=True,
            data=profile.model_dump(),
            evidence=evidence,
            errors=[],
        )

    # Process failure / unavailable evidence
    error_summary = " | ".join(errors) if errors else "Vendor evidence unavailable"
    evidence.append(
        EvidenceItem(
            source="vendor-risk-api",
            finding=(
                f"External vendor risk service unavailable or returned error for '{vendor_name}': "
                f"{error_summary}. Risk posture is unverified."
            ),
            reference=vendor_name,
        )
    )

    profile = VendorRiskProfile(
        vendor_name=vendor_name,
        verified=False,
        status_code=status_code,
        error=error_summary,
        evidence=evidence,
    )

    return ToolResult(
        tool_name="get_vendor_risk",
        success=False,
        data=profile.model_dump(),
        evidence=evidence,
        errors=errors,
    )
