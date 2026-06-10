# Dependency Map

Generated from Python AST imports for `app/**/*.py` and top-level `test_*.py`.

## High-Level Internal Modules

- `app.ai` imports 30 internal modules: `app.ai.llm`, `app.ai.nodes.approval`, `app.ai.nodes.architect`, `app.ai.nodes.code_generator`, `app.ai.nodes.contract_guard`, `app.ai.nodes.dependency_guard`, `app.ai.nodes.file_generator`, `app.ai.nodes.file_writer`, `app.ai.nodes.fixer`, `app.ai.nodes.human_review`, `app.ai.nodes.interface_contract`, `app.ai.nodes.manifest_generator` ...
- `app.api` imports 9 internal modules: `app.api.dependencies`, `app.core.database`, `app.core.security`, `app.langgraph_app.graph`, `app.langgraph_app.resume_graph`, `app.models.user`, `app.services.auth_service`, `app.services.file_writer_service`, `app.services.project_service`
- `app.core` imports 1 internal modules: `app.core.observability`
- `app.langgraph_app` imports 11 internal modules: `app.core.llm`, `app.core.llm_security`, `app.langgraph_app.nodes.approval_node`, `app.langgraph_app.nodes.architect_node`, `app.langgraph_app.nodes.codegen_node`, `app.langgraph_app.nodes.intake_node`, `app.langgraph_app.nodes.product_spec_node`, `app.langgraph_app.nodes.qa_node`, `app.langgraph_app.nodes.security_node`, `app.langgraph_app.state`, `app.schemas.product_spec`
- `app.main` imports 11 internal modules: `app.api.routes`, `app.platform.api.agent_task_routes`, `app.platform.api.app_build_routes`, `app.platform.api.approval_routes`, `app.platform.api.platform_auth_routes`, `app.platform.api.routes`, `app.platform.api.telegram_routes`, `app.platform.persistence.database`, `app.platform.security.rate_limit`, `app.platform.security.rate_limit_audit`, `app.platform.services.production_config_service`
- `app.models` imports 5 internal modules: `app.core.database`, `app.models.membership`, `app.models.organization`, `app.models.project`, `app.models.user`
- `app.platform.agents` imports 62 internal modules: `app.main`, `app.platform.agents`, `app.platform.agents.app_build_request_run_check`, `app.platform.agents.approval_gated_static_preview_materialization_check`, `app.platform.agents.background_job_runner_readiness_check`, `app.platform.agents.builtin`, `app.platform.agents.deployment_pack_v86_check`, `app.platform.agents.factory`, `app.platform.agents.hosted_sandbox_boundary_check`, `app.platform.agents.orchestrator`, `app.platform.agents.production_config_healthcheck_check`, `app.platform.agents.registry` ...
- `app.platform.api` imports 54 internal modules: `app.core.security`, `app.platform.agents.app_build_request_run_check`, `app.platform.api.app_build`, `app.platform.api.app_build.dashboard`, `app.platform.api.app_build.generated_file_content_routes`, `app.platform.api.app_build.generated_file_runtime_routes`, `app.platform.api.app_build.materialization_routes`, `app.platform.api.app_build.module_routes`, `app.platform.api.app_build.repair_routes`, `app.platform.api.app_build.restore_approval_routes`, `app.platform.api.app_build.runs`, `app.platform.api.app_build.schemas` ...
- `app.platform.artifacts` imports 1 internal modules: `app.platform.artifacts.registry_report`
- `app.platform.compatibility` imports 2 internal modules: `app.platform.compatibility.dependency_policy`, `app.platform.compatibility.policy`
- `app.platform.persistence` imports 7 internal modules: `app.platform.persistence.audit`, `app.platform.persistence.crud`, `app.platform.persistence.database`, `app.platform.persistence.models`, `app.platform.projects.schemas`, `app.platform.tenants.schemas`, `app.platform.workspaces.schemas`
- `app.platform.repair` imports 2 internal modules: `app.platform.artifacts.detect_drift`, `app.platform.repair.simulate_failure`
- `app.platform.security` imports 2 internal modules: `app.platform.persistence.audit`, `app.platform.persistence.database`
- `app.platform.services` imports 36 internal modules: `app.platform.agents`, `app.platform.agents.registry`, `app.platform.guards.filesystem_write_guard`, `app.platform.persistence.database`, `app.platform.persistence.models`, `app.platform.services.agent_dependency_graph_service`, `app.platform.services.agent_execution_bridge_service`, `app.platform.services.agent_execution_planner_service`, `app.platform.services.agent_registry_persistence_service`, `app.platform.services.agent_task_service`, `app.platform.services.approval_service`, `app.platform.services.controlled_sandbox_runtime_service` ...
- `app.platform.telegram` imports 1 internal modules: `app.platform.telegram.config`
- `app.platform.workspaces` imports 5 internal modules: `app.platform.persistence.crud`, `app.platform.persistence.database`, `app.platform.persistence.repository`, `app.platform.workspaces.db_registry`, `app.platform.workspaces.schemas`
- `app.services` imports 5 internal modules: `app.core.security`, `app.models.membership`, `app.models.organization`, `app.models.project`, `app.models.user`
- `test_approve_and_write` imports 2 internal modules: `app.langgraph_app.resume_graph`, `app.services.file_writer_service`
- `test_codegen` imports 1 internal modules: `app.langgraph_app.resume_graph`
- `test_graph` imports 2 internal modules: `app.ai.graphs.approval_resume_graph`, `app.ai.graphs.project_graph`
- `test_resume` imports 1 internal modules: `app.langgraph_app.resume_graph`
- `test_write_files` imports 1 internal modules: `app.services.file_writer_service`

