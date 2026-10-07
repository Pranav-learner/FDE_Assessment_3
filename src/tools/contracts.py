from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field

from src.contracts import EvidenceItem


class ToolResult(BaseModel):
    """Standardized result envelope returned by all tools."""
    tool_name: str
    success: bool
    data: Any = None
    evidence: list[EvidenceItem] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class RequestContext(BaseModel):
    request: dict[str, Any]
    requester: dict[str, Any]
    department: str
    manager: dict[str, Any] | None
    budget: dict[str, Any]
    evidence: list[EvidenceItem] = Field(default_factory=list)


class CatalogSearchResult(BaseModel):
    exact_matches: list[dict[str, Any]] = Field(default_factory=list)
    vendor_matches: list[dict[str, Any]] = Field(default_factory=list)
    category_matches: list[dict[str, Any]] = Field(default_factory=list)
    potential_alternatives: list[dict[str, Any]] = Field(default_factory=list)
    has_overlap: bool = False
    evidence: list[EvidenceItem] = Field(default_factory=list)


class VendorRiskProfile(BaseModel):
    vendor_name: str
    verified: bool = False
    risk_level: str | None = None
    security_review_status: str | None = None
    last_review_date: str | None = None
    processes_personal_data: bool | None = None
    stores_data_outside_region: bool | None = None
    notes: str | None = None
    raw_response: dict[str, Any] | None = None
    status_code: int | None = None
    error: str | None = None
    evidence: list[EvidenceItem] = Field(default_factory=list)


class PolicySection(BaseModel):
    section_number: int
    title: str
    content: str


class PolicyMetadata(BaseModel):
    version: str
    reference_date: str
    sections: list[PolicySection] = Field(default_factory=list)
    raw_policy: str


class RuleEvaluationResult(BaseModel):
    request_id: str
    is_valid: bool
    missing_information: list[str] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)
    required_approvals: list[str] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    human_review_required: bool = True
    preliminary_recommendation: str
    next_step: str
