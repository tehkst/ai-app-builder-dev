---
name: code-relevance-check
description: Answer "is X relevant to Y" / "what depends on this module or function" questions using this repo's real AST-derived architecture graph, instead of manually grepping. Use whenever a task requires understanding what a file/module connects to, what would break if it changed, or who calls into it.
---

# Code relevance check

This repo (`tehkst/ai-app-builder-dev`) has a real, AST-derived architecture knowledge graph at
`app/platform/architecture_knowledge_graph/`. It already knows module import dependencies and
function/class-level call edges for the whole codebase. Use it instead of open-ended grepping
whenever the question is about relevance, dependency, or blast radius.

## When to use this skill

- The user (or the current task) asks "is `<file A>` relevant to `<file B>`?"
- "What depends on this module/function?"
- "What would break if I changed/removed this?"
- "Who calls this function?"
- Before making a change to a file whose blast radius isn't already obvious from context.

Don't use it for questions about *what a file does* (just read the file) or runtime/business
behavior (that's not what this graph captures) - it's specifically for structural
dependency/call relevance.

## Procedure

1. Resolve the target to a real file path under `app/` (e.g.
   `app/platform/services/customer_app_scope_service.py`). If the user gave a symbol name
   instead of a path (a function or class), find its defining file first (a quick grep for
   `def <name>` or `class <name>` is fine for that one lookup - the graph command itself takes a
   file path, not a bare symbol name).

2. Run:

   ```
   python -m app.platform.architecture_knowledge_graph.relevance <path/to/file.py>
   ```

   This needs no database and no running server - it's pure AST + filesystem - so run it
   directly, don't try to start the platform server first. It can take up to ~20 seconds on this
   repo's current size (it parses every `.py` file under `app/` each time); that's expected.

   If the path doesn't resolve to a real module, the command says so explicitly - don't guess a
   corrected path silently, report what it said and ask or re-derive the correct path.

3. Interpret the output into a direct answer to the actual question, not a raw dump:
   - **Depends on** = what this file needs; changing those files can affect this one.
   - **Depended on by / imported by** = what would be affected if you change *this* file's
     public surface - this is usually the list that matters most for "what would break".
   - **Functions/classes defined here** + **external callers of its functions** = the
     function-level answer to "who calls this", already filtered to unambiguous matches only
     (an ambiguous call - same function name defined in more than one place - is dropped from
     this list rather than guessed at, so don't treat an empty or short caller list as proof of
     zero callers if the function name is generic/common; say so and fall back to a targeted
     grep for that specific case only).
   - **Related tests** = existing coverage for this module, if any.

4. State the relevance conclusion plainly (e.g. "yes, `foo.py` is directly relevant to `bar.py` -
   `bar.py` imports it and two functions in `bar.py` call into it: ...") with the specific
   module/function names as evidence, rather than a generic "they might be related."

## Notes

- This only covers modules under `app/`. Generated customer applications
  (`generated_apps/` locally, or the platform database in production) aren't in this graph.
- The full graph (this data plus governance authority, delivery lineage, and runtime/mission
  projections that *do* need the platform database) is available via
  `app.platform.architecture_knowledge_graph.projection.build_graph()` for cases beyond plain
  module/function relevance - see CLAUDE.md and that package's other modules.
