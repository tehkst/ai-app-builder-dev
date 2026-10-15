# Workforce

The AI employees of AI Software Factory. Orca (`app/platform/orca/`) reads this directory to
know who works here and what each employee may do.

- `manifest.yaml` - one entry per employee: id, department, role file, permission mode,
  autonomy tier, responsibilities, and the roles it was adapted from.
- `roles/<id>.md` - the employee's role prompt: identity, mission, rules, definition of done.
  It becomes the system prompt when Orca puts the employee to work on Nautilus.

Role files are written in our own words and format. Several are adapted from
[agency-agents](https://github.com/msitarzewski/agency-agents) (MIT, © AgentLand Contributors);
each manifest entry's `adapted_from` names the source roles. The onboarding plan is
`company/strategy/ai-workforce-plan.md`.

Rules for role files:

- State the job, the rules, and the definition of done; skip personality flourishes.
- Never grant more than the manifest does: a role file can't widen tools or autonomy.
- Executing generated application code needs founder approval (see the CLAUDE.md decision log);
  role files must not tell an employee to run code unless its task says execution is approved.