## App Build API Split

- `app/platform/api/app_build/__init__.py` (22 lines)
  imports: `app.platform.api.app_build.dashboard`, `app.platform.api.app_build.generated_file_content_routes`, `app.platform.api.app_build.generated_file_runtime_routes`, `app.platform.api.app_build.materialization_routes`, `app.platform.api.app_build.module_routes`, `app.platform.api.app_build.repair_routes`, `app.platform.api.app_build.restore_approval_routes`, `app.platform.api.app_build.runs`, `app.platform.api.app_build.workflow_runtime_routes`
- `app/platform/api/app_build/dashboard.py` (25 lines)
- `app/platform/api/app_build/generated_file_content_routes.py` (153 lines)
  imports: `app.platform.api.app_build.schemas`, `app.platform.api.security`, `app.platform.persistence.database`, `app.platform.services.generated_file_persistence_service`, `app.platform.services.generated_file_version_diff_service`, `app.platform.services.generated_file_version_restore_plan_service`, `app.platform.services.generated_file_version_restore_simulation_service`, `app.platform.services.generated_file_version_service`
- `app/platform/api/app_build/generated_file_runtime_routes.py` (93 lines)
  imports: `app.platform.api.security`, `app.platform.persistence.database`, `app.platform.services.generated_file_persistence_service`, `app.platform.services.runtime_approval_gate_service`, `app.platform.services.runtime_readiness_detector_service`, `app.platform.services.runtime_run_plan_builder_service`
- `app/platform/api/app_build/materialization_routes.py` (95 lines)
  imports: `app.platform.api.security`, `app.platform.persistence.database`, `app.platform.services.manual_browser_test_harness_service`, `app.platform.services.materialization_approval_record_service`, `app.platform.services.materialization_dry_run_service`, `app.platform.services.materialization_execution_gate_service`, `app.platform.services.materialization_sandbox_writer_service`
- `app/platform/api/app_build/module_routes.py` (182 lines)
  imports: `app.platform.api.security`, `app.platform.services.internal_dogfooding_module_service`, `app.platform.services.module_rollout_gate_service`, `app.platform.services.self_build_module_request_service`
- `app/platform/api/app_build/repair_routes.py` (174 lines)
  imports: `app.platform.api.security`, `app.platform.persistence.database`, `app.platform.services.repair_approval_gate_service`, `app.platform.services.repair_executor_service`, `app.platform.services.repair_plan_generator_service`, `app.platform.services.repair_rerun_coordinator_service`, `app.platform.services.self_healing_loop_coordinator_service`
