# 32. Production Deployment & Operations Runbook

## 1. Quick Start Operations

### 1.1 Local Python Deployment

#### Prerequisites:
- Python 3.10+ (Python 3.11 recommended)
- Virtual environment (`venv`)

#### Step-by-Step Setup:
```bash
# 1. Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 3. Verify pre-flight environment
python verify_setup.py

# 4. Start local services (FastAPI vendor-risk API + Streamlit Web UI)
python run_local.py
```

- **Mock Vendor API:** `http://127.0.0.1:8001`
- **Streamlit Web UI:** `http://127.0.0.1:8501`

---

### 1.2 Docker Container Deployment

#### Build and Run:
```bash
# 1. Build the production Docker image
docker build -t fde-procurement-copilot:latest .

# 2. Run the container as non-root user
docker run -d \
  --name fde-procurement \
  -p 8001:8001 \
  -p 8501:8501 \
  fde-procurement-copilot:latest

# 3. Verify container health
curl -s http://127.0.0.1:8001/health
# Response: {"status":"ok"}

# 4. Stop the container
docker stop fde-procurement && docker rm fde-procurement
```

#### Docker Compose Orchestration:
```bash
# Start all services (API + UI) in detached mode
docker compose up -d

# Check service status and health
docker compose ps

# View unified service logs
docker compose logs -f

# Teardown services
docker compose down
```

---

## 2. Environment Variables & Configuration

Configure via `.env` file or container environment variables:

| Variable | Default Value | Description |
|:---|:---|:---|
| `VENDOR_RISK_BASE_URL` | `http://127.0.0.1:8001` | Upstream vendor risk assessment endpoint |
| `LLM_MODE` | `mock` | `mock` (offline deterministic) or `live` (cloud API) |
| `DEFAULT_ARCHITECTURE` | `single` | Default architecture (`single` or `staged`) |
| `LLM_TIMEOUT_SECONDS` | `15.0` | Maximum network timeout for LLM generation |
| `VENDOR_API_TIMEOUT_SECONDS` | `5.0` | Network timeout for vendor risk HTTP calls |
| `OPENAI_API_KEY` | *(None)* | Required only when `LLM_MODE=live` and using OpenAI |
| `ANTHROPIC_API_KEY` | *(None)* | Required only when `LLM_MODE=live` and using Anthropic |
| `GOOGLE_API_KEY` | *(None)* | Required only when `LLM_MODE=live` and using Gemini |

---

## 3. Health Checks & Readiness Probes

### Liveness Probe (`GET /health`):
- Verifies that the FastAPI process is responsive.
- Does **not** depend on external LLM availability.
- Command: `curl -f http://127.0.0.1:8001/health`
- Expected: `{"status": "ok"}` (HTTP 200)

### Readiness Probe (`GET /ready`):
- Verifies that all mandatory corporate data files (`requests.json`, `software_catalog.csv`, `vendors.csv`, `vendor_risk.json`, `department_budgets.csv`, `employees.csv`, `procurement_policy.md`) exist on disk.
- Command: `curl -f http://127.0.0.1:8001/ready`
- Expected: `{"status": "ready", "assets_loaded": 7, "default_architecture": "single"}` (HTTP 200)

---

## 4. CLI Execution & Batch Commands

```bash
# Standard evaluation (Core Production MVP - Architecture A)
python app.py --request-id REQ-1001

# Escalation evaluation (Staged Two-Agent - Architecture B)
python app.py --request-id REQ-1005 --architecture staged

# Machine-readable JSON output (for automated CI/CD or ticketing pipelines)
python app.py --request-id REQ-1002 --json

# List all available requests
python app.py --list
```

---

## 5. Troubleshooting & Common Failures

### 1. Port 8001 / 8501 Already in Use
- **Symptom:** `OSError: [Errno 98] Address already in use`
- **Remedy:** Check for existing processes:
  ```bash
  lsof -i :8001
  kill -9 <PID>
  ```

### 2. Missing Corporate Data Asset
- **Symptom:** `/ready` returns HTTP 503 `Missing required data assets`
- **Remedy:** Verify that `data/` directory is mounted and contains all required CSV and JSON files.

### 3. Upstream Vendor Risk API Timeout
- **Symptom:** `vendor_risk_unavailable` flag present in decision output.
- **Remedy:** Ensure mock API is running on port 8001. If testing intentional resilience (e.g., REQ-1009), this is expected behavior and routes safely to Security/Legal.

---

## 6. Rollback Procedure

If a deployed revision introduces unexpected regression:
1. Revert Git repository to previous verified commit:
   ```bash
   git checkout <PREVIOUS_STABLE_COMMIT>
   ```
2. Re-run verification suite:
   ```bash
   python verify_setup.py && python -m unittest discover tests -v
   ```
3. Re-build and restart Docker container:
   ```bash
   docker compose down
   docker compose build --no-cache
   docker compose up -d
   ```
