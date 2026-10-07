from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import warnings
warnings.filterwarnings("ignore")

from src.contracts import Architecture, ProcurementDecision
from src.solution import handle_request

# Configure logging to stderr so stdout remains clean for --json output
logging.basicConfig(
    stream=sys.stderr,
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger("copilot.cli")


def load_request_catalog() -> list[dict]:
    requests_path = ROOT / "data" / "requests.json"
    if requests_path.exists():
        return json.loads(requests_path.read_text(encoding="utf-8"))
    return []


def format_human_report(decision: ProcurementDecision, architecture: str) -> str:
    """Format a clean, professional human-readable terminal report."""
    border = "=" * 68
    divider = "-" * 68
    req_data = next((r for r in load_request_catalog() if r.get("request_id") == decision.request_id), {})
    product_str = req_data.get("product_name", "Unknown Product")
    vendor_str = req_data.get("vendor_name", "Unknown Vendor")

    # Extract summary narrative
    summary_text = getattr(decision, "summary", "") or "No executive summary available."

    approvals_str = "\n".join(f"  * {app}" for app in decision.required_approvals) if decision.required_approvals else "  * None (No departmental approvals triggered)"
    risks_str = "\n".join(f"  * {flag}" for flag in decision.risk_flags) if decision.risk_flags else "  * None (Low-risk baseline)"
    missing_str = "\n".join(f"  * {item}" for item in decision.missing_information) if decision.missing_information else "  * None (Request payload is complete)"

    evidence_lines = []
    for idx, ev in enumerate(decision.evidence[:5], 1):
        ref = f" ({ev.reference})" if ev.reference else ""
        evidence_lines.append(f"  [{idx}] {ev.source}{ref}: {ev.finding}")
    if len(decision.evidence) > 5:
        evidence_lines.append(f"  ... and {len(decision.evidence) - 5} additional evidence items.")
    evidence_str = "\n".join(evidence_lines) if evidence_lines else "  * No evidence recorded."

    tel = decision.telemetry
    tel_str = (
        f"LLM Calls: {tel.llm_calls if tel else 1} | "
        f"Tool Calls: {tel.tool_calls if tel else 5} | "
        f"Agents: {', '.join(tel.agent_names) if tel and tel.agent_names else 'single_agent'}"
    )

    return f"""{border}
AI PROCUREMENT REQUEST COPILOT — TRIAGE REPORT
{border}
Request ID:             {decision.request_id}
Product:                {product_str} (Vendor: {vendor_str})
Architecture:           {architecture} ({'Single-Agent Baseline' if architecture == 'single' else 'Staged Two-Agent Architecture'})

RECOMMENDATION:         {decision.recommendation}
HUMAN REVIEW REQUIRED:  {'YES (Mandatory Corporate Policy)' if decision.human_review_required else 'NO'}

{divider}
EXECUTIVE SUMMARY
{divider}
{summary_text}

{divider}
REQUIRED APPROVALS
{divider}
{approvals_str}

{divider}
RISK FLAGS
{divider}
{risks_str}

{divider}
MISSING INFORMATION
{divider}
{missing_str}

{divider}
NEXT ACTION
{divider}
{decision.next_step}

{divider}
VERIFIED EVIDENCE TRACE
{divider}
{evidence_str}

{divider}
TELEMETRY
{divider}
{tel_str}
{border}"""


def run_cli() -> int:
    parser = argparse.ArgumentParser(
        prog="python app.py",
        description="AI Procurement Request Copilot — Autonomous Intake & Decision Support CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python app.py --request-id REQ-1001
  python app.py --request-id REQ-1002 --architecture single
  python app.py --request-id REQ-1005 --architecture staged --json
  python app.py --list
  python app.py --ui
""",
    )
    parser.add_argument(
        "--request-id",
        type=str,
        help="Procurement request identifier (e.g. REQ-1001)",
    )
    parser.add_argument(
        "--architecture",
        type=str,
        choices=["single", "staged"],
        default="single",
        help="Agent architecture to execute: 'single' (Core Production MVP) or 'staged' (Two-Agent Escalation). Default: 'single'",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output machine-readable JSON to stdout (disables human report)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all available purchase request IDs and exit",
    )
    parser.add_argument(
        "--ui",
        action="store_true",
        help="Launch the interactive Streamlit web interface",
    )

    args = parser.parse_args()

    if args.list:
        requests = load_request_catalog()
        print(f"\nAvailable Purchase Requests ({len(requests)} total):\n")
        print(f"{'Request ID':<12} | {'Requester':<10} | {'Cost (USD)':<12} | {'Product Name':<30} | {'Vendor'}")
        print("-" * 80)
        for r in requests:
            cost_str = f"${r['annual_cost_usd']:,}" if r.get("annual_cost_usd") is not None else "Unspecified"
            print(f"{r['request_id']:<12} | {r.get('requester_id', ''):<10} | {cost_str:<12} | {r.get('product_name', ''):<30} | {r.get('vendor_name', '')}")
        print()
        return 0

    if args.ui:
        import subprocess
        logger.info("Launching Streamlit Web UI on port 8501...")
        cmd = [sys.executable, "-m", "streamlit", "run", str(ROOT / "app.py"), "--server.port", "8501"]
        return subprocess.call(cmd)

    if not args.request_id:
        parser.print_help(sys.stderr)
        return 1

    try:
        decision = handle_request(args.request_id, architecture=args.architecture)
    except KeyError as exc:
        logger.error(f"Request not found: {exc}")
        if args.json:
            print(json.dumps({"error": str(exc), "request_id": args.request_id}))
        else:
            print(f"\nError: Request '{args.request_id}' not found in requests database.\nRun 'python app.py --list' to view available IDs.\n", file=sys.stderr)
        return 1
    except Exception as exc:
        logger.error(f"Processing error: {exc}", exc_info=True)
        if args.json:
            print(json.dumps({"error": f"{type(exc).__name__}: {exc}", "request_id": args.request_id}))
        else:
            print(f"\nError processing request {args.request_id}: {exc}\n", file=sys.stderr)
        return 1

    if args.json:
        # Output clean machine-readable JSON to stdout
        payload = decision.model_dump(mode="json")
        print(json.dumps(payload, indent=2))
    else:
        # Output professional human report
        print(format_human_report(decision, architecture=args.architecture))

    return 0


def render_streamlit_ui() -> None:
    """Render interactive Streamlit UI for procurement copilot."""
    import streamlit as st

    st.set_page_config(
        page_title="AI Procurement Request Copilot",
        page_icon="🛡️",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    requests = load_request_catalog()
    by_id = {r["request_id"]: r for r in requests}

    # Custom styling for professional enterprise look
    st.markdown(
        """
        <style>
        .metric-card {
            background-color: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 14px 18px;
            margin-bottom: 12px;
        }
        .metric-label {
            font-size: 0.82rem;
            color: #64748b;
            text-transform: uppercase;
            font-weight: 600;
            letter-spacing: 0.05em;
        }
        .metric-value {
            font-size: 1.15rem;
            color: #0f172a;
            font-weight: 700;
            margin-top: 4px;
        }
        .badge-chip {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 16px;
            font-size: 0.85rem;
            font-weight: 600;
            margin-right: 6px;
            margin-bottom: 6px;
        }
        .badge-approver {
            background-color: #e0f2fe;
            color: #0369a1;
            border: 1px solid #bae6fd;
        }
        .badge-risk {
            background-color: #fee2e2;
            color: #b91c1c;
            border: 1px solid #fecaca;
        }
        .badge-missing {
            background-color: #fef3c7;
            color: #b45309;
            border: 1px solid #fde68a;
        }
        .evidence-box {
            background-color: #ffffff;
            border-left: 4px solid #3b82f6;
            border-top: 1px solid #e2e8f0;
            border-right: 1px solid #e2e8f0;
            border-bottom: 1px solid #e2e8f0;
            border-radius: 4px;
            padding: 10px 14px;
            margin-bottom: 8px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Header
    st.title("🛡️ AI Procurement Request Copilot")
    st.markdown(
        "**Autonomous Intake & Policy Triage** | "
        "*Deterministic Rule Authority · Grounded Evidence Trace · Mandatory Human Review*"
    )

    # Corporate Governance Invariant Notice
    st.info(
        "⚖️ **Corporate Governance Invariant:** Copilot assessments are strictly advisory. "
        "Autonomous purchasing is disabled by policy. Final procurement approval always requires authorized human sign-off."
    )

    # Sidebar Controls
    st.sidebar.header("📋 Intake Controls")
    request_id = st.sidebar.selectbox(
        "Select Purchase Request",
        list(by_id.keys()),
        format_func=lambda rid: f"{rid} — {by_id[rid].get('product_name', 'Unknown')}",
    )

    architecture = st.sidebar.radio(
        "Copilot Architecture",
        ["single", "staged"],
        index=0,
        format_func=lambda a: "Architecture A: Single-Agent (Core MVP)" if a == "single" else "Architecture B: Staged Two-Agent (Escalation)",
        help=(
            "Architecture A (Single): 1 LLM call, lower latency, recommended Core Production MVP.\n"
            "Architecture B (Staged): 2 LLM calls, specialized Intake + Governance dossiers."
        ),
    )

    auto_run = st.sidebar.checkbox("Auto-evaluate on selection", value=True)
    trigger_eval = st.sidebar.button("⚡ Evaluate Procurement Request", type="primary", use_container_width=True)

    req = by_id[request_id]

    # Load Employee mapping if available
    requester_name = req.get("requester_id", "Unknown")
    requester_dept = "Unknown Department"
    try:
        from src.data_access import load_employees
        emp_df = load_employees()
        emp_row = emp_df[emp_df["employee_id"] == req.get("requester_id")]
        if not emp_row.empty:
            requester_name = f"{emp_row.iloc[0]['name']} ({req.get('requester_id')})"
            requester_dept = f"{emp_row.iloc[0]['department']} — {emp_row.iloc[0]['role_level']}"
    except Exception:
        pass

    # SECTION 1: REQUEST DETAILS
    st.markdown("### 1. Inbound Procurement Request")
    r_col1, r_col2, r_col3, r_col4 = st.columns(4)
    with r_col1:
        st.markdown(
            f"""<div class="metric-card">
                <div class="metric-label">Requester & Dept</div>
                <div class="metric-value">{requester_name}</div>
                <div style="font-size: 0.8rem; color: #64748b;">{requester_dept}</div>
            </div>""",
            unsafe_allow_html=True,
        )
    with r_col2:
        cost_val = req.get("annual_cost_usd")
        cost_display = f"${cost_val:,.2f}" if cost_val is not None else "Unspecified"
        users_val = req.get("user_count", "N/A")
        st.markdown(
            f"""<div class="metric-card">
                <div class="metric-label">Annual Spend & Seats</div>
                <div class="metric-value">{cost_display}</div>
                <div style="font-size: 0.8rem; color: #64748b;">{users_val} seats requested</div>
            </div>""",
            unsafe_allow_html=True,
        )
    with r_col3:
        prod_val = req.get("product_name", "Unknown")
        vendor_val = req.get("vendor_name", "Unknown")
        st.markdown(
            f"""<div class="metric-card">
                <div class="metric-label">Product & Vendor</div>
                <div class="metric-value">{prod_val}</div>
                <div style="font-size: 0.8rem; color: #64748b;">Vendor: {vendor_val}</div>
            </div>""",
            unsafe_allow_html=True,
        )
    with r_col4:
        data_acc = req.get("data_access_level", "unspecified")
        category_val = req.get("category", "General")
        st.markdown(
            f"""<div class="metric-card">
                <div class="metric-label">Data Access & Category</div>
                <div class="metric-value">{data_acc}</div>
                <div style="font-size: 0.8rem; color: #64748b;">Category: {category_val}</div>
            </div>""",
            unsafe_allow_html=True,
        )

    # Justification Card
    st.markdown(
        f"""<div style="background-color: #f1f5f9; border-radius: 6px; padding: 10px 14px; margin-bottom: 20px;">
            <strong>Business Justification:</strong> {req.get('business_justification', 'None provided')}
        </div>""",
        unsafe_allow_html=True,
    )

    # Perform Evaluation
    if auto_run or trigger_eval:
        with st.spinner(f"Analyzing request {request_id} using Architecture: {architecture}..."):
            try:
                result = handle_request(request_id, architecture=architecture)
            except Exception as exc:
                st.error(f"Error evaluating request {request_id}: {exc}")
                return

        # SECTION 2 & 3: SPLIT VIEW (RECOMMENDATION & EVIDENCE)
        main_col1, main_col2 = st.columns([1.0, 1.0], gap="large")

        # MAIN COL 1: RECOMMENDATION & NEXT ACTIONS
        with main_col1:
            st.markdown("### 2. Copilot Recommendation & Action")

            # Status Banner
            rec = result.recommendation
            if rec == "PROCEED_TO_REVIEW":
                st.success(f"### 🟢 RECOMMENDATION: {rec}")
            elif rec == "MANUAL_REVIEW":
                st.warning(f"### 🟠 RECOMMENDATION: {rec}")
            else:
                st.error(f"### 🟡 RECOMMENDATION: {rec}")

            # Human Review Required Callout
            st.markdown(
                f"""<div style="background-color: #ecfdf5; border: 1px solid #a7f3d0; border-radius: 6px; padding: 8px 12px; margin-bottom: 12px;">
                    <strong style="color: #065f46;">Human Review Required:</strong> <code>{'YES (MANDATORY)' if result.human_review_required else 'NO'}</code>
                    <br/><span style="font-size: 0.82rem; color: #047857;">Autonomous purchases are forbidden. A designated human reviewer must approve.</span>
                </div>""",
                unsafe_allow_html=True,
            )

            # Executive Summary
            summary_val = getattr(result, "summary", "") or "No executive summary available."
            st.markdown("#### Executive Summary")
            st.markdown(f"> {summary_val}")

            # Required Approvals
            st.markdown("#### Required Approvals")
            if result.required_approvals:
                chips_html = "".join(f'<span class="badge-chip badge-approver">👤 {app}</span>' for app in result.required_approvals)
                st.markdown(chips_html, unsafe_allow_html=True)
            else:
                st.markdown("*(None — Standard employee discretionary threshold)*")

            # Risk Flags
            st.markdown("#### Identified Risk Flags")
            if result.risk_flags:
                risk_html = "".join(f'<span class="badge-chip badge-risk">⚠️ {rf}</span>' for rf in result.risk_flags)
                st.markdown(risk_html, unsafe_allow_html=True)
            else:
                st.markdown("*(None — Low-risk operational profile)*")

            # Missing Information
            st.markdown("#### Missing Information & Clarifications")
            if result.missing_information:
                miss_html = "".join(f'<span class="badge-chip badge-missing">❓ {mi}</span>' for mi in result.missing_information)
                st.markdown(miss_html, unsafe_allow_html=True)
            else:
                st.markdown("*(None — Request payload contains complete business context)*")

            # Next Step
            st.markdown("#### Recommended Next Step")
            st.info(f"👉 **{result.next_step}**")

            # Telemetry metrics
            st.markdown("#### Runtime Telemetry")
            tel = result.telemetry
            t_col1, t_col2, t_col3, t_col4 = st.columns(4)
            with t_col1:
                st.metric("LLM Calls", tel.llm_calls if tel else 1)
            with t_col2:
                st.metric("Tool Calls", tel.tool_calls if tel else 5)
            with t_col3:
                st.metric("Duration", f"{tel.duration_ms:.1f} ms" if tel else "N/A")
            with t_col4:
                st.metric("Architecture", architecture)

        # MAIN COL 2: EVIDENCE PANEL
        with main_col2:
            st.markdown("### 3. Verified Evidence Panel")
            st.caption("Visual audit trail connecting deterministic ground truth to policy recommendation.")

            # Filter evidence by categories
            ev_context = [e for e in result.evidence if "requests.json" in e.source or "employees.csv" in e.source or "department_budgets" in e.source]
            ev_catalog = [e for e in result.evidence if "software_catalog" in e.source]
            ev_vendor = [e for e in result.evidence if "vendor" in e.source.lower()]
            ev_policy = [e for e in result.evidence if "policy" in e.source.lower() or "rules" in e.source.lower()]
            ev_other = [e for e in result.evidence if e not in ev_context + ev_catalog + ev_vendor + ev_policy]

            tab1, tab2, tab3, tab4, tab5 = st.tabs([
                "💰 Budget & Context",
                "📦 Software Catalog",
                "🔍 Vendor Security",
                "📜 Procurement Policy",
                "📋 Complete Trace",
            ])

            with tab1:
                st.markdown("**Department Budget & Request Context:**")
                if ev_context:
                    for e in ev_context:
                        ref_str = f" `[{e.reference}]`" if e.reference else ""
                        st.markdown(
                            f"""<div class="evidence-box">
                                <strong>Source:</strong> <code>{e.source}</code>{ref_str}<br/>
                                <span style="font-size: 0.9rem; color: #1e293b;">{e.finding}</span>
                            </div>""",
                            unsafe_allow_html=True,
                        )
                else:
                    st.write("No specific budget context findings.")

            with tab2:
                st.markdown("**Existing Software Catalog Overlap Analysis:**")
                if ev_catalog:
                    for e in ev_catalog:
                        ref_str = f" `[{e.reference}]`" if e.reference else ""
                        st.markdown(
                            f"""<div class="evidence-box">
                                <strong>Source:</strong> <code>{e.source}</code>{ref_str}<br/>
                                <span style="font-size: 0.9rem; color: #1e293b;">{e.finding}</span>
                            </div>""",
                            unsafe_allow_html=True,
                        )
                else:
                    st.write("No software catalog items triggered.")

            with tab3:
                st.markdown("**Vendor Security & Risk Posture:**")
                if ev_vendor:
                    for e in ev_vendor:
                        ref_str = f" `[{e.reference}]`" if e.reference else ""
                        st.markdown(
                            f"""<div class="evidence-box">
                                <strong>Source:</strong> <code>{e.source}</code>{ref_str}<br/>
                                <span style="font-size: 0.9rem; color: #1e293b;">{e.finding}</span>
                            </div>""",
                            unsafe_allow_html=True,
                        )
                else:
                    st.write("No vendor risk findings recorded.")

            with tab4:
                st.markdown("**Policy Rules & Spend Governance:**")
                if ev_policy:
                    for e in ev_policy:
                        ref_str = f" `[{e.reference}]`" if e.reference else ""
                        st.markdown(
                            f"""<div class="evidence-box">
                                <strong>Source:</strong> <code>{e.source}</code>{ref_str}<br/>
                                <span style="font-size: 0.9rem; color: #1e293b;">{e.finding}</span>
                            </div>""",
                            unsafe_allow_html=True,
                        )
                else:
                    st.write("Standard discretionary tier applied.")

            with tab5:
                st.markdown("**Full Ordered Evidence Sequence:**")
                for idx, e in enumerate(result.evidence, 1):
                    ref_str = f" ({e.reference})" if e.reference else ""
                    st.markdown(f"**[{idx}] {e.source}{ref_str}**")
                    st.markdown(f"- {e.finding}")

            # Structured JSON Inspector
            with st.expander("🔍 Inspect Full Machine-Readable Decision JSON"):
                st.json(result.model_dump(mode="json"))
    else:
        st.info("Select a request and click '⚡ Evaluate Procurement Request' (or check 'Auto-evaluate on selection').")

    st.divider()
    st.caption("AI Procurement Request Copilot · Production MVP Deliverable · FDE Assessment 3")



# Determine runtime entry point
def _is_running_in_streamlit() -> bool:
    if any(s in sys.argv[0] for s in ("streamlit", "streamlit.exe")):
        return True
    return False


if __name__ == "__main__":
    if _is_running_in_streamlit():
        render_streamlit_ui()
    else:
        sys.exit(run_cli())
else:
    # When Streamlit executes the file via exec / run, it may not be __main__ or may be imported
    if _is_running_in_streamlit():
        render_streamlit_ui()
