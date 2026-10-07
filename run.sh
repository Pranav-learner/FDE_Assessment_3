#!/usr/bin/env bash
# ==============================================================================
# FDE Assessment 3: AI Procurement Request Copilot — One-Command Start Script
# ==============================================================================
# Usage:
#   ./run.sh              # Start Mock API (8001) and Streamlit Web UI (8501)
#   ./run.sh --cli REQ-1001  # Run CLI evaluation for a specific request ID
#   ./run.sh --test       # Run entire regression test suite (136 tests)
#   ./run.sh --eval       # Run public evaluations and comparative benchmark
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

echo "======================================================================"
echo "AI PROCUREMENT REQUEST COPILOT — STARTING ENVIRONMENT"
echo "======================================================================"

# 1. Environment configuration
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        echo "Creating .env from .env.example with safe offline defaults..."
        cp .env.example .env
    else
        echo "Warning: .env.example not found. Proceeding with default environment."
    fi
fi

# 2. Virtual Environment Detection / Setup
PYTHON_BIN=""
if [ -d ".venv" ] && [ -f ".venv/bin/python" ]; then
    PYTHON_BIN=".venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
else
    echo "Error: Python 3 is required but was not found in PATH." >&2
    exit 1
fi

# Check Python version >= 3.10
PY_VER=$("${PYTHON_BIN}" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "Using Python binary: ${PYTHON_BIN} (version ${PY_VER})"

# If not in a venv and .venv doesn't exist, create it
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment at .venv..."
    "${PYTHON_BIN}" -m venv .venv
    PYTHON_BIN=".venv/bin/python"
    echo "Installing required dependencies..."
    "${PYTHON_BIN}" -m pip install --quiet --upgrade pip
    "${PYTHON_BIN}" -m pip install --quiet -r requirements.txt
fi

# 3. Optional Command Flags
if [ "${1:-}" = "--cli" ]; then
    shift
    echo "Executing CLI Copilot with arguments: $*"
    exec "${PYTHON_BIN}" app.py "$@"
elif [ "${1:-}" = "--test" ]; then
    echo "Running complete test suite..."
    exec "${PYTHON_BIN}" -m unittest discover tests -v
elif [ "${1:-}" = "--eval" ]; then
    echo "Running evaluation suite..."
    "${PYTHON_BIN}" evals/run_public_evals.py --architecture single
    "${PYTHON_BIN}" evals/run_public_evals.py --architecture staged
    exec "${PYTHON_BIN}" evals/run_comparison.py
fi

# 4. Launch Full Stack (Mock API on 8001 + Streamlit UI on 8501)
echo "Starting local procurement stack..."
echo "  * Vendor-Risk API:  http://127.0.0.1:8001"
echo "  * Procurement UI:   http://127.0.0.1:8501"
echo "Press Ctrl+C to terminate all services."
echo "======================================================================"

exec "${PYTHON_BIN}" run_local.py
