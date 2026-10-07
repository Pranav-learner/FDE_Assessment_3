from __future__ import annotations

from typing import Any
from src.contracts import EvidenceItem
from src.data_access import get_request, load_budgets, load_employees
from src.tools.contracts import RequestContext, ToolResult


def get_request_context(request_id: str) -> ToolResult:
    """Retrieve full organizational, departmental, and budgetary context for a request.

    Queries:
    - requests.json (request details)
    - employees.csv (requester profile, manager, country)
    - department_budgets.csv (annual budget, committed spend, available budget)

    Returns a ToolResult wrapping RequestContext with structured evidence items.
    """
    evidence: list[EvidenceItem] = []
    errors: list[str] = []

    # 1. Fetch Request
    try:
        request_data = get_request(request_id)
    except KeyError:
        return ToolResult(
            tool_name="get_request_context",
            success=False,
            data=None,
            evidence=[],
            errors=[f"Unknown request_id: '{request_id}'"],
        )
    except Exception as exc:
        return ToolResult(
            tool_name="get_request_context",
            success=False,
            data=None,
            evidence=[],
            errors=[f"Error loading request '{request_id}': {exc}"],
        )

    requester_id = request_data.get("requester_id")
    annual_cost = request_data.get("annual_cost_usd")
    cost_str = f"${annual_cost:,.2f}" if annual_cost is not None else "unspecified"
    user_count = request_data.get("user_count")
    user_str = str(user_count) if user_count is not None else "unspecified"

    evidence.append(
        EvidenceItem(
            source="requests.json",
            finding=(
                f"Request {request_id} for '{request_data.get('product_name')}' "
                f"from vendor '{request_data.get('vendor_name')}' (category: {request_data.get('category')}) "
                f"specifies annual cost {cost_str} for {user_str} seats."
            ),
            reference=request_id,
        )
    )

    # 2. Fetch Requester & Manager from employees.csv
    requester: dict[str, Any] | None = None
    manager: dict[str, Any] | None = None
    department: str = "Unknown"

    try:
        employees_df = load_employees()
        employee_rows = employees_df[employees_df["employee_id"] == requester_id]

        if not employee_rows.empty:
            requester = employee_rows.iloc[0].to_dict()
            department = str(requester.get("department", "Unknown"))
            manager_id = requester.get("manager_id")

            if manager_id and not (isinstance(manager_id, float) and str(manager_id) == "nan"):
                manager_rows = employees_df[employees_df["employee_id"] == str(manager_id)]
                if not manager_rows.empty:
                    manager = manager_rows.iloc[0].to_dict()

            manager_desc = f"{manager.get('name')} ({manager.get('employee_id')})" if manager else "None (Executive)"
            evidence.append(
                EvidenceItem(
                    source="employees.csv",
                    finding=(
                        f"Requester {requester.get('name')} ({requester_id}) is level {requester.get('level')} "
                        f"in {department} ({requester.get('country')}), reporting to {manager_desc}."
                    ),
                    reference=requester_id,
                )
            )
        else:
            errors.append(f"Requester '{requester_id}' not found in employees.csv")
    except Exception as exc:
        errors.append(f"Failed to query employee directory: {exc}")

    # 3. Fetch Department Budget from department_budgets.csv
    budget_data: dict[str, Any] = {
        "department": department,
        "annual_software_budget_usd": 0,
        "committed_usd": 0,
        "available_usd": 0,
    }

    try:
        budgets_df = load_budgets()
        dept_budget_rows = budgets_df[budgets_df["department"] == department]

        if not dept_budget_rows.empty:
            row = dept_budget_rows.iloc[0]
            annual_budget = int(row["annual_software_budget_usd"])
            committed = int(row["committed_usd"])
            # Strictly calculate available_budget = annual_software_budget_usd - committed_usd
            available = annual_budget - committed

            budget_data = {
                "department": department,
                "annual_software_budget_usd": annual_budget,
                "committed_usd": committed,
                "available_usd": available,
            }

            evidence.append(
                EvidenceItem(
                    source="department_budgets.csv",
                    finding=(
                        f"Department '{department}' software budget: ${available:,} available "
                        f"(${annual_budget:,} annual budget - ${committed:,} committed)."
                    ),
                    reference=department,
                )
            )
        else:
            errors.append(f"Department '{department}' not found in department_budgets.csv")
    except Exception as exc:
        errors.append(f"Failed to query department budgets: {exc}")

    context = RequestContext(
        request=request_data,
        requester=requester or {},
        department=department,
        manager=manager,
        budget=budget_data,
        evidence=evidence,
    )

    return ToolResult(
        tool_name="get_request_context",
        success=len(errors) == 0,
        data=context.model_dump(),
        evidence=evidence,
        errors=errors,
    )
