# 11. Tool Contracts & Interfaces: AI Procurement Request Copilot

**Document Version:** 1.0.0  
**Phase:** Phase 2 (Data Foundation & Tool Contracts)  
**Author:** Forward Deployed Engineering (FDE)

---

## 1. Overview & Universal Tool Result Envelope

All tools in the procurement copilot package (`src/tools/`) adhere to a standardized result envelope: `ToolResult`. This ensures uniform error handling, telemetry, and evidence accumulation across both deterministic scripts and future AI agent workflows.

```python
class ToolResult(BaseModel):
    tool_name: str
    success: bool
    data: Any = None
    evidence: list[EvidenceItem] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
```

---

## 2. Tool 1: `get_request_context`

### 2.1 Purpose & Scope
Gathers the complete operational context for an incoming purchase request by joining the request record with employee organizational hierarchy, reporting line, and departmental software budget.

### 2.2 Input Schema
```python
def get_request_context(request_id: str) -> ToolResult:
```
* **`request_id` (str):** The unique identifier of the request (e.g., `"REQ-1001"`).

### 2.3 Output Data Schema (`RequestContext`)
```python
class RequestContext(BaseModel):
    request: dict[str, Any]
    requester: dict[str, Any]
    department: str
    manager: dict[str, Any] | None
    budget: dict[str, Any]  # annual_software_budget_usd, committed_usd, available_usd
    evidence: list[EvidenceItem]
```

### 2.4 Budget Arithmetic Formula
$$\text{available\_usd} = \text{annual\_software\_budget\_usd} - \text{committed\_usd}$$

### 2.5 Failure & Edge Behavior
* If `request_id` is not found, returns `success=False` with error `"Unknown request_id: '...'"` and `data=None`.
* If requester has no manager (e.g. VP level), `manager` is returned as `None` without crashing.
* Never invents missing values for null fields.

---

## 3. Tool 2: `search_software_catalog`

### 3.1 Purpose & Scope
Searches the corporate software catalog (`software_catalog.csv`) to identify existing tools that overlap with the requested product by exact name, vendor, category, or functional capabilities.

### 3.2 Input Schema
```python
def search_software_catalog(
    product_name: str | None = None,
    vendor_name: str | None = None,
    category: str | None = None,
    query: str | None = None,
) -> ToolResult:
```

### 3.3 Output Data Schema (`CatalogSearchResult`)
```python
class CatalogSearchResult(BaseModel):
    exact_matches: list[dict[str, Any]]
    vendor_matches: list[dict[str, Any]]
    category_matches: list[dict[str, Any]]
    potential_alternatives: list[dict[str, Any]]
    has_overlap: bool
    evidence: list[EvidenceItem]
```

### 3.4 Governance Rule
* Overlap is **not an automatic rejection**. The tool generates factual evidence; downstream policy reasoning evaluates whether the requested tool fills a credible gap.

---

## 4. Tool 3: `get_vendor_risk`

### 4.1 Purpose & Scope
Queries the third-party Vendor Risk REST service via `src/vendor_client.py` to retrieve verified security and privacy risk intelligence.

### 4.2 Input Schema
```python
def get_vendor_risk(
    vendor_name: str,
    timeout_seconds: float = 3.0,
    simulate_failure: str | None = None,
) -> ToolResult:
```

### 4.3 Output Data Schema (`VendorRiskProfile`)
```python
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
    evidence: list[EvidenceItem]
```

### 4.4 Failure & Degradation Behavior
* **200 OK:** Returns `verified=True`, `success=True`.
* **404 Not Found:** Returns `verified=False`, `success=False`, `status_code=404`.
* **503 Forced Outage:** Returns `verified=False`, `success=False`, `status_code=503`.
* **Timeout / Connection Failure:** Returns `verified=False`, `success=False`.
* **Golden Rule:** Never converts unavailable evidence into a favorable result. Evidence explicitly states risk posture is unverified.

---

## 5. Tool 4: `get_procurement_policy`

### 5.1 Purpose & Scope
Loads the authoritative procurement policy (`data/procurement_policy.md`), extracts metadata (version `2026.09`, reference date `2026-09-30`), and parses all eleven governance sections.

### 5.2 Input Schema
```python
def get_procurement_policy() -> ToolResult:
```

### 5.3 Output Data Schema (`PolicyMetadata`)
```python
class PolicyMetadata(BaseModel):
    version: str
    reference_date: str
    sections: list[PolicySection]  # section_number, title, content
    raw_policy: str
```

---

## 6. Tool 5: `evaluate_procurement_rules`

### 6.1 Purpose & Scope
The deterministic policy engine. Evaluates all hard procurement rules, calculations, and governance triggers without calling an LLM.

### 6.2 Input Schema
```python
def evaluate_procurement_rules(
    context: RequestContext | dict[str, Any],
    catalog_result: CatalogSearchResult | ToolResult | dict[str, Any] | None = None,
    vendor_risk: VendorRiskProfile | ToolResult | dict[str, Any] | None = None,
    vendor_registry_record: dict[str, Any] | None = None,
) -> RuleEvaluationResult:
```

### 6.3 Output Data Schema (`RuleEvaluationResult`)
```python
class RuleEvaluationResult(BaseModel):
    request_id: str
    is_valid: bool
    missing_information: list[str]
    risk_flags: list[str]
    required_approvals: list[str]
    evidence: list[EvidenceItem]
    human_review_required: bool = True
    preliminary_recommendation: str
    next_step: str
```

### 6.4 Human Authority Guardrail
`human_review_required` unconditionally evaluates to `True` on every single execution. The deterministic engine never approves or executes purchases.
