from __future__ import annotations

from typing import Any, Dict

from app.platform.agents.registry import AgentDefinition, register_agent
from app.platform.agents.factory import agent_factory_handler


def _goal(task: Dict[str, Any]) -> str:
    input_payload = task.get("input_payload") or {}
    workflow_context = input_payload.get("workflow_context") or {}
    workflow_name = str(workflow_context.get("workflow_name") or "")

    if workflow_name.startswith("Build App: "):
        return workflow_name.removeprefix("Build App: ").strip() or "No goal provided"

    return str(input_payload.get("goal") or task.get("description") or task.get("title") or "No goal provided")


def architect_agent_handler(task: Dict[str, Any]) -> Dict[str, Any]:
    goal = _goal(task)
    return {
        "success": True,
        "agent_id": "architect_agent",
        "message": "Architect Agent V1 produced an architecture plan.",
        "goal": goal,
        "architecture_plan": {
            "frontend": "React or generated UI layer",
            "backend": "FastAPI service layer",
            "database": "SQLAlchemy-managed relational database",
            "auth": "User authentication and role-based access control",
            "core_modules": [
                "data models",
                "API routes",
                "service layer",
                "validation layer",
                "tests",
            ],
            "next_recommended_task": "builder_task",
        },
    }


def builder_agent_handler(task: Dict[str, Any]) -> Dict[str, Any]:
    goal = _goal(task)
    return {
        "success": True,
        "agent_id": "builder_agent",
        "message": "Builder Agent V1 produced an implementation plan.",
        "goal": goal,
        "implementation_plan": {
            "files_to_create": [
                "index.html",
                "styles.css",
                "app.js",
                "README.md",
            ],
            "safe_mode": True,
            "writes_code": False,
            "write_mode": "db_preview_only",
            "reason": "V88 emits browser app files as DB-preview records only. No disk write, filesystem write, deployment, or generated-code execution is performed.",
            "next_recommended_task": "reviewer_task",
        },
        "generated_files": [
            {
                "path": "index.html",
                "language": "html",
                "purpose": "Static browser entry point for the generated app preview.",
                "content": f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AI Software Factory App Preview</title>
  <link rel="stylesheet" href="styles.css">
</head>
<body>
  <main class="app-shell">
    <section class="hero">
      <p class="eyebrow">DB-preview generated app</p>
      <h1>{goal}</h1>
      <p class="summary">This app was generated as a safe database preview artifact. It has not been written to disk, deployed, or executed.</p>
      <div class="actions">
        <button id="primary-action" type="button">Review Generated App</button>
        <button id="secondary-action" type="button">View Safety Status</button>
      </div>
    </section>
    <section class="status-grid" aria-label="Safety status">
      <article>
        <h2>Write Mode</h2>
        <p>DB preview only</p>
      </article>
      <article>
        <h2>Disk Write</h2>
        <p>Disabled</p>
      </article>
      <article>
        <h2>Code Execution</h2>
        <p>Disabled</p>
      </article>
    </section>
    <pre id="status-output" aria-live="polite"></pre>
  </main>
  <script src="app.js"></script>
</body>
</html>
""",
                "content_preview": "Static HTML shell for the generated browser app preview.",
                "write_status": "preview_only",
            },
            {
                "path": "styles.css",
                "language": "css",
                "purpose": "Styles for the generated browser app preview.",
                "content": """body {
  margin: 0;
  font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  background: #f5f7fb;
  color: #172033;
}

.app-shell {
  max-width: 960px;
  margin: 0 auto;
  padding: 48px 24px;
}

.hero {
  background: white;
  border-radius: 24px;
  padding: 40px;
  box-shadow: 0 20px 50px rgba(23, 32, 51, 0.08);
}

.eyebrow {
  margin: 0 0 12px;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  font-size: 0.75rem;
  font-weight: 700;
  color: #4f46e5;
}

h1 {
  margin: 0;
  font-size: clamp(2rem, 5vw, 4rem);
  line-height: 1;
}

.summary {
  max-width: 680px;
  color: #5d667a;
  font-size: 1.1rem;
  line-height: 1.7;
}

.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 24px;
}

button {
  border: 0;
  border-radius: 999px;
  padding: 12px 18px;
  font-weight: 700;
  cursor: pointer;
}

#primary-action {
  background: #172033;
  color: white;
}

#secondary-action {
  background: #e8ecf8;
  color: #172033;
}

.status-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px;
  margin-top: 24px;
}

.status-grid article,
#status-output {
  background: white;
  border-radius: 18px;
  padding: 20px;
  box-shadow: 0 10px 30px rgba(23, 32, 51, 0.06);
}

