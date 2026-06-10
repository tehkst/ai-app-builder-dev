# Code Size Audit

Objective: keep Python source code files at or below 200 lines.

## Refactored In This Pass

- `app/ai/nodes/template_enforcer.py`: reduced from 1,456 lines to a 41-line orchestration node.
- `app/ai/templates/*.py`: trusted template payloads split into one-template modules; all are under 200 lines.
- `app/platform/services/controlled_sandbox_runtime_service.py`: reduced from 583 lines to a 22-line compatibility facade.
- `app/platform/services/controlled_runtime_*.py`: runtime command, log, registry, response, runner, safety, status, and workspace modules are all under 200 lines.
- `app/platform/services/agent_workflow_executor_service.py`: reduced from 512 lines to 184 lines.
- `app/platform/services/agent_workflow_*.py`: workflow audit, context, JSON, limits, result, scalability, and step helpers are all under 200 lines.
- `docs/PROJECT_MILESTONE_PLAN.md`: removed from the repository.

## Remaining Python Files Over 200 Lines

- `app/platform/persistence/models.py`: 476 lines
- `app/platform/api/routes.py`: 470 lines
- `app/platform/services/agent_task_service.py`: 414 lines
- `app/platform/services/runtime_readiness_detector_service.py`: 408 lines
- `app/platform/services/generated_file_version_restore_execution_service.py`: 398 lines
- `app/platform/agents/specialists.py`: 365 lines
- `app/platform/persistence/crud.py`: 327 lines
- `app/platform/services/workflow_run_persistence_service.py`: 320 lines
- `app/platform/services/generated_file_persistence_service.py`: 318 lines
- `app/platform/services/persistent_state_store_service.py`: 312 lines
- `app/platform/agents/version_restore_execution_check.py`: 307 lines
- `app/platform/repair/plan_repair.py`: 292 lines
- `app/platform/agents/self_healing_loop_coordinator_check.py`: 291 lines
- `app/platform/agents/repair_rerun_coordinator_check.py`: 277 lines
- `app/platform/services/generated_file_version_restore_approval_service.py`: 271 lines
- `app/platform/services/capability_recovery_service.py`: 268 lines
- `app/platform/agents/version_restore_approval_decision_check.py`: 268 lines
- `app/platform/services/agent_execution_planner_service.py`: 265 lines
- `app/platform/repair/workflow.py`: 258 lines
- `app/platform/services/runtime_approval_gate_service.py`: 251 lines
- `app/platform/agents/repair_executor_check.py`: 246 lines
- `app/platform/dashboard/approval_dashboard.py`: 241 lines
- `app/platform/agents/internal_dogfooding_module_check.py`: 240 lines
- `app/platform/services/materialization_sandbox_writer_service.py`: 235 lines
- `app/platform/services/internal_dogfooding_module_service.py`: 235 lines
- `app/platform/repair/execute_plan.py`: 235 lines
- `app/platform/repair/simulate_failure.py`: 231 lines
- `app/platform/agents/version_restore_approval_workflow_check.py`: 227 lines
- `app/platform/agents/production_config_healthcheck_check.py`: 226 lines
- `app/platform/services/self_healing_loop_coordinator_service.py`: 225 lines
- `app/ai/nodes/dependency_guard.py`: 224 lines
- `app/platform/repair/health.py`: 221 lines
- `app/platform/services/repair_executor_service.py`: 220 lines
- `app/platform/services/production_config_service.py`: 214 lines
- `app/platform/services/agent_execution_bridge_service.py`: 214 lines
- `app/platform/agents/static_preview_browser_smoke_check.py`: 214 lines
- `app/platform/agents/version_history_dashboard_panel_check.py`: 213 lines
- `app/platform/agents/factory.py`: 211 lines
- `app/platform/agents/auth_admin_access_gate_check.py`: 211 lines
- `app/platform/services/self_build_module_request_service.py`: 209 lines
- `app/platform/services/agent_factory_registration_service.py`: 209 lines
- `app/platform/agents/run_project.py`: 209 lines
- `app/platform/services/generated_file_version_service.py`: 207 lines
- `app/platform/agents/version_restore_simulation_check.py`: 204 lines
- `app/ai/nodes/reviewer.py`: 202 lines

Total remaining over-limit Python files: 45
