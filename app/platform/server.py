from __future__ import annotations

from dataclasses import asdict

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from app.platform.ai_workforce.service import build_workforce_summary
from app.platform.executive_office.service import build_executive_briefing
from app.platform.health import build_health_status, build_readiness_status
from app.platform.knowledge_vault.service import build_knowledge_vault_summary
from app.platform.logging.install import install_request_logging
from app.platform.mission_control.service import build_mission_control_summary
from app.platform.ui.mission_control import render_dashboard
from app.platform.company_objects.service import build_company_object_registry
from app.platform.board_room.service import build_board_room_summary
from app.platform.company_brain.service import build_company_brain_repository_summary
from app.platform.company_graph.service import build_company_graph
from app.platform.founder_workspace.service import build_founder_workspace_summary, build_request_intake
from app.platform.proposal_generator.service import build_proposal_generator_summary, generate_proposal
from app.platform.founder_approval.service import (
    approve_proposal,
    build_founder_approval_summary,
    get_proposal_status,
    reject_proposal,
)
from app.platform.mission_execution.service import (
    build_mission_execution_summary,
    get_mission_status,
    plan_mission,
    start_mission,
)
from app.platform.runtime.service import (
    build_ai_provider_status,
    build_persistent_runtime_summary,
    build_runtime_event,
    build_runtime_memory_status,
    build_secret_manager_status,
    build_worker_next_step,
    invoke_ai,
)
from app.platform.autonomous_engineering.service import (
    build_autonomous_engineering_summary,
    create_engineering_blueprint,
    create_pr_plan,
)
from app.platform.repository_intelligence.service import (
    build_file_plan,
    build_repository_context,
    build_repository_index,
    build_repository_intelligence_summary,
    search_repository,
)
from app.platform.code_planner.service import (
    build_code_planner_summary,
    build_code_status,
    generate_code_patch,
    package_code_proposal,
    validate_code_proposal,
)
from app.platform.patch_application.service import (
    apply_patch_application,
    build_patch_application_summary,
    get_patch_application_status,
    prepare_patch_application,
)
from app.platform.pr_orchestration.service import (
    build_gcp_handover_status,
    build_pr_orchestration_summary,
    create_pull_request_record,
    get_pull_request_status,
    prepare_pull_request,
)
from app.platform.founder_console.service import build_founder_console_summary
from app.platform.github_execution.service import (
    build_github_execution_summary,
    execute_github_execution,
    get_github_execution_status,
    plan_github_execution,
)
from app.platform.ci_repair.service import (
    build_ci_repair_summary,
    diagnose_ci_failure,
    get_ci_repair_status,
    plan_ci_repair,
    retry_ci_repair,
)

app = FastAPI(title="AI Software Factory", version="1.0.0")
install_request_logging(app)


@app.get("/")
def root():
    return {"service": "ai-software-factory", "status": "running"}


@app.get("/health")
def health():
    return build_health_status()


@app.get("/ready")
def ready():
    return build_readiness_status()


@app.get("/ui", response_class=HTMLResponse)
def ui():
    return render_dashboard()


@app.get("/mission-control/ui", response_class=HTMLResponse)
def mission_control_ui():
    return render_dashboard()


@app.get("/mission-control/founder-console")
def founder_console():
    return build_founder_console_summary()


@app.get("/mission-control")
def mission_control():
    return asdict(build_mission_control_summary())


@app.get("/mission-control/summary")
def mission_control_summary():
    return asdict(build_mission_control_summary())


@app.get("/mission-control/health")
def mission_control_health():
    summary = build_mission_control_summary()
    return {
        "service": "mission-control",
        "company": summary.company,
        "status": summary.health,
        "environment": summary.environment,
        "region": summary.region,
    }


@app.get("/mission-control/version")
def mission_control_version():
    summary = build_mission_control_summary()
    return {
        "service": "mission-control",
        "version": summary.version,
        "environment": summary.environment,
    }


@app.get("/mission-control/executive-office")
def executive_office():
    return build_executive_briefing()


@app.get("/mission-control/workforce")
def workforce():
    return build_workforce_summary()


@app.get("/mission-control/knowledge-vault")
def knowledge_vault():
    return build_knowledge_vault_summary()


@app.get("/mission-control/company-objects")
def company_objects():
    return build_company_object_registry()


@app.get("/mission-control/board-room")
def board_room():
    return build_board_room_summary()


@app.get("/mission-control/company-brain")
def company_brain():
    return build_company_brain_repository_summary()


@app.get("/mission-control/company-graph")
def company_graph():
    return build_company_graph()


@app.get("/mission-control/founder")
def founder_workspace():
    return build_founder_workspace_summary()


@app.post("/mission-control/requests")
def request_intake(payload: dict):
    return build_request_intake(payload)


@app.get("/mission-control/proposals")
def proposal_generator():
    return build_proposal_generator_summary()


@app.post("/mission-control/proposals/generate")
def proposal_generate(payload: dict):
    return generate_proposal(payload)


@app.get("/mission-control/approvals")
def founder_approval():
    return build_founder_approval_summary()


@app.get("/mission-control/proposals/{proposal_id}")
def proposal_status(proposal_id: str):
    return get_proposal_status(proposal_id)


