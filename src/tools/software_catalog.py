from __future__ import annotations

import re
from typing import Any
from src.contracts import EvidenceItem
from src.data_access import load_software_catalog
from src.tools.contracts import CatalogSearchResult, ToolResult


def _normalize(text: str | None) -> str:
    if not text:
        return ""
    return re.sub(r"[^\w\s]", "", str(text)).strip().lower()


def search_software_catalog(
    product_name: str | None = None,
    vendor_name: str | None = None,
    category: str | None = None,
    query: str | None = None,
) -> ToolResult:
    """Search the approved corporate software catalog for overlapping or alternative tools.

    Matches by:
    - exact product name (or normalized equivalent)
    - vendor name (same vendor)
    - category (same functional software category)
    - use-case relevance / general query

    Returns structured matches without rejecting requests automatically.
    """
    evidence: list[EvidenceItem] = []
    errors: list[str] = []

    try:
        catalog_df = load_software_catalog()
    except Exception as exc:
        return ToolResult(
            tool_name="search_software_catalog",
            success=False,
            data=None,
            evidence=[],
            errors=[f"Failed to load software catalog: {exc}"],
        )

    norm_product = _normalize(product_name)
    norm_vendor = _normalize(vendor_name)
    norm_category = _normalize(category)
    norm_query = _normalize(query)

    exact_matches: list[dict[str, Any]] = []
    vendor_matches: list[dict[str, Any]] = []
    category_matches: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    potential_alternatives: list[dict[str, Any]] = []

    for _, row in catalog_df.iterrows():
        item = row.to_dict()
        sw_id = str(item.get("software_id", ""))
        item_product = _normalize(item.get("product_name"))
        item_vendor = _normalize(item.get("vendor_name"))
        item_cat = _normalize(item.get("category"))
        item_notes = _normalize(item.get("notes"))

        is_exact = False
        is_vendor = False
        is_category = False
        is_alt = False

        # Exact / strong product match
        if norm_product and (norm_product == item_product or norm_product in item_product or item_product in norm_product):
            exact_matches.append(item)
            is_exact = True

        # Vendor match
        if norm_vendor and (norm_vendor == item_vendor or norm_vendor in item_vendor or item_vendor in norm_vendor):
            vendor_matches.append(item)
            is_vendor = True

        # Category match
        if norm_category and (norm_category == item_cat or norm_category in item_cat or item_cat in norm_category):
            category_matches.append(item)
            is_category = True

        # Generic query / use-case match
        if norm_query and (norm_query in item_product or norm_query in item_cat or norm_query in item_notes):
            is_alt = True

        if (is_exact or is_vendor or is_category or is_alt) and sw_id not in seen_ids:
            seen_ids.add(sw_id)
            potential_alternatives.append(item)

    has_overlap = bool(exact_matches or vendor_matches or category_matches or potential_alternatives)

    # Generate structured evidence for key findings
    if exact_matches:
        for m in exact_matches:
            evidence.append(
                EvidenceItem(
                    source="software_catalog.csv",
                    finding=(
                        f"Exact/similar product match in catalog: '{m.get('product_name')}' "
                        f"(ID: {m.get('software_id')}, vendor: {m.get('vendor_name')}, status: {m.get('status')}) "
                        f"has {m.get('licensed_seats')} licensed seats with scope '{m.get('scope')}'."
                    ),
                    reference=str(m.get("software_id")),
                )
            )

    if vendor_matches and not exact_matches:
        for m in vendor_matches:
            evidence.append(
                EvidenceItem(
                    source="software_catalog.csv",
                    finding=(
                        f"Catalog includes existing product '{m.get('product_name')}' ({m.get('software_id')}) "
                        f"from the same vendor '{m.get('vendor_name')}' (scope: '{m.get('scope')}')."
                    ),
                    reference=str(m.get("software_id")),
                )
            )

    if category_matches and not exact_matches:
        for m in category_matches:
            evidence.append(
                EvidenceItem(
                    source="software_catalog.csv",
                    finding=(
                        f"Catalog contains existing approved alternative in category '{m.get('category')}': "
                        f"'{m.get('product_name')}' ({m.get('software_id')}, vendor: {m.get('vendor_name')}, "
                        f"{m.get('licensed_seats')} seats, scope: '{m.get('scope')}')."
                    ),
                    reference=str(m.get("software_id")),
                )
            )

    if not has_overlap:
        evidence.append(
            EvidenceItem(
                source="software_catalog.csv",
                finding="No overlapping or duplicate software products found in the active catalog.",
                reference="software_catalog.csv",
            )
        )

    result_data = CatalogSearchResult(
        exact_matches=exact_matches,
        vendor_matches=vendor_matches,
        category_matches=category_matches,
        potential_alternatives=potential_alternatives,
        has_overlap=has_overlap,
        evidence=evidence,
    )

    return ToolResult(
        tool_name="search_software_catalog",
        success=True,
        data=result_data.model_dump(),
        evidence=evidence,
        errors=errors,
    )
