"""Architecture map: every top-level area of `app/` placed in a layer, with its status.

Single source of truth for docs/architecture/MODULE_MAP.md (`python -m app.platform.architecture_map
--write` regenerates it) and checked by `architecture_map_check`: adding or removing a package
without updating MAP fails CI, so the map can't go stale. Statuses come from the reachability audit
of clean-up batches 1-5 (2026-10-16):

- live: production (`app.platform.server`) uses it.
- legacy: live, but part of the older platform-mission pipeline or role agents that Orca replaces;
  migrate onto Orca, then retire. Don't build new features on it.
- check-only: production never uses it; only its own registered checks import it (mostly demo
  scaffolding from earlier milestones). Candidates for retirement together with those checks.
- tooling: validation, gates and CI helpers.
- new: built and checked, not yet wired into production; a planned roadmap step will use it.
"""
from __future__ import annotations

import sys
from pathlib import Path

LAYERS = (
    ("interfaces", "Founder interfaces", "What the founder sees and talks to: Mission Control, Jarvis, consoles."),
    ("orchestration", "Orchestration", "Decides what work happens and in which order."),
    ("workforce", "AI workforce", "The AI employees (Orca's workforce lives in company/workforce/)."),
    ("engine", "Execution engine", "Lets an employee act safely: tool loop, coding, GitHub, sandboxes."),
    ("data", "Providers, data and knowledge", "AI providers, persistence, company knowledge and evidence."),
    ("governance", "Governance and safety", "Who may do what: auth, approvals, policies, guards."),
    ("customer", "Customer product", "What customers use: the Customer Portal and their app builds."),
    ("operations", "Deploy and operations", "Hosting, deployment, health and logging."),
    ("tooling", "Tooling and checks", "Validation, gates and CI helpers."),
)