@app.post("/mission-control/proposals/approve")
def proposal_approve(payload: dict):
    return approve_proposal(payload)


@app.post("/mission-control/proposals/reject")
def proposal_reject(payload: dict):
    return reject_proposal(payload)


@app.get("/mission-control/missions")
def missions():
    return build_mission_execution_summary()


@app.get("/mission-control/missions/{mission_id}")
def mission_status(mission_id: str):
    return get_mission_status(mission_id)


@app.post("/mission-control/missions/plan")
def mission_plan(payload: dict):
    return plan_mission(payload)


@app.post("/mission-control/missions/start")
def mission_start(payload: dict):
    return start_mission(payload)


@app.get("/mission-control/runtime")
def persistent_runtime():
    return build_persistent_runtime_summary()


@app.get("/mission-control/runtime/memory")
def runtime_memory():
    return build_runtime_memory_status()


@app.get("/mission-control/runtime/ai-provider")
def runtime_ai_provider():
    return build_ai_provider_status()


@app.post("/mission-control/runtime/ai/invoke")
def runtime_ai_invoke(payload: dict):
    return invoke_ai(payload)


@app.post("/mission-control/runtime/worker/next-step")
def runtime_worker_next_step(payload: dict):
    return build_worker_next_step(payload)


@app.get("/mission-control/runtime/secrets")
def runtime_secrets():
    return build_secret_manager_status()


@app.post("/mission-control/runtime/events")
def runtime_events(payload: dict):
    return build_runtime_event(payload)


@app.get("/mission-control/engineering-worker")
def engineering_worker():
    return build_autonomous_engineering_summary()


@app.post("/mission-control/engineering-worker/blueprint")
def engineering_worker_blueprint(payload: dict):
    return create_engineering_blueprint(payload)


@app.post("/mission-control/engineering-worker/pr-plan")
def engineering_worker_pr_plan(payload: dict):
    return create_pr_plan(payload)


@app.get("/mission-control/repository")
def repository_intelligence():
    return build_repository_intelligence_summary()


@app.post("/mission-control/repository/index")
def repository_index(payload: dict):
    return build_repository_index(payload)


@app.post("/mission-control/repository/context")
def repository_context(payload: dict):
    return build_repository_context(payload)


@app.post("/mission-control/repository/search")
def repository_search(payload: dict):
    return search_repository(payload)


@app.post("/mission-control/repository/file-plan")
def repository_file_plan(payload: dict):
    return build_file_plan(payload)


@app.get("/mission-control/code")
def code_planner():
    return build_code_planner_summary()


@app.get("/mission-control/code/status")
def code_status():
    return build_code_status()


@app.post("/mission-control/code/generate")
def code_generate(payload: dict):
    return generate_code_patch(payload)


@app.post("/mission-control/code/validate")
def code_validate(payload: dict):
    return validate_code_proposal(payload)


@app.post("/mission-control/code/package")
def code_package(payload: dict):
    return package_code_proposal(payload)


@app.get("/mission-control/patches")
def patches():
    return build_patch_application_summary()


@app.post("/mission-control/patches/prepare")
def patches_prepare(payload: dict):
    return prepare_patch_application(payload)


@app.post("/mission-control/patches/apply")
def patches_apply(payload: dict):
    return apply_patch_application(payload)


@app.post("/mission-control/patches/status")
def patches_status(payload: dict):
    return get_patch_application_status(payload)


@app.get("/mission-control/pull-requests")
def pull_requests():
    return build_pr_orchestration_summary()


@app.post("/mission-control/pull-requests/prepare")
def pull_requests_prepare(payload: dict):
    return prepare_pull_request(payload)


@app.post("/mission-control/pull-requests/create")
def pull_requests_create(payload: dict):
    return create_pull_request_record(payload)


@app.post("/mission-control/pull-requests/status")
def pull_requests_status(payload: dict):
    return get_pull_request_status(payload)


@app.get("/mission-control/github-executor")
def github_executor():
    return build_github_execution_summary()


@app.post("/mission-control/github-executor/plan")
def github_executor_plan(payload: dict):
    return plan_github_execution(payload)


@app.post("/mission-control/github-executor/execute")
def github_executor_execute(payload: dict):
    return execute_github_execution(payload)


@app.post("/mission-control/github-executor/status")
def github_executor_status(payload: dict):
    return get_github_execution_status(payload)


@app.get("/mission-control/ci-repair")
def ci_repair():
    return build_ci_repair_summary()


@app.post("/mission-control/ci-repair/diagnose")
def ci_repair_diagnose(payload: dict):
    return diagnose_ci_failure(payload)


@app.post("/mission-control/ci-repair/plan")
def ci_repair_plan(payload: dict):
    return plan_ci_repair(payload)


@app.post("/mission-control/ci-repair/retry")
def ci_repair_retry(payload: dict):
    return retry_ci_repair(payload)


@app.post("/mission-control/ci-repair/status")
def ci_repair_status(payload: dict):
    return get_ci_repair_status(payload)


@app.get("/mission-control/handover")
def mission_control_handover():
    return build_gcp_handover_status()
