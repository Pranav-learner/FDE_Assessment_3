from __future__ import annotations

import re
from src.contracts import EvidenceItem
from src.data_access import load_policy_text
from src.tools.contracts import PolicyMetadata, PolicySection, ToolResult


def get_procurement_policy() -> ToolResult:
    """Retrieve the authoritative procurement policy text and structured sections.

    Source of truth: data/procurement_policy.md
    Reference Date: 2026-09-30
    Policy Version: 2026.09
    """
    evidence: list[EvidenceItem] = []
    errors: list[str] = []

    try:
        raw_text = load_policy_text()
    except Exception as exc:
        return ToolResult(
            tool_name="get_procurement_policy",
            success=False,
            data=None,
            evidence=[],
            errors=[f"Failed to load procurement policy: {exc}"],
        )

    # Extract version and reference date from header
    version_match = re.search(r"\*\*Policy version:\*\*\s*([^\n\r]+)", raw_text)
    date_match = re.search(r"\*\*Data snapshot / evaluation reference date:\*\*\s*([^\n\r]+)", raw_text)

    version = version_match.group(1).strip() if version_match else "2026.09"
    reference_date = date_match.group(1).strip() if date_match else "2026-09-30"

    # Parse sections
    sections: list[PolicySection] = []
    section_pattern = re.compile(r"^##\s+(\d+)\.\s+([^\n\r]+)\n(.*?)(?=\n##\s+\d+\.|\Z)", re.MULTILINE | re.DOTALL)

    for match in section_pattern.finditer(raw_text):
        sec_num = int(match.group(1))
        sec_title = match.group(2).strip()
        sec_content = match.group(3).strip()
        sections.append(
            PolicySection(
                section_number=sec_num,
                title=sec_title,
                content=sec_content,
            )
        )

    evidence.append(
        EvidenceItem(
            source="procurement_policy.md",
            finding=f"Loaded authoritative Procurement Policy version {version} (evaluation reference date: {reference_date}) with {len(sections)} governance sections.",
            reference=f"Version {version}",
        )
    )

    metadata = PolicyMetadata(
        version=version,
        reference_date=reference_date,
        sections=sections,
        raw_policy=raw_text,
    )

    return ToolResult(
        tool_name="get_procurement_policy",
        success=True,
        data=metadata.model_dump(),
        evidence=evidence,
        errors=errors,
    )