# package -> (layer, status, what it does)
MAP = {
    # interfaces
    "ui": ("interfaces", "live", "Server-rendered pages: Mission Control (ui/mc2) and its Insights pages, Customer Portal, landing."),
    "mission_control": ("interfaces", "live", "Mission Control summary API."),
    "board_room": ("interfaces", "live", "Jarvis: founder conversation, intent routing and executive reasoning."),
    "operating_console": ("interfaces", "live", "Jarvis chat endpoint and its action buttons (Board Room actions)."),
    "conversation_intelligence": ("interfaces", "live", "Analyses founder conversations for Jarvis."),
    "founder_decision": ("interfaces", "live", "Founder decision experience built on Jarvis responses."),
    "founder_console": ("interfaces", "live", "Founder console API (GCP-13)."),
    "founder_workspace": ("interfaces", "live", "Founder workspace and request intake."),
    "executive_office": ("interfaces", "live", "Executive Office summary for Mission Control."),
    "executive_decision": ("interfaces", "live", "Executive Decision Center (recommended actions)."),
    "organization_console": ("interfaces", "live", "Organisation view: departments, workers, evidence (Insights page)."),
    "delivery_lineage": ("interfaces", "live", "Delivery history: how each mission went from idea to done."),
    "journey_inspection": ("interfaces", "live", "Read-only end-to-end mission journey inspection."),
    "cognitive_memory": ("interfaces", "live", "Memory and knowledge view (Insights page)."),
    "knowledge_vault": ("interfaces", "live", "Knowledge Vault summary."),
    "customers_overview": ("interfaces", "live", "Customers screen data: customers joined with their apps."),
    "clients": ("interfaces", "live", "Clients area: clients, their code, Health Checks, jobs to the AI team, delivery (PR/patch)."),
    "codebase_health": ("customer", "live", "Codebase Health Check for client code: read-only scorecard, impact map and PDF."),
    "ai_costs": ("engine", "new", "AI usage and cost per mission, client job and Audit; model tiers per employee."),
    "impact_map": ("customer", "new", "Impact map: PHP/JS/Python dependency graph; 'what breaks if we change this?'."),
    "container_sandbox": ("engine", "live", "Locked-down Docker sandbox: every client-mission command runs here (copy, no network, non-root)."),
    "repair_console": ("interfaces", "live", "Founder-only repair flow for customer app builds (/mission-control/repair/*)."),
    "ui_ux_agent": ("interfaces", "live", "Jarvis-proposed UI/UX changes with preview, approve, PR."),
    "telegram": ("interfaces", "live", "Telegram approval messages."),
    "business_metrics": ("interfaces", "live", "Customers, sign-ups and MRR from the customer database."),
    "ai_workforce": ("interfaces", "legacy", "Deprecated /mission-control/workforce adapter; use organization_console."),
    # orchestration
    "orca": ("orchestration", "live", "Orca: missions, Builder <-> QA (+UX) loop, gates, store, API, CLI. The orchestrator."),
    "pipeline": ("orchestration", "legacy", "Older mission operating system (platform missions)."),
    "execution": ("orchestration", "legacy", "Older mission execution lifecycle (UI retired in step 3b; checks still use it)."),
    "mission_execution": ("orchestration", "legacy", "Mission execution bridge (GCP-05)."),
    "planning": ("orchestration", "legacy", "Older autonomous engineering planning."),
    "engineering_manager": ("orchestration", "legacy", "Engineering Manager planning layer."),
    "engineering": ("orchestration", "legacy", "Engineering operating-system primitives (change sets)."),
    "founder_workflow": ("orchestration", "legacy", "Founder workflow engine (FWE-01)."),
    "founder_approval": ("orchestration", "legacy", "Founder approval workflow (GCP-04)."),
    "proposal_generator": ("orchestration", "legacy", "Proposal generator (GCP-03)."),
    "pmo": ("orchestration", "legacy", "Programme management office; mostly unused by production."),
    "delegation": ("orchestration", "legacy", "Dynamic delegation services; mostly unused by production."),
    "management": ("orchestration", "legacy", "Engineering management hierarchy."),
    "organization": ("orchestration", "legacy", "Organisation hierarchy of the legacy agents."),
    # workforce
    "agents": ("workforce", "legacy", "Legacy role agents, registry and worker, plus many checks; Orca's workforce replaces them."),
    # engine
    "nautilus": ("engine", "live", "Nautilus: tool-calling agent loop, permissions, recipes, provider adapters."),
    "coding_agent": ("engine", "live", "Governed edit/test/repair loop for platform changes; Stage D qualification."),
    "autonomous_engineering": ("engine", "legacy", "Autonomous engineering worker (GCP-08)."),
    "code_planner": ("engine", "legacy", "Guarded code planner (GCP-10)."),
    "patch_application": ("engine", "legacy", "Guarded patch application (GCP-11)."),
    "pr_orchestration": ("engine", "legacy", "Pull request orchestration (GCP-12)."),
    "github_execution": ("engine", "live", "Approved GitHub execution: branches, commits, PRs, merges (its classic panel retired in step 3b)."),
    "github": ("engine", "live", "GitHub integration and health."),
    "ci_repair": ("engine", "live", "CI repair loop (GCP-16)."),
    "repo_import": ("engine", "live", "Import external repositories for Jarvis to read."),
    "repository_intelligence": ("engine", "live", "Repository intelligence (GCP-09)."),
    "digital_twin": ("engine", "live", "Sandbox runner with resource limits."),
    "workspaces": ("engine", "live", "Generated-app workspace roots."),
    "guards": ("engine", "live", "Filesystem write guard for generated files."),
    # data
    "runtime": ("data", "live", "AI provider selection (OpenAI, DeepSeek) and job runtime primitives."),
    "persistence": ("data", "live", "Platform database models, sessions and migrations."),
    "credential_vault": ("data", "live", "Encrypted credentials (KMS) with masked display."),
    "config": ("data", "live", "Application settings from the environment."),
    "events": ("data", "live", "Governed event contracts and emission."),
    "plugins": ("data", "live", "Vendor-neutral plugin architecture for providers."),
    "registry": ("data", "live", "Unified platform registry for resource discovery."),
    "repository": ("data", "live", "Shared repository loading and Markdown parsing."),
    "company_brain": ("data", "live", "Company Brain: constitution, strategy, decisions."),
    "company_objects": ("data", "live", "Company object model."),
    "company_graph": ("data", "live", "Company graph projection."),
    "company_intelligence": ("data", "live", "Company intelligence snapshot."),
    "executive_intelligence": ("data", "live", "Executive briefing and evidence registry (AEL-01)."),
    "capability_intelligence": ("data", "live", "Evidence-based capability inventory (never guesses)."),
    "architecture_knowledge_graph": ("data", "live", "AST-derived architecture graph, size rule, relevance CLI."),
    "architecture_agent": ("data", "live", "Platform-aware architecture decision support."),
    "architecture_map": ("tooling", "tooling", "This map of every area, layer and status (CI and docs only)."),
    "billing": ("data", "live", "Billing plans catalogue (used for MRR)."),
    # governance
    "auth": ("governance", "live", "Founder login, sessions, password reset; customer auth."),
    "auth_boundary": ("governance", "live", "Authentication boundary policy (PROTECT-01)."),
    "governance_authorization": ("governance", "live", "Canonical governance authorization boundary."),
    "constitution": ("governance", "live", "Platform constitution and its runtime bindings."),
    "validation": ("governance", "live", "Evidence-derived platform validation missions."),
    "security": ("governance", "check-only", "Rate limiting helpers."),
    # customer
    "saas_builder": ("customer", "live", "Customer app builds: scope, generate, review, preview."),
    "publish_review": ("customer", "live", "Customer publish requests: approve, reject, open PR."),
    "services": ("customer", "live", "Shared services used by the customer pipeline and Jarvis (scoping, repair, workflows)."),
    "app.api": ("customer", "live", "Customer Portal API (/api/projects, auth)."),
    "app.core": ("customer", "live", "Customer database and security core."),
    "app.models": ("customer", "live", "Customer database models: organisations, users, memberships, projects."),
    "app.services": ("customer", "live", "Customer-side services."),
    "app.schemas": ("customer", "live", "Customer API schemas."),
    "app.ai": ("customer", "check-only", "Older generation graph and trusted templates; only checks use it."),
    "app": ("customer", "live", "Root package."),
    # operations
    "deployment": ("operations", "live", "Cloud Run deployment, preview and teardown (paused: no host)."),
    "gcp": ("operations", "live", "GCP readiness and deploy gates (project deleted; kept until a new host)."),
    "release": ("operations", "live", "Release actions and probes."),
    "health": ("operations", "live", "Health status."),
    "logging": ("operations", "live", "Structured request logging."),
    "repair": ("operations", "check-only", "Repair report listing tools."),
    # tooling
    "validate_all": ("tooling", "tooling", "Runs every registered check by profile (CI uses --profile ci)."),
    "api_contract": ("tooling", "tooling", "Checks the server registers every expected endpoint."),
    "server": ("interfaces", "live", "The production app (app.platform.server:app): every route."),
    "compatibility": ("tooling", "tooling", "Dependency policy and compatibility scanner."),
    "release_gate": ("tooling", "tooling", "Release gate runner."),
    "security_report": ("tooling", "tooling", "Security report check."),
    "frontend": ("tooling", "tooling", "Frontend build validation."),
    "artifacts": ("tooling", "tooling", "Generated-artifact stability checks."),
    "company_brain_check": ("tooling", "tooling", "Company Brain check."),
    "import_integrity_check": ("tooling", "tooling", "Fails CI if any file imports an app.* module that does not exist."),
    "architecture_map_check": ("tooling", "tooling", "Keeps this map and docs/architecture/MODULE_MAP.md in step with the code."),
    "api": ("tooling", "check-only", "Remaining helpers of the retired app/main.py API (platform admin auth, schemas); only checks use them."),
    **{alias: ("tooling", "tooling", "Milestone alias that runs a registered check.") for alias in (
        "a140_144", "c135_139", "d1_1", "d1_2", "d1_3", "d1_4", "f126", "l158_160", "n127", "o129",
        "o145_149", "p128", "r150_153", "r154_157", "w130_134", "z125")},
    # check-only demo scaffolding from earlier milestones
    **{name: ("tooling", "check-only", summary) for name, summary in (
        ("webconsole", "Platform admin web console foundation (never served)."),
        ("api_gateway", "Enterprise API gateway foundation (never served)."),
        ("saas_portal", "Earlier customer portal foundation (superseded by ui/customer_home)."),
        ("lifecycle", "Lifecycle stage catalogue."),
        ("knowledge", "Engineering knowledge graph primitives."),
        ("integration", "Shared UX integration foundation."),
        ("workspace", "Demo workspace flow."),
        ("collab", "Demo collaboration flow."),
        ("catalog", "Catalogue models."),
        ("adminops", "Demo admin operations flow."),
        ("opscenter", "Demo operations centre flow."),
        ("memory", "Engineering memory scopes."),
        ("readiness", "Demo readiness flow."),
        ("learning", "Decision learning primitives."),
        ("self_healing", "Platform health control loop."),
        ("notify", "Demo notices flow."),
        ("preferences", "Demo preferences flow."),
        ("launch", "Demo launch flow."),
        ("operations", "Operations centre primitives."),
        ("data", "Data events, tenants, readiness and recovery primitives."),
        ("work", "Demo work flow."),
        ("onboarding", "Demo onboarding flow."),
        ("feed", "Demo feed flow."),
        ("projects", "Project platform module."),
    )},
}

