from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.platform.agents.app_build_request_run_check import run_app_build_request
from app.platform.api.security import require_platform_admin
from app.platform.persistence.database import get_platform_db
from app.platform.services.generated_file_persistence_service import (
    get_persisted_generated_file,
    list_persisted_generated_files,
)
from app.platform.services.generated_file_rollback_service import (
    extract_generated_files_from_workflow_detail,
)
from app.platform.services.workflow_run_persistence_service import (
    compact_workflow_run_summary,
    get_workflow_run_detail,
    list_recent_workflow_runs,
)


APP_BUILD_DASHBOARD_HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>AI Software Factory App Build Dashboard</title>
  <style>
    body { margin: 0; font-family: Arial, sans-serif; background: #f6f7fb; color: #172033; }
    header { background: #172033; color: white; padding: 24px 32px; }
    main { max-width: 1100px; margin: 24px auto; padding: 0 20px 40px; }
    .card { background: white; border: 1px solid #dde2ee; border-radius: 12px; padding: 20px; margin-bottom: 18px; box-shadow: 0 2px 8px rgba(20, 30, 50, 0.06); }
    textarea, input { width: 100%; box-sizing: border-box; padding: 12px; border: 1px solid #cbd5e1; border-radius: 8px; font-size: 14px; margin-top: 8px; }
    textarea { min-height: 90px; }
    button { border: 0; background: #2563eb; color: white; border-radius: 8px; padding: 11px 14px; font-weight: 700; cursor: pointer; margin-right: 8px; margin-top: 12px; }
    button.secondary { background: #475467; }
    .notice { border-radius: 10px; padding: 12px 14px; margin-top: 14px; background: #fef7c3; color: #854a0e; font-weight: 700; }
    .notice.ok { background: #dcfae6; color: #067647; }
    .notice.bad { background: #fee4e2; color: #b42318; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 14px; }
    .metric { border: 1px solid #e3e7f0; border-radius: 10px; padding: 16px; background: #fbfcff; min-width: 0; }
    .metric-label { color: #667085; font-size: 13px; margin-bottom: 8px; }
    .metric-value { font-size: 20px; font-weight: 700; overflow-wrap: anywhere; word-break: break-word; line-height: 1.25; }
    pre { background: #101828; color: #e4e7ec; padding: 16px; border-radius: 10px; overflow: auto; max-height: 420px; font-size: 13px; }
    table { width: 100%; border-collapse: collapse; margin-top: 12px; }
    th, td { text-align: left; padding: 10px; border-bottom: 1px solid #e3e7f0; font-size: 14px; vertical-align: top; }
    th { color: #475467; }
    .muted { color: #667085; }
    .workspace-layout { display: grid; grid-template-columns: minmax(240px, 320px) 1fr; gap: 14px; }
    .file-list { border: 1px solid #e3e7f0; border-radius: 10px; background: #fbfcff; padding: 10px; max-height: 420px; overflow: auto; }
    .file-item { display: block; width: 100%; text-align: left; color: #172033; background: white; border: 1px solid #e3e7f0; border-radius: 8px; padding: 10px; margin: 0 0 8px 0; font-weight: 700; cursor: pointer; overflow-wrap: anywhere; }
    .file-item:hover { background: #eef4ff; }
    .file-viewer { min-width: 0; }
  </style>
</head>
<body>
  <header>
    <h1>AI Software Factory App Build Dashboard</h1>
    <div>Run app-build workflows, inspect summaries, and view recent runs.</div>
  </header>

  <main>
    <section class="card">
      <h2>Platform Token</h2>
      <p class="muted">Paste your PLATFORM_INTERNAL_TOKEN from .env. It is stored only in this browser's localStorage.</p>
      <input id="token" type="password" placeholder="X-Platform-Internal-Token" />
      <button onclick="saveToken()">Save Token</button>
      <button class="secondary" onclick="clearToken()">Clear Token</button>
      <div id="lastAction" class="notice">Ready. Save token, then run an app-build workflow.</div>
    </section>

    <section class="card">
      <h2>Run App Build</h2>
      <textarea id="appRequest">Build me a booking app for yoga classes</textarea>
      <label><input id="realBridge" type="checkbox" checked /> Use real agent bridge</label>
      <br />
      <button onclick="runAppBuild()">Run App Build</button>
      <button class="secondary" onclick="loadRecentRuns()">Load Recent Runs</button>
    </section>

    <section class="card">
      <h2>Current Run</h2>
      <div class="grid">
        <div class="metric"><div class="metric-label">Workflow Run ID</div><div id="workflowRunId" class="metric-value">None</div></div>
        <div class="metric"><div class="metric-label">Status</div><div id="runStatus" class="metric-value">Unknown</div></div>
        <div class="metric"><div class="metric-label">Completed Steps</div><div id="completedSteps" class="metric-value">0</div></div>
        <div class="metric"><div class="metric-label">Blocked / Failed</div><div id="blockedFailed" class="metric-value">0 / 0</div></div>
      </div>
      <button onclick="loadSummary()">Load Current Summary</button>
    </section>

    <section class="card">
      <h2>Recent Runs</h2>
      <div id="recentRuns">No recent runs loaded.</div>
    </section>

    <section class="card">
      <h2>Generated Files</h2>
      <p class="muted">Preview-only generated file metadata. No files are written to disk from this dashboard.</p>
      <div class="grid">
        <div class="metric"><div class="metric-label">Generated File Count</div><div id="generatedFileCount" class="metric-value">0</div></div>
        <div class="metric"><div class="metric-label">Write Mode</div><div id="generatedFileWriteMode" class="metric-value">preview_only</div></div>
      </div>
      <div id="generatedFiles">No generated files loaded.</div>
    </section>

    <section class="card">
      <h2>Workspace Explorer</h2>
      <p class="muted">DB-backed explorer for persisted generated files. Viewer-only: no disk writes, no execution.</p>
      <button onclick="loadWorkspaceExplorer()">Load Workspace Explorer</button>
      <div class="grid">
        <div class="metric"><div class="metric-label">Persisted Files</div><div id="workspaceFileCount" class="metric-value">0</div></div>
        <div class="metric"><div class="metric-label">Workspace Write Mode</div><div id="workspaceWriteMode" class="metric-value">db_preview_only</div></div>
      </div>
      <div class="workspace-layout" style="margin-top:14px;">
        <div class="file-list" id="workspaceFileList">No persisted files loaded.</div>
        <div class="file-viewer">
          <div class="metric">
            <div class="metric-label">Selected File</div>
            <div id="workspaceSelectedPath" class="metric-value">None</div>
            <div id="workspaceSelectedMeta" class="muted" style="margin-top:8px;">No file selected.</div>
          </div>
          <pre id="workspaceFilePreview">No file preview loaded.</pre>
        </div>
      </div>
    </section>

    <section class="card">
      <h2>Agent Output Preview</h2>
      <p class="muted">Shows the detailed handler output from each workflow step.</p>
      <div id="agentOutputs">No agent outputs loaded.</div>
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
      setNotice('Token saved. You can now run app-build actions.', 'ok');
    }
    function clearToken() {
      localStorage.removeItem('platformInternalToken');
      tokenInput.value = '';
      setNotice('Token cleared.', 'warn');
    }
    function getToken() {
      const token = tokenInput.value.trim() || localStorage.getItem('platformInternalToken');
      if (!token) { throw new Error('Missing platform token. Paste PLATFORM_INTERNAL_TOKEN from .env first.'); }
      return token;
    }
    async function apiFetch(path, options = {}) {
      const response = await fetch(path, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          'X-Platform-Internal-Token': getToken(),
          ...(options.headers || {})
        }
      });
      const data = await response.json();
      if (!response.ok || data.success === false) { throw new Error(JSON.stringify(data)); }
      return data;
    }
    function updateSummary(data) {
      document.getElementById('workflowRunId').textContent = data.workflow_run_id || 'None';
      document.getElementById('runStatus').textContent = data.status || 'Unknown';
      document.getElementById('completedSteps').textContent = String(data.completed_step_count || 0);
      document.getElementById('blockedFailed').textContent = String(data.blocked_step_count || 0) + ' / ' + String(data.failed_step_count || 0);
    }
    async function runAppBuild() {
      setNotice('Running app-build workflow...', 'warn');
      try {
        const data = await apiFetch('/platform/app-build/run', {
          method: 'POST',
          body: JSON.stringify({
            app_request: document.getElementById('appRequest').value,
            real_bridge: document.getElementById('realBridge').checked
          })
        });
        setOutput(data);
        const summary = data.summary || {};
        updateSummary({
          workflow_run_id: summary.workflow_run_id,
          status: data.status,
          completed_step_count: summary.completed_step_count,
          blocked_step_count: summary.blocked_step_count,
          failed_step_count: summary.failed_step_count
        });
        setNotice('App-build workflow completed.', 'ok');
        await loadRecentRuns();
      } catch (error) {
        setNotice('Run failed. See Raw Result.', 'bad');
        setOutput({ error: String(error) });
      }
    }
    function escapeHtml(value) {
      return String(value)
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#039;');
    }

    function renderGeneratedFiles(data) {
      const files = data.generated_files || [];
      const container = document.getElementById('generatedFiles');
      document.getElementById('generatedFileCount').textContent = String(data.generated_file_count || files.length || 0);

      const writeModes = Array.from(new Set(files.map(file => file.write_status || 'unknown')));
      document.getElementById('generatedFileWriteMode').textContent = writeModes.length ? writeModes.join(', ') : 'none';

      if (!files.length) {
        container.textContent = 'No generated files found for this workflow run.';
        return;
      }

      container.innerHTML = files.map(file => {
        return '<div class="metric" style="margin-top:12px;">' +
          '<div class="metric-label">' + escapeHtml(file.path || 'unknown path') + ' · ' + escapeHtml(file.language || 'unknown language') + '</div>' +
          '<div class="metric-value" style="font-size:16px;">' + escapeHtml(file.purpose || 'No purpose provided') + '</div>' +
          '<div class="muted" style="margin-top:6px;">Write status: ' + escapeHtml(file.write_status || 'unknown') + '</div>' +
          '<div class="muted" style="margin-top:6px;">Source: ' + escapeHtml(file.source_step_id || 'unknown step') + ' / ' + escapeHtml(file.source_agent_id || 'unknown agent') + '</div>' +
          '<pre>' + escapeHtml(file.content_preview || '') + '</pre>' +
          '</div>';
      }).join('');
    }

    async function loadGeneratedFiles(workflowRunId) {
      const data = await apiFetch('/platform/app-build/runs/' + workflowRunId + '/generated-files');
      renderGeneratedFiles(data);
      return data;
    }

    function renderWorkspaceExplorer(data) {
      const files = data.generated_files || [];
      const list = document.getElementById('workspaceFileList');
      document.getElementById('workspaceFileCount').textContent = String(data.persisted_file_count || files.length || 0);
      document.getElementById('workspaceWriteMode').textContent = data.write_mode || 'db_preview_only';

      if (!files.length) {
        list.textContent = 'No persisted files found for this workflow run.';
        document.getElementById('workspaceSelectedPath').textContent = 'None';
        document.getElementById('workspaceSelectedMeta').textContent = 'No file selected.';
        document.getElementById('workspaceFilePreview').textContent = 'No file preview loaded.';
        return;
      }

      list.innerHTML = files.map(file => {
        return '<button class="file-item" onclick="loadWorkspaceFile(\'' + escapeHtml(file.generated_file_id || '') + '\')">' +
          escapeHtml(file.path || 'unknown path') +
          '<div class="muted" style="font-weight:400;margin-top:4px;">' + escapeHtml(file.write_status || 'unknown') + '</div>' +
          '</button>';
      }).join('');
    }

    async function loadWorkspaceExplorer() {
      const workflowRunId = document.getElementById('workflowRunId').textContent.trim();
      if (!workflowRunId || workflowRunId === 'None') {
        setNotice('No workflow_run_id selected for workspace explorer.', 'bad');
        return null;
      }

      setNotice('Loading workspace explorer...', 'warn');
      try {
        const data = await apiFetch('/platform/app-build/runs/' + workflowRunId + '/persisted-files');
        renderWorkspaceExplorer(data);
        setOutput(data);
        setNotice('Workspace explorer loaded.', 'ok');
        return data;
      } catch (error) {
        setNotice('Workspace explorer failed. Persist files first or see Raw Result.', 'bad');
        setOutput({ error: String(error) });
        return null;
      }
    }

    async function loadWorkspaceFile(generatedFileId) {
      if (!generatedFileId) {
        setNotice('Missing generated_file_id.', 'bad');
        return null;
      }

      setNotice('Loading workspace file...', 'warn');
      try {
        const data = await apiFetch('/platform/app-build/generated-files/' + generatedFileId);
        const file = data.generated_file || {};
        document.getElementById('workspaceSelectedPath').textContent = file.path || 'Unknown file';
        document.getElementById('workspaceSelectedMeta').textContent =
          'Hash: ' + (file.content_hash || 'none') +
          ' · Status: ' + (file.write_status || 'unknown') +
          ' · Source: ' + (file.source_step_id || 'unknown step') + ' / ' + (file.source_agent_id || 'unknown agent');
        document.getElementById('workspaceFilePreview').textContent = file.content_preview || '';
        setOutput(data);
        setNotice('Workspace file loaded.', 'ok');
        return data;
      } catch (error) {
        setNotice('Workspace file failed. See Raw Result.', 'bad');
        setOutput({ error: String(error) });
        return null;
      }
    }

    function renderAgentOutputs(detail) {
      const steps = detail.steps || [];
      const container = document.getElementById('agentOutputs');

      if (!steps.length) {
        container.textContent = 'No step outputs found.';
        return;
      }

      container.innerHTML = steps.map(step => {
        const handlerResult = step.handler_result || {};
        const pretty = JSON.stringify(handlerResult, null, 2);
        return '<div class="metric" style="margin-top:12px;">' +
          '<div class="metric-label">' + escapeHtml(step.step_id || 'unknown') + ' · ' + escapeHtml(step.selected_agent_id || 'no agent') + '</div>' +
          '<div class="metric-value" style="font-size:16px;">' + escapeHtml(step.title || 'Untitled Step') + '</div>' +
          '<div class="muted" style="margin-top:6px;">Status: ' + escapeHtml(step.status || 'unknown') + '</div>' +
          '<pre>' + escapeHtml(pretty) + '</pre>' +
          '</div>';
      }).join('');
    }

    async function loadDetail(workflowRunId) {
      const data = await apiFetch('/platform/app-build/runs/' + workflowRunId + '/detail');
      renderAgentOutputs(data);
      return data;
    }

    async function loadSummary() {
      const workflowRunId = document.getElementById('workflowRunId').textContent.trim();
      if (!workflowRunId || workflowRunId === 'None') {
        setNotice('No workflow_run_id selected.', 'bad');
        return;
      }
      setNotice('Loading summary...', 'warn');
      try {
        const data = await apiFetch('/platform/app-build/runs/' + workflowRunId + '/summary');
        setOutput(data);
        updateSummary(data);
        await loadDetail(workflowRunId);
        await loadGeneratedFiles(workflowRunId);
        await loadWorkspaceExplorer();
        setNotice('Summary, generated files, workspace explorer, and agent outputs loaded.', 'ok');
      } catch (error) {
        setNotice('Summary failed. See Raw Result.', 'bad');
        setOutput({ error: String(error) });
      }
    }

    async function selectRecentRun(workflowRunId) {
      document.getElementById('workflowRunId').textContent = workflowRunId;
      await loadSummary();
    }
    async function loadRecentRuns() {
      setNotice('Loading recent runs...', 'warn');
      try {
        const data = await apiFetch('/platform/app-build/runs/recent?limit=10');
        setOutput(data);
        const runs = data.workflow_runs || [];
        if (!runs.length) {
          document.getElementById('recentRuns').textContent = 'No recent runs found.';
        } else {
          document.getElementById('recentRuns').innerHTML = '<table><thead><tr><th>Run ID</th><th>Name</th><th>Status</th><th>Steps</th><th>Created</th><th>Action</th></tr></thead><tbody>' +
            runs.map(run => '<tr><td>' + run.workflow_run_id + '</td><td>' + run.workflow_name + '</td><td>' + run.status + '</td><td>' + run.completed_step_count + '/' + run.step_count + '</td><td>' + run.created_at + '</td><td><button onclick="selectRecentRun(\'' + run.workflow_run_id + '\')">Load Summary</button></td></tr>').join('') +
            '</tbody></table>';
        }
        setNotice('Recent runs loaded.', 'ok');
      } catch (error) {
        setNotice('Recent runs failed. See Raw Result.', 'bad');
        setOutput({ error: String(error) });
      }
    }
  </script>
</body>
</html>
"""


router = APIRouter(prefix="/platform/app-build", tags=["platform-app-build"])


class AppBuildRunRequest(BaseModel):
    app_request: str = Field(..., min_length=1)
    workflow_name: Optional[str] = None
    real_bridge: bool = False



@router.get("/dashboard", response_class=HTMLResponse)
def app_build_dashboard(
    _: bool = Depends(require_platform_admin),
):
    return HTMLResponse(APP_BUILD_DASHBOARD_HTML)


@router.post("/run")
def run_app_build(
    request: AppBuildRunRequest,
    _: bool = Depends(require_platform_admin),
) -> Dict[str, Any]:
    return run_app_build_request(
        app_request=request.app_request,
        workflow_name=request.workflow_name,
        real_bridge=request.real_bridge,
    )




@router.get("/runs/recent")
def list_recent_app_build_runs(
    limit: int = 10,
    _: bool = Depends(require_platform_admin),
    db: Session = Depends(get_platform_db),
) -> Dict[str, Any]:
    safe_limit = max(1, min(limit, 100))
    return {
        "success": True,
        "limit": safe_limit,
        "workflow_runs": list_recent_workflow_runs(
            db,
            limit=safe_limit,
        ),
    }


@router.get("/runs/{workflow_run_id}/summary")
def get_app_build_run_summary(
    workflow_run_id: str,
    _: bool = Depends(require_platform_admin),
    db: Session = Depends(get_platform_db),
) -> Dict[str, Any]:
    detail = get_workflow_run_detail(
        db,
        workflow_run_id=workflow_run_id,
    )
    return compact_workflow_run_summary(detail)


@router.get("/runs/{workflow_run_id}/detail")
def get_app_build_run_detail(
    workflow_run_id: str,
    _: bool = Depends(require_platform_admin),
    db: Session = Depends(get_platform_db),
) -> Dict[str, Any]:
    return get_workflow_run_detail(
        db,
        workflow_run_id=workflow_run_id,
    )


@router.get("/runs/{workflow_run_id}/generated-files")
def get_app_build_run_generated_files(
    workflow_run_id: str,
    _: bool = Depends(require_platform_admin),
    db: Session = Depends(get_platform_db),
) -> Dict[str, Any]:
    detail = get_workflow_run_detail(
        db,
        workflow_run_id=workflow_run_id,
    )
    generated_files = extract_generated_files_from_workflow_detail(detail)

    return {
        "success": True,
        "found": detail.get("found", False),
        "workflow_run_id": workflow_run_id,
        "workflow_name": detail.get("workflow_name"),
        "workflow_status": detail.get("status"),
        "generated_file_count": len(generated_files),
        "generated_files": generated_files,
    }

@router.get("/runs/{workflow_run_id}/persisted-files")
def get_app_build_run_persisted_files(
    workflow_run_id: str,
    _: bool = Depends(require_platform_admin),
    db: Session = Depends(get_platform_db),
) -> Dict[str, Any]:
    return list_persisted_generated_files(
        db,
        workflow_run_id=workflow_run_id,
    )


@router.get("/generated-files/{generated_file_id}")
def get_app_build_persisted_generated_file(
    generated_file_id: str,
    _: bool = Depends(require_platform_admin),
    db: Session = Depends(get_platform_db),
) -> Dict[str, Any]:
    return get_persisted_generated_file(
        db,
        generated_file_id=generated_file_id,
    )