- `app/platform/api/app_build/restore_approval_routes.py` (89 lines)
  imports: `app.platform.api.app_build.schemas`, `app.platform.api.security`, `app.platform.persistence.database`, `app.platform.services.generated_file_version_restore_approval_service`, `app.platform.services.generated_file_version_restore_execution_service`
- `app/platform/api/app_build/runs.py` (111 lines)
  imports: `app.platform.agents.app_build_request_run_check`, `app.platform.api.app_build.schemas`, `app.platform.api.security`, `app.platform.persistence.database`, `app.platform.services.generated_file_persistence_service`, `app.platform.services.generated_file_rollback_service`, `app.platform.services.workflow_run_persistence_service`
- `app/platform/api/app_build/schemas.py` (21 lines)
- `app/platform/api/app_build/workflow_runtime_routes.py` (140 lines)
  imports: `app.platform.api.security`, `app.platform.persistence.database`, `app.platform.services.controlled_sandbox_runtime_service`, `app.platform.services.runtime_approval_gate_service`, `app.platform.services.runtime_failure_analyzer_service`, `app.platform.services.runtime_readiness_detector_service`, `app.platform.services.runtime_run_plan_builder_service`

## Most-Connected Files

- `app/ai/graphs/project_graph.py` -> 18 internal imports
- `app/main.py` -> 11 internal imports
- `app/platform/api/app_build/__init__.py` -> 9 internal imports
- `app/platform/api/telegram_routes.py` -> 9 internal imports
- `app/langgraph_app/graph.py` -> 8 internal imports
- `app/platform/api/app_build/generated_file_content_routes.py` -> 8 internal imports
- `app/api/routes/projects.py` -> 7 internal imports
- `app/platform/agents/app_build_request_run_check.py` -> 7 internal imports
- `app/platform/agents/controlled_sandbox_runtime_check.py` -> 7 internal imports
- `app/platform/agents/controlled_sandbox_runtime_log_capture_check.py` -> 7 internal imports
- `app/platform/agents/version_diff_viewer_check.py` -> 7 internal imports
- `app/platform/agents/version_restore_approval_decision_check.py` -> 7 internal imports
- `app/platform/agents/version_restore_approval_workflow_check.py` -> 7 internal imports
- `app/platform/agents/version_restore_execution_check.py` -> 7 internal imports
- `app/platform/agents/version_restore_planning_check.py` -> 7 internal imports
- `app/platform/agents/version_restore_simulation_check.py` -> 7 internal imports
- `app/platform/api/app_build/materialization_routes.py` -> 7 internal imports
- `app/platform/api/app_build/repair_routes.py` -> 7 internal imports
- `app/platform/api/app_build/runs.py` -> 7 internal imports
- `app/platform/api/app_build/workflow_runtime_routes.py` -> 7 internal imports

## External Dependency Families

- `typing` used by 156 modules
- `json` used by 122 modules
- `__future__` used by 118 modules
- `sqlalchemy` used by 59 modules
- `fastapi` used by 53 modules
- `pathlib` used by 47 modules
- `uuid` used by 27 modules
- `datetime` used by 26 modules
- `argparse` used by 25 modules
- `pydantic` used by 17 modules
- `os` used by 11 modules
- `subprocess` used by 10 modules
- `sys` used by 9 modules
- `re` used by 8 modules
- `hashlib` used by 7 modules
- `dataclasses` used by 6 modules
- `dotenv` used by 6 modules
- `shutil` used by 6 modules
- `importlib` used by 4 modules
- `langgraph` used by 4 modules
- `tempfile` used by 4 modules
- `time` used by 4 modules
- `asyncio` used by 3 modules
- `enum` used by 3 modules
- `jose` used by 3 modules
- `slowapi` used by 3 modules
- `ast` used by 2 modules
- `starlette` used by 2 modules
- `bcrypt` used by 1 modules
- `collections` used by 1 modules
