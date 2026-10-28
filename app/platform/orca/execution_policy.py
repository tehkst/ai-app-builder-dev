"""Which commands Orca may execute in an execution-approved mission.

Founder approval allows running the generated app's tests, not arbitrary commands. Like the
controlled sandbox runtime (which only runs allowlisted commands such as `npm run dev`), Orca
only runs allowlisted command shapes: test runners and read-only inspection, with every path
operand confined to the workspace. Model-written one-liners (`python -c`, `node -e`), scripts,
shells and network tools are refused.

For generated-app missions this is a command policy, not an OS sandbox: an allowed test runner
still executes the generated tests with the platform process's user rights, which is what the
founder's approval covers. Client missions (`Mission.sandboxed`) apply the same policy and run
every command in the container sandbox (`sandbox_commands.py`).
"""
from __future__ import annotations

import re
import shlex
from typing import Optional, Tuple

from app.platform.nautilus.permissions import command_is_read_only, operands_confined

PYTHONS = {"python", "python3"}
# The project's own check scripts: `npm run test`, `build`, `lint`, `typecheck`, and named variants such
# as `test:unit` (found in the pilot: only `npm test` was allowed, and it also ran database tests).
NPM_RUN_SCRIPT = re.compile(r"build|(?:test|lint|typecheck|type-check)(?::[A-Za-z0-9_.-]+)?")
PHPUNITS = {"phpunit", "vendor/bin/phpunit", "./vendor/bin/phpunit"}
ALLOWED_FORMS = (
    "`pytest [args]`, `python -m pytest [args]` / `python3 -m pytest [args]`, `python -m unittest [args]`, `npm test`, "
    "`npm run test|build|lint|typecheck` (or a named variant such as `npm run test:unit`), `vendor/bin/phpunit [args]`, `composer test`, `php -l FILE`, or a read-only inspection command such as `grep -q PATTERN FILE`; "
    "all paths relative to the workspace"
)


def check_command_allowed(command: str, workspace_root: Optional[str]) -> Tuple[bool, str]:
    """(allowed, reason). Used for acceptance checks and for builder commands."""
    try:
        argv = shlex.split(command)
    except ValueError as exc:
        return False, f"cannot parse command: {exc}"
    if not argv:
        return False, "empty command"
    if not operands_confined(argv[1:], workspace_root):
        return False, "every path must stay inside the workspace"
    program, rest = argv[0], argv[1:]
    if program == "pytest":
        return True, "test runner"
    if program in PYTHONS and rest[:2] in (["-m", "pytest"], ["-m", "unittest"]):
        return True, "test runner"
    if program == "npm" and (rest == ["test"] or (len(rest) == 2 and rest[0] == "run" and NPM_RUN_SCRIPT.fullmatch(rest[1]))):
        return True, "npm script"
    if program in PHPUNITS or (program == "composer" and rest == ["test"]):
        return True, "test runner"
    if program == "php" and len(rest) == 2 and rest[0] == "-l":
        return True, "PHP syntax check"
    if command_is_read_only(command, workspace_root):
        return True, "read-only inspection"
    return False, "not an allowed command; use " + ALLOWED_FORMS
