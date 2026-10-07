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
    """Render interactive Streamlit UI when executed via streamlit run."""
    import streamlit as st

    requests = load_request_catalog()
    by_id = {r["request_id"]: r for r in requests}

    st.set_page_config(page_title="AI Procurement Request Copilot", layout="wide")
    st.title("AI Procurement Request Copilot")
    st.caption("FDE Production Decision Support Platform | Human Authority Always Preserved")

    st.sidebar.header("Triage Controls")
    request_id = st.sidebar.selectbox(
        "Select Purchase Request",
        list(by_id.keys()),
        format_func=lambda rid: f"{rid} — {by_id[rid].get('product_name', 'Unknown')}",
    )
    architecture = st.sidebar.radio(
        "Copilot Architecture",
        ["single", "staged"],
        index=0,
        help="'single': Architecture A (Core Production MVP)\n'staged': Architecture B (Staged Two-Agent Escalation)",
        horizontal=True,
    )

    req = by_id[request_id]

    col1, col2 = st.columns([1.1, 0.9], gap="large")
    with col1:
        st.subheader("Inbound Request Details")
        st.json(req)

    with col2:
        st.subheader("Copilot Assessment")
        if st.button("Evaluate Procurement Policy", type="primary", use_container_width=True):
            with st.spinner(f"Evaluating request under Architecture: {architecture}..."):
                try:
                    result = handle_request(request_id, architecture=architecture)
                    st.success(f"Recommendation: {result.recommendation}")
                    st.markdown(f"**Human Review Required:** `{'YES' if result.human_review_required else 'NO'}`")
                    st.markdown(f"**Required Approvers:** {', '.join(result.required_approvals) if result.required_approvals else 'None'}")
                    if result.risk_flags:
                        st.warning(f"**Risk Flags:** {', '.join(result.risk_flags)}")
                    if result.missing_information:
                        st.error(f"**Missing Information:** {', '.join(result.missing_information)}")

                    summary_val = getattr(result, "summary", "")
                    if summary_val:
                        st.info(summary_val)

                    st.markdown(f"**Next Action:** {result.next_step}")
                    with st.expander("Full Structured Output & Evidence"):
                        st.json(result.model_dump(mode="json"))
                except Exception as exc:
                    st.error(f"Evaluation error: {exc}")
        else:
            st.info("Click 'Evaluate Procurement Policy' to trigger deterministic policy checks and copilot triage.")

    st.divider()
    st.caption("Notice: Copilot recommendations are strictly advisory. Final approval authority resides with human reviewers.")


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
