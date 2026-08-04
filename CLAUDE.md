# CLAUDE.md

Repo-specific instructions for AI coding agent sessions working on AI Software Factory
(`tehkst/ai-app-builder-dev`). This file is read directly by Claude Code (terminal and
claude.ai/code); `AGENTS.md` at the repo root is a symlink to this file so Codex sessions get
the same instructions. Where a convention below differs by tool (e.g. the commit trailer), it's
called out explicitly - everything else applies equally to both.

## Before grepping the codebase, check the architecture graph

This repo has a real, AST-derived architecture knowledge graph
(`app/platform/architecture_knowledge_graph/`) covering module import dependencies,
authority/governance ownership, ADRs, delivery lineage, and function/class-level call edges. It
already knows the answer to most "is X relevant to Y" / "what depends on this" questions.

**Before manually grepping the codebase to answer that kind of question, run this first:**

```
python -m app.platform.architecture_knowledge_graph.relevance <path/to/file.py>
```

This prints a plain-text report for the given module: what it depends on, what depends on it
(direct imports both ways), its functions/classes, and which functions elsewhere call into it
(only unambiguous matches - an ambiguous call site, same function name defined in multiple
places, is reported as unresolvable rather than guessed). It needs no database and no running
server - pure AST + filesystem - so it works in any checkout, including a fresh session with no
prior context. It takes up to ~20 seconds on this repo's current size (it parses every `.py`
file under `app/`); that's expected, not a hang.

Equivalently, invoke the `/code-relevance-check <file or symbol>` skill, which runs the same
command and interprets the result for you.

The full graph (this CLI's data plus runtime/mission/governance projections that do need the
platform database) is queryable via `app.platform.architecture_knowledge_graph.projection.build_graph()`
and is what backs the founder-facing "Architecture" tab in Mission Control and Jarvis's own
conversational context - see that package's other modules if you need more than module/function
relevance (e.g. governance authority, delivery lineage, or the impact-analysis / blast-radius
report).

## CI gates - run these locally before pushing

These are the same checks `.github/workflows/pr-validation.yml` runs on every PR; run them
locally first so CI isn't your first signal of a break:

```
python -m compileall app
python -m app.platform.validate_all --profile ci
python -m app.platform.api_contract
python -m app.platform.gcp.readiness
python -m app.platform.gcp.check
python -m app.platform.gcp.deploy_check
bash infra/scripts/gate.sh
```

Set `PLATFORM_DATABASE_URL` to an isolated sqlite path (e.g.
`sqlite:////tmp/scratch.db`) for local runs unless you specifically need the real
platform Postgres - most of these gates don't need a live database, and pointing at an
unreachable one will make DB-dependent calls slow or fail rather than crash outright (several
already degrade gracefully; see `architecture_knowledge_graph/authority_projection.py` and
`lineage_projection.py` for the pattern if you add a new one).

Some board_room checks (e.g. `natural_conversation_check`, `operating_console.action_flow_check`)
call a real AI provider and need `OPENAI_API_KEY` (or `DEEPSEEK_API_KEY`) exported to pass -
without it they fail in a way that looks like a regression but isn't.

## Conventions

- Work on a branch named `claude/<descriptive-name>`; open PRs with `gh pr create`, a `## Summary`
  and `## Test plan` in the body, and a co-authorship trailer on commits identifying whichever
  agent actually did the work: `Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>` for
  Claude Code sessions, `Co-Authored-By: Codex <noreply@openai.com>` for Codex sessions.
- Keep files under ~200 lines; this convention is self-enforced and checked
  (`repository_projection.py` flags its own `line_rule: "Split Required"` past 200 LOC). Split an
  over-limit file using the existing `part_1.py`/`part_2.py`/... pattern with an `__init__.py`
  that merges their public names (see `app/platform/services/agent_task_service/`).
- No decorative or fabricated data: if a field has no real evidence, say so explicitly rather than
  inventing a plausible-looking value - this is enforced throughout the codebase (architecture
  graph nodes, agent roster profiles, etc.) and reviewers will flag violations.

## Where things live

- **Founder-facing Mission Control** (the platform operator's own admin UI): `app/platform/ui/`
  (page shells and scripts) + `app/platform/organization_console/`, `board_room/`,
  `operating_console/`, `architecture_knowledge_graph/` (backing services). Served at
  `/mission-control/ui`.
- **Customer-facing SaaS Portal** (an AI Software Factory customer building their own app):
  `app/platform/ui/customer_home.py` (served at `/customer/home`) calling
  `app/api/routes/projects.py`, `app/platform/saas_builder/` (app generation/preparation/
  deployment), and `app/platform/services/customer_app_scope_service.py` /
  `generated_app_preview_service.py` for scope drafting and in-browser preview.
- **Generated customer applications themselves** live under `generated_apps/` locally / the
  platform database in production - not part of this platform's own codebase.
