import json
import subprocess
import sys
from typing import Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.platform.api.security import require_platform_admin
from app.platform.persistence.database import get_platform_db
from app.platform.security.rate_limit import PLATFORM_API_RATE_LIMIT, limiter
from app.platform.persistence.models import (
    PlatformGenerationRun,
    PlatformProject,
    PlatformTenant,
    PlatformWorkspace,
)


router = APIRouter(prefix="/platform", tags=["platform"])


MAX_LIST_LIMIT = 100
COMMAND_TIMEOUT_SECONDS = 300


REPAIR_DASHBOARD_HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>AI Software Factory Repair Dashboard</title>
  <style>
    body { margin: 0; font-family: Arial, sans-serif; background: #f6f7fb; color: #172033; }
    header { background: #172033; color: white; padding: 24px 32px; }
    main { max-width: 1100px; margin: 24px auto; padding: 0 20px 40px; }
    .card { background: white; border: 1px solid #dde2ee; border-radius: 12px; padding: 20px; margin-bottom: 18px; box-shadow: 0 2px 8px rgba(20, 30, 50, 0.06); }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 14px; }
    .metric { border: 1px solid #e3e7f0; border-radius: 10px; padding: 16px; background: #fbfcff; min-width: 0; }
    .metric-label { color: #667085; font-size: 13px; margin-bottom: 8px; }
    .metric-value { font-size: 22px; font-weight: 700; overflow-wrap: anywhere; word-break: break-word; line-height: 1.25; }
    .small-value { font-size: 15px; }
    .ok { color: #16794c; }
    .bad { color: #b42318; }
    .warn { color: #b54708; }
    input { width: 100%; box-sizing: border-box; padding: 12px; border: 1px solid #cbd5e1; border-radius: 8px; font-size: 14px; margin-top: 8px; }
    button { border: 0; background: #2563eb; color: white; border-radius: 8px; padding: 11px 14px; font-weight: 700; cursor: pointer; margin-right: 8px; margin-top: 12px; }
    button.secondary { background: #475467; }
    button:disabled { background: #98a2b3; cursor: not-allowed; }
    .notice { border-radius: 10px; padding: 12px 14px; margin-top: 14px; background: #fef7c3; color: #854a0e; font-weight: 700; }
    .notice.ok { background: #dcfae6; color: #067647; }
    .notice.bad { background: #fee4e2; color: #b42318; }
    pre { background: #101828; color: #e4e7ec; padding: 16px; border-radius: 10px; overflow: auto; max-height: 360px; font-size: 13px; }
    .muted { color: #667085; }
  </style>
</head>
<body>
  <header>
    <h1>AI Software Factory Repair Dashboard</h1>
    <div>Platform admin self-healing, release gate, and repair workflow monitor.</div>
  </header>
  <main>
    <section class="card">
      <h2>Platform Token</h2>
      <p class="muted">For local development, paste your PLATFORM_INTERNAL_TOKEN from .env. It is stored only in this browser's localStorage.</p>
      <input id="token" type="password" placeholder="X-Platform-Internal-Token" />
      <button onclick="saveToken()">Save Token</button>
      <button class="secondary" onclick="clearToken()">Clear Token</button>
      <div id="lastAction" class="notice">Ready. Save token, then run a dashboard action.</div>
    </section>

    <section class="card">
      <h2>Actions</h2>
      <button onclick="refreshHealth()">Refresh Health</button>
      <button onclick="runWorkflow()">Run Repair Workflow</button>
      <button onclick="runFastGate()">Run Fast Release Gate</button>
      <button class="secondary" onclick="loadReports()">Load Reports</button>
    </section>

    <section class="card">
      <h2>Status</h2>
      <div class="grid">
        <div class="metric"><div class="metric-label">Health</div><div id="healthStatus" class="metric-value warn">Not checked</div></div>
        <div class="metric"><div class="metric-label">Repair Needed</div><div id="repairNeeded" class="metric-value warn">Unknown</div></div>
        <div class="metric"><div class="metric-label">Fast Gate</div><div id="fastGate" class="metric-value warn">Unknown</div></div>
        <div class="metric"><div class="metric-label">Latest Report</div><div id="latestReport" class="metric-value small-value">None</div></div>
      </div>
    </section>

    <section class="card">
      <h2>Raw Result</h2>
      <pre id="output">No API result yet.</pre>
    </section>
  </main>

  <script>
    const tokenInput = document.getElementById('token');
    tokenInput.value = localStorage.getItem('platformInternalToken') || '';

    function setOutput(data) { document.getElementById('output').textContent = JSON.stringify(data, null, 2); }
    function setNotice(message, status = 'warn') {
      const element = document.getElementById('lastAction');
      element.textContent = message;
      element.className = 'notice ' + status;
    }
    function saveToken() {
      localStorage.setItem('platformInternalToken', tokenInput.value.trim());
      setNotice('Token saved. You can now run dashboard actions.', 'ok');
      setOutput({ message: 'Token saved locally in this browser.' });
    }
    function clearToken() {
      localStorage.removeItem('platformInternalToken');
      tokenInput.value = '';
      setNotice('Token cleared.', 'warn');
      setOutput({ message: 'Token cleared.' });
    }
    function getToken() {
      const token = tokenInput.value.trim() || localStorage.getItem('platformInternalToken');
      if (!token) { throw new Error('Missing platform token. Paste PLATFORM_INTERNAL_TOKEN from .env first.'); }
      return token;
    }
    function setMetric(id, value, status, small = false) {
      const element = document.getElementById(id);
      element.textContent = value;
      element.className = 'metric-value ' + status + (small ? ' small-value' : '');
    }
    async function apiFetch(path, options = {}) {
      const token = getToken();
      const response = await fetch(path, { ...options, headers: { 'X-Platform-Internal-Token': token, ...(options.headers || {}) } });
      const data = await response.json();
      if (!response.ok || data.passed === false) { throw new Error(JSON.stringify(data)); }
      return data;
    }
    function showError(action, error) {
      setNotice(action + ' failed. See Raw Result for details.', 'bad');
      setOutput({ action, error: String(error) });
    }
    async function refreshHealth() {
      setNotice('Refreshing health...', 'warn');
      try {
        const data = await apiFetch('/platform/repair/health');
        setOutput(data);
        const parsed = data.parsed_output || {};
        setMetric('healthStatus', parsed.healthy ? 'Healthy' : 'Issue', parsed.healthy ? 'ok' : 'bad');
        const repairNeeded = parsed.summary ? parsed.summary.planner_repair_needed : null;
        setMetric('repairNeeded', repairNeeded ? 'Yes' : 'No', repairNeeded ? 'bad' : 'ok');
        const latest = parsed.latest_repair_report && parsed.latest_repair_report.latest_report;
        setMetric('latestReport', latest ? latest.filename : 'None', latest ? 'ok' : 'warn', true);
        setNotice('Health refreshed successfully.', 'ok');
      } catch (error) { showError('Refresh Health', error); }
    }
    async function runWorkflow() {
      setNotice('Running repair workflow...', 'warn');
      try {
        const data = await apiFetch('/platform/repair/workflow?summary=true', { method: 'POST' });
        setOutput(data);
        const parsed = data.parsed_output || {};
        setMetric('healthStatus', parsed.passed ? 'Healthy' : 'Issue', parsed.passed ? 'ok' : 'bad');
        setMetric('repairNeeded', parsed.repair_needed ? 'Yes' : 'No', parsed.repair_needed ? 'bad' : 'ok');
        setMetric('fastGate', parsed.fast_release_gate_passed ? 'Passed' : 'Failed', parsed.fast_release_gate_passed ? 'ok' : 'bad');
        setMetric('latestReport', parsed.latest_report ? parsed.latest_report.filename : 'None', parsed.latest_report ? 'ok' : 'warn', true);
        setNotice('Repair workflow completed successfully.', 'ok');
      } catch (error) { showError('Run Repair Workflow', error); }
    }
    async function runFastGate() {
      setNotice('Running fast release gate...', 'warn');
      try {
        const data = await apiFetch('/platform/release-gate/fast');
        setOutput(data);
        const parsed = data.parsed_output || {};
        setMetric('fastGate', parsed.passed ? 'Passed' : 'Failed', parsed.passed ? 'ok' : 'bad');
        setNotice(parsed.passed ? 'Fast release gate passed.' : 'Fast release gate failed.', parsed.passed ? 'ok' : 'bad');
      } catch (error) { showError('Run Fast Release Gate', error); }
    }
    async function loadReports() {
      setNotice('Loading reports...', 'warn');
      try {
        const data = await apiFetch('/platform/repair/reports?limit=5');
        setOutput(data);
        const parsed = data.parsed_output || {};
        const reports = parsed.reports || [];
        setMetric('latestReport', reports.length ? reports[0].filename : 'None', reports.length ? 'ok' : 'warn', true);
        setNotice(reports.length ? 'Reports loaded successfully.' : 'No repair reports found.', reports.length ? 'ok' : 'warn');
      } catch (error) { showError('Load Reports', error); }
    }
  </script>
</body>
</html>
"""


def extract_json_block(stdout: str) -> Optional[dict]:
    start = stdout.find("{")
    end = stdout.rfind("}")

    if start == -1 or end == -1 or end <= start:
        return None

    try:
        return json.loads(stdout[start : end + 1])
    except json.JSONDecodeError:
        return None


def run_platform_command(command: list, timeout: int = COMMAND_TIMEOUT_SECONDS) -> dict:
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        parsed_output = extract_json_block(result.stdout)

        return {
            "passed": result.returncode == 0,
            "return_code": result.returncode,
            "command": " ".join(command),
            "parsed_output": parsed_output,
            "stdout": result.stdout,
            "stderr": result.stderr if result.returncode != 0 else "",
            "timed_out": False,
        }
    except subprocess.TimeoutExpired as error:
        return {
            "passed": False,
            "return_code": None,
            "command": " ".join(command),
            "parsed_output": None,
            "stdout": error.stdout or "",
            "stderr": error.stderr or "",
            "timed_out": True,
            "timeout_seconds": timeout,
        }


def clamp_limit(limit: int) -> int:
    if limit < 1:
        return 1

    if limit > MAX_LIST_LIMIT:
        return MAX_LIST_LIMIT

    return limit


@router.get("/dashboard/repair", response_class=HTMLResponse)
def repair_dashboard():
    return HTMLResponse(REPAIR_DASHBOARD_HTML)


@router.get("/tenants")
@limiter.limit(PLATFORM_API_RATE_LIMIT)
def list_tenants(
    request: Request,
    limit: int = 50,
    db: Session = Depends(get_platform_db),
    platform_admin=Depends(require_platform_admin),
):
    safe_limit = clamp_limit(limit)
    tenants = db.query(PlatformTenant).order_by(PlatformTenant.id.desc()).limit(safe_limit).all()

    return {
        "items": [
            {
                "tenant_id": tenant.tenant_id,
                "name": tenant.name,
                "status": tenant.status,
                "plan": tenant.plan,
                "owner_id": tenant.owner_id,
            }
            for tenant in tenants
        ],
        "limit": safe_limit,
    }


@router.get("/workspaces")
@limiter.limit(PLATFORM_API_RATE_LIMIT)
def list_workspaces(
    request: Request,
    limit: int = 50,
    db: Session = Depends(get_platform_db),
    platform_admin=Depends(require_platform_admin),
):
    safe_limit = clamp_limit(limit)
    workspaces = (
        db.query(PlatformWorkspace)
        .order_by(PlatformWorkspace.id.desc())
        .limit(safe_limit)
        .all()
    )

    return {
        "items": [
            {
                "tenant_id": workspace.tenant_id,
                "workspace_id": workspace.workspace_id,
                "status": workspace.status,
                "owner_id": workspace.owner_id,
            }
            for workspace in workspaces
        ],
        "limit": safe_limit,
    }


@router.get("/projects")
@limiter.limit(PLATFORM_API_RATE_LIMIT)
def list_projects(
    request: Request,
    limit: int = 50,
    db: Session = Depends(get_platform_db),
    platform_admin=Depends(require_platform_admin),
):
    safe_limit = clamp_limit(limit)
    projects = db.query(PlatformProject).order_by(PlatformProject.id.desc()).limit(safe_limit).all()

    return {
        "items": [
            {
                "tenant_id": project.tenant_id,
                "workspace_id": project.workspace_id,
                "project_id": project.project_id,
                "generation_status": project.generation_status,
                "runtime_status": project.runtime_status,
                "deployment_status": project.deployment_status,
                "current_version": project.current_version,
                "generation_count": project.generation_count,
                "repair_count": project.repair_count,
            }
            for project in projects
        ],
        "limit": safe_limit,
    }


@router.get("/generation-runs")
@limiter.limit(PLATFORM_API_RATE_LIMIT)
def list_generation_runs(
    request: Request,
    limit: int = 50,
    db: Session = Depends(get_platform_db),
    platform_admin=Depends(require_platform_admin),
):
    safe_limit = clamp_limit(limit)
    generation_runs = (
        db.query(PlatformGenerationRun)
        .order_by(PlatformGenerationRun.id.desc())
        .limit(safe_limit)
        .all()
    )

    return {
        "items": [
            {
                "run_id": generation_run.run_id,
                "tenant_id": generation_run.tenant_id,
                "workspace_id": generation_run.workspace_id,
                "project_id": generation_run.project_id,
                "status": generation_run.status,
                "review_status": generation_run.review_status,
                "runtime_status": generation_run.runtime_status,
                "error_summary": generation_run.error_summary,
                "started_at": generation_run.started_at,
                "completed_at": generation_run.completed_at,
            }
            for generation_run in generation_runs
        ],
        "limit": safe_limit,
    }


@router.get("/repair/health")
@limiter.limit(PLATFORM_API_RATE_LIMIT)
def get_repair_health(
    request: Request,
    platform_admin=Depends(require_platform_admin),
):
    return run_platform_command(
        [
            sys.executable,
            "-m",
            "app.platform.repair.health",
        ]
    )


@router.post("/repair/workflow")
@limiter.limit(PLATFORM_API_RATE_LIMIT)
def run_repair_workflow(
    request: Request,
    summary: bool = True,
    platform_admin=Depends(require_platform_admin),
):
    command = [
        sys.executable,
        "-m",
        "app.platform.repair.workflow",
        "--dry-run",
    ]

    if summary:
        command.append("--summary")

    return run_platform_command(command)


@router.get("/repair/reports")
@limiter.limit(PLATFORM_API_RATE_LIMIT)
def list_repair_reports(
    request: Request,
    limit: int = 10,
    platform_admin=Depends(require_platform_admin),
):
    safe_limit = clamp_limit(limit)

    return run_platform_command(
        [
            sys.executable,
            "-m",
            "app.platform.repair.list_reports",
            "--limit",
            str(safe_limit),
        ]
    )


@router.get("/release-gate/fast")
@limiter.limit(PLATFORM_API_RATE_LIMIT)
def run_fast_release_gate(
    request: Request,
    platform_admin=Depends(require_platform_admin),
):
    return run_platform_command(
        [
            sys.executable,
            "-m",
            "app.platform.release_gate",
            "--mode",
            "fast",
        ]
    )
