# Code Size Audit

Objective: keep Python source code files at or below 200 lines.

## Current Status

- Python source files over 200 lines: 0
- Largest Python source file: `app/platform/services/agent_dependency_graph_service.py` at 200 lines
- Validation command:
  `find app -name '*.py' -not -path '*/__pycache__/*' -print0 | xargs -0 wc -l`

## Refactored Structure

- Oversized service and agent modules were converted to packages that preserve the original import paths.
- `app/platform/persistence/models.py` now re-exports model classes from domain modules under `app/platform/persistence/model_definitions/`.
- `app/platform/api/routes.py` now re-exports focused platform route modules from `app/platform/api/platform_routes/`.
- Embedded dashboard and generated-preview markup moved to template files outside Python source.
- CLI-style packages include `__main__.py` where the original module supported `python -m ...`.

## Largest Python Files

- `app/platform/services/agent_dependency_graph_service.py`: 200 lines
- `app/platform/services/generated_preview_repair_apply_service.py`: 199 lines
- `app/platform/repair/run_repair.py`: 199 lines
- `app/platform/agents/controlled_sandbox_runtime_log_capture_check.py`: 199 lines
- `app/platform/agents/version_restore_planning_check.py`: 198 lines
- `app/platform/agents/version_diff_viewer_check.py`: 198 lines
- `app/platform/services/materialization_approval_record_service.py`: 196 lines
- `app/platform/api/security.py`: 195 lines
- `app/platform/services/runtime_run_plan_builder_service.py`: 191 lines
- `app/platform/services/materialization_sandbox_writer_service.py`: 191 lines

## Verification

- Python 3.9 compatibility scanner: passed
- Full app compile: passed
- Platform route validation: passed
- Full platform validation: passed
