# AFOS-017A Implementation Map

Mission evidence:
[AFOS-017A Mission Completion Report](../../company/missions/active/afos-017a/MISSION_COMPLETION_REPORT.md).

## Authority map

| Concern | Canonical source | AFOS-017A use |
|---|---|---|
| Worker identity and executable handler | `app/platform/agents/registry.py` | Read projection; no replacement registry |
| Runtime capability and dependency contract | `app/platform/agents/manifest_registry.py` | Skills, inputs, outputs, dependencies and approval boundaries |
| Persisted specialist definitions | `PlatformAgentDefinition` | Included when loaded into the canonical registry |
| Organisation departments and teams | `app/platform/organization/registry.py` | Existing department/team metadata |
| Executive reporting hierarchy | `app/platform/management/registry.py` | Reporting lines and management roles |
| Current work | `PlatformAgentTask` | Current jobs, workload and runtime status |
| Mission runtime | `PlatformWorkflowRun` and mission run service | Mission identity and workflow linkage |
| Contribution evidence | Delivery Lineage, task results and lifecycle events | Read-only activity and mission history |
| Architecture contribution | Architecture Knowledge Graph | Cross-links from worker contributions |
| Authority | Governance Authorization | Capability remains distinct from authority |
| Authentication | Founder authentication service | Every Organisation API is founder-only |
| Founder UI | Stable Founder Dashboard | Organisation replaces the static Agents panel |

## Findings

The existing Agents page is static presentation code in
`app/platform/ui/founder_dashboard_stable.py`. It is not an authority and shows
roles that are not derived from the runtime registry.

There is already an organisation registry, a separate management hierarchy,
runtime manifests, persisted agent definitions and durable agent tasks. They
are connected by identifiers but have no consolidated founder-facing read
model.

No `skills.md` source exists in the repository. AFOS-017A therefore introduces
repository-backed operational skill documents next to the canonical agent
runtime. The worker loads the assigned agent's active document before invoking
the existing handler. The documents are not a second registry and grant no
authority.

## Integration plan

1. Build a read-only Organisation projection over existing authorities.
2. Derive reporting relationships from management delegation and existing
   department/team membership.
3. Derive workload and status only from durable `PlatformAgentTask` evidence.
4. Keep missing data explicitly unavailable; do not fabricate progress or
   performance scores.
5. Add founder-only skill reads and governed repository-backed skill changes.
6. Replace the static Agents panel while preserving `#agents` as a compatibility
   alias for canonical `#organisation`.
7. Reuse the existing dashboard shell, routes, authentication and governance.

## Minimum extensions

- Repository-backed operational skill documents and loader.
- Organisation read-model service and founder-only API boundary.
- Organisation dashboard script and section.
- Audit evidence for skill changes through the existing event boundary.

No new database, mission store, task model, event stream or agent registry is
required.

## Deprecation

| Component | Decision |
|---|---|
| Static `AGENTS_SECTION` | Replace; no authoritative data |
| `#agents` deep link | Retain as compatibility alias to `#organisation` |
| Existing organisation registry | Retain as canonical structural metadata |
| Existing management registry | Retain as canonical reporting metadata |

## Risks

- Organisation and management registries currently cover different subsets of
  the workforce. The projection must expose incomplete metadata rather than
  inventing relationships.
- Production containers cannot treat local filesystem mutation as durable.
  Skill editing must use governed repository changes and becomes active only
  when the resulting version is released.
- Historical contribution quality depends on mission and task identity already
  present in durable evidence.

## Production acceptance

The candidate must prove founder-only access, real registry-derived workers,
real task-derived workload, organisation chart and directory accessibility,
live skill source loading, reviewed skill diffs, conflict detection, governance
preservation, deep-link compatibility, responsive layouts and regression-free
Mission Control navigation.

## Completed integration

- The Organisation Console is a read-only projection over the canonical agent
  registry, manifests, organisation metadata, management metadata, durable
  workflow runs, durable agent tasks, execution evidence, Delivery Lineage and
  the Architecture Knowledge Graph.
- Department, team and worker detail are loaded through founder-authenticated
  endpoints. Heavy worker evidence is deferred until its profile tab is opened.
- Operational `skills.md` files are injected by the existing Agent Worker before
  handler execution. Runtime diagnostics distinguish a repository version from
  a version confirmed as loaded in the current process.
- Skill edits prepare the existing governed GitHub execution package. They do
  not directly mutate the repository, activate runtime behavior or grant
  authority.
- The legacy Workforce response is retained as a compatibility adapter over the
  canonical Organisation projection. Its synthetic employee records were
  removed.
- The legacy `#agents` URL remains an alias for `#organisation`; there is no
  second Agents UI or organisation authority.

## Performance and loading

The landing projection builds one bounded runtime index and uses a five-second
process-local read cache. Directory rendering is windowed to 100 workers and
worker evidence is paged at 25 records by default. Local validation with 500
task records completed the evidence projection below the 500 ms acceptance
budget. The cache is presentation-only and does not own runtime state.

## Known limitations

- Two registered workers have no authoritative department assignment and are
  shown as `Unassigned`; the UI does not infer a reporting relationship.
- A repository skill version is not described as released or active unless
  runtime load evidence exists. Cross-instance production activation remains
  dependent on the normal merge, release and verification lifecycle.
- Empty mission, lineage, architecture, repository and deployment tabs mean no
  authoritative evidence is linked to that worker in the current environment;
  no placeholder history or progress is fabricated.
- Skill history depends on existing repository history availability.