STATUS_ORDER = ("live", "new", "legacy", "check-only", "tooling")


def discover() -> set:
    """Top-level areas that exist on disk: app/platform/<package or module> and app/<package>."""
    root = Path(__file__).resolve().parents[2]
    found = {"app"}
    for path in (root / "app" / "platform").iterdir():
        if path.name.startswith(("_", ".")):
            continue
        if path.is_dir() and any(path.rglob("*.py")):
            found.add(path.name)
        elif path.suffix == ".py":
            found.add(path.stem)
    for path in (root / "app").iterdir():
        if path.is_dir() and path.name not in {"platform", "__pycache__"} and any(path.rglob("*.py")):
            found.add(f"app.{path.name}")
    return found


def render_markdown() -> str:
    lines = [
        "# Module map",
        "",
        "Every top-level area of `app/`, its layer and status. Generated from",
        "`app/platform/architecture_map.py` (`python -m app.platform.architecture_map --write`); CI fails if a",
        "package is added or removed without updating the map. Statuses: **live** (production uses it),",
        "**new** (built and checked, wired in by a coming roadmap step), **legacy** (live but replaced by",
        "Orca; migrate, don't extend), **check-only** (only its own checks use it; retirement candidate),",
        "**tooling** (validation and gates).",
        "",
    ]
    for key, title, purpose in LAYERS:
        rows = sorted((name, info) for name, info in MAP.items() if info[0] == key)
        if not rows:
            continue
        rows.sort(key=lambda item: (STATUS_ORDER.index(item[1][1]), item[0]))
        lines += [f"## {title}", "", purpose, "", "| Area | Status | What it does |", "|---|---|---|"]
        lines += [f"| `{name}` | {info[1]} | {info[2]} |" for name, info in rows]
        lines.append("")
    counts = {status: sum(1 for info in MAP.values() if info[1] == status) for status in STATUS_ORDER}
    lines.append("Totals: " + ", ".join(f"{count} {status}" for status, count in counts.items()) + ".")
    return "\n".join(lines) + "\n"


DOC_PATH = Path(__file__).resolve().parents[2] / "docs" / "architecture" / "MODULE_MAP.md"

if __name__ == "__main__":
    if "--write" in sys.argv:
        DOC_PATH.write_text(render_markdown(), encoding="utf-8")
        print(f"wrote {DOC_PATH}")
    else:
        print(render_markdown())