.status-grid h2 {
  margin: 0 0 8px;
  font-size: 0.9rem;
}

.status-grid p {
  margin: 0;
  color: #15803d;
  font-weight: 700;
}
""",
                "content_preview": "CSS styles for the generated browser app preview.",
                "write_status": "preview_only",
            },
            {
                "path": "app.js",
                "language": "javascript",
                "purpose": "Small browser interaction script for the generated app preview.",
                "content": """const statusOutput = document.getElementById("status-output");
const primaryAction = document.getElementById("primary-action");
const secondaryAction = document.getElementById("secondary-action");

const safetyStatus = {
  writeMode: "db_preview_only",
  diskWritePerformed: false,
  filesystemWritePerformed: false,
  generatedCodeExecutionPerformed: false,
  externalDeploymentPerformed: false
};

function showStatus(message) {
  statusOutput.textContent = `${message}\n\n${JSON.stringify(safetyStatus, null, 2)}`;
}

primaryAction?.addEventListener("click", () => {
  showStatus("Generated app preview is ready for browser review.");
});

secondaryAction?.addEventListener("click", () => {
  showStatus("Safety boundary verified for DB-preview-only generation.");
});

showStatus("Preview loaded from generated DB record content.");
""",
                "content_preview": "JavaScript interaction for DB-preview browser review.",
                "write_status": "preview_only",
            },
            {
                "path": "README.md",
                "language": "markdown",
                "purpose": "Operator notes for the generated DB-preview app.",
                "content": f"""# Generated App Preview

## Goal

{goal}

## V88 Safety Boundary

This app was generated as database-preview content only.

- Write mode: `db_preview_only`
- Disk write performed: `false`
- Filesystem write performed: `false`
- Generated code execution performed: `false`
- External deployment performed: `false`

## Review Notes

Use the browser Generated Files panel, Workspace Explorer, and file preview flow to inspect these generated files before any later approval-gated materialization milestone.
""",
                "content_preview": "README notes for the generated DB-preview app.",
                "write_status": "preview_only",
            },
        ],
        "write_mode": "db_preview_only",
        "disk_write_performed": False,
        "filesystem_write_performed": False,
        "generated_code_execution_performed": False,
        "external_deployment_performed": False,
    }


def reviewer_agent_handler(task: Dict[str, Any]) -> Dict[str, Any]:
    goal = _goal(task)
    return {
        "success": True,
        "agent_id": "reviewer_agent",
        "message": "Reviewer Agent V1 produced a review checklist.",
        "goal": goal,
        "review_checklist": [
            "Validate architecture matches user goal",
            "Check security-sensitive operations",
            "Check database model consistency",
            "Check API route naming",
            "Check approval requirement for risky actions",
            "Check tests are defined before deployment",
        ],
        "next_recommended_task": "test_task",
    }


def validation_agent_handler(task: Dict[str, Any]) -> Dict[str, Any]:
    goal = _goal(task)
    return {
        "success": True,
        "agent_id": "test_agent",
        "message": "Test Agent V1 produced a validation plan.",
        "goal": goal,
        "validation_plan": {
            "compile_checks": True,
            "release_gate": "fast",
            "api_smoke_tests": True,
            "manual_approval_required_before_deployment": True,
        },
    }


def register_specialist_agents() -> None:
    register_agent(
        AgentDefinition(
            agent_id="architect_agent",
            name="Architect Agent",
            description="Creates architecture plans for generated applications.",
            capabilities=["architect_task"],
            handler=architect_agent_handler,
        )
    )
    register_agent(
        AgentDefinition(
            agent_id="builder_agent",
            name="Builder Agent",
            description="Creates implementation plans before code generation.",
            capabilities=["builder_task"],
            handler=builder_agent_handler,
            requires_approval_for_new_tasks=True,
        )
    )
    register_agent(
        AgentDefinition(
            agent_id="reviewer_agent",
            name="Reviewer Agent",
            description="Reviews planned or generated work for quality and safety.",
            capabilities=["reviewer_task"],
            handler=reviewer_agent_handler,
        )
    )
    register_agent(
        AgentDefinition(
            agent_id="agent_factory_agent",
            name="Agent Factory Agent",
            description="Proposes new specialist agents when a project needs capabilities not covered by existing agents.",
            capabilities=["agent_factory_task", "propose_agent"],
            handler=agent_factory_handler,
            requires_approval_for_new_tasks=True,
        )
    )
    register_agent(
        AgentDefinition(
            agent_id="test_agent",
            name="Test Agent",
            description="Creates validation plans and later runs tests.",
            capabilities=["test_task", "worker_loop_test"],
            handler=validation_agent_handler,
        )
    )


register_specialist_agents()
